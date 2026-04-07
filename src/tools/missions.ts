/**
 * Mission tools: start, list, status, progress. droid_mission_cancel is
 * intentionally NOT implemented in v1 — cancellation semantics need
 * investigation (spec §6.3).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { setTimeout as delay } from "node:timers/promises";
import { z } from "zod";
import { DEFAULT_MODEL } from "../droid/defaults.js";
import { spawnDroidExec } from "../droid/exec.js";
import {
  getMissionProgress,
  getMissionStatus,
  listMissions,
  missionStateFile,
} from "../droid/missions.js";
import { TagSpecSchema } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createJsonResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerMissionTools(server: McpServer): void {
  server.registerTool(
    "droid_mission_start",
    {
      description:
        "Start a new droid mission — spawns `droid exec --mission --auto high \"...\"` in the given cwd and looks for a new mission directory under ~/.factory/missions/. IMPORTANT: droid only spawns mission orchestration (factoryd workers, state.json, progress_log.jsonl) when the PROMPT IS SUBSTANTIAL enough to trigger multi-feature planning. Trivial prompts like 'say hi' complete as a plain exec and never create a mission directory — this tool detects that case and returns mission_triggered=false with the exec result. Real missions typically need a multi-step implementation prompt: 'implement X with tests and docs' or 'refactor Y to use Z with migration path'. Long-running missions: the tool returns as soon as the mission directory appears; poll progress with droid_mission_status / droid_mission_progress.",
      inputSchema: {
        prompt: z.string(),
        cwd: z.string().optional(),
        model: z.string().optional(),
        allow_unsafe: z
          .boolean()
          .optional()
          .describe(
            "Use --skip-permissions-unsafe instead of --auto high. Only in isolated environments.",
          ),
        tags: z.array(TagSpecSchema).optional(),
        timeout_ms: z
          .number()
          .int()
          .positive()
          .optional()
          .describe(
            "Hard cap on how long we wait for the droid exec subprocess. For long missions use a large value (e.g. 600000 = 10 min) — the tool returns as soon as the mission dir appears on disk, not when the exec completes. Default 120 seconds.",
          ),
      },
    },
    async ({
      prompt,
      cwd,
      model,
      allow_unsafe,
      tags,
      timeout_ms,
    }): Promise<McpToolResponse> => {
      try {
        const resolvedCwd = resolveCwd(cwd);
        const execTimeout = timeout_ms ?? 120_000;
        const beforeUuids = new Set(
          (await listMissions({ all: true, limit: 100_000 })).map((m) => m.uuid),
        );

        const result = await spawnDroidExec(
          {
            prompt,
            model: model ?? DEFAULT_MODEL,
            mission: true,
            ...(allow_unsafe ? { allow_unsafe: true } : { auto: "high" }),
            tags,
          },
          { cwd: resolvedCwd, timeout_ms: execTimeout },
        );

        const sessionId = result.parsed.session_id;

        // Give the filesystem ~500ms to flush any mission state writes
        // that happened during the exec's final teardown — writes can
        // post-date the child process exit briefly.
        await delay(500);
        const afterMissions = await listMissions({ all: true, limit: 100_000 });

        // Primary: a new mission directory whose workingDirectory matches.
        let match = afterMissions.find(
          (m) => !beforeUuids.has(m.uuid) && m.working_directory === resolvedCwd,
        );
        // Fallback 1: any new directory created during the spawn window.
        if (!match) {
          match = afterMissions.find((m) => !beforeUuids.has(m.uuid));
        }
        // Fallback 2: an existing mission whose baseSessionId == our session_id.
        if (!match && sessionId) {
          match = afterMissions.find((m) => m.base_session_id === sessionId);
        }

        if (!match) {
          // Not an error — this happens for trivial prompts that don't
          // trigger real mission orchestration (verified: droid exec
          // --mission "say hi" completes in ~5s as a plain exec with zero
          // new mission dirs on disk). Return the exec result and let the
          // caller decide whether to retry with a more substantial prompt.
          return createJsonResponse({
            mission_triggered: false,
            reason:
              "droid exec --mission completed without creating a new mission directory. Common cause: prompt was too trivial to trigger multi-feature orchestration. Try a prompt like 'implement X with tests and docs' that requires multiple steps.",
            base_session_id: sessionId,
            working_directory: resolvedCwd,
            text: result.parsed.text,
            spawn: {
              ok: result.ok,
              failure: result.failure,
              exit_code: result.exit_code,
              duration_ms: result.duration_ms,
              stderr_tail: result.stderr.trim().slice(0, 500),
            },
            usage: result.parsed.usage,
          });
        }

        const status = await getMissionStatus(match.uuid, {
          include_progress: true,
          progress_limit: 5,
        });

        return createJsonResponse({
          mission_triggered: true,
          mission_id: match.mission_id,
          uuid: match.uuid,
          base_session_id: sessionId,
          working_directory: resolvedCwd,
          state_file: missionStateFile(match.uuid),
          initial_status: status,
          spawn: {
            ok: result.ok,
            exit_code: result.exit_code,
            duration_ms: result.duration_ms,
          },
        });
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_mission_list",
    {
      description:
        "List droid missions from ~/.factory/missions/, filtered by cwd by default (pass all=true for every mission). Returns mission_id, uuid, state, completed/total features, created/updated timestamps, sorted by updatedAt desc.",
      inputSchema: {
        cwd: z.string().optional(),
        all: z.boolean().optional(),
        state: z
          .string()
          .optional()
          .describe("Filter by state: running | paused | completed | failed | ..."),
        limit: z.number().int().positive().optional(),
      },
    },
    async ({ cwd, all, state, limit }): Promise<McpToolResponse> => {
      try {
        const missions = await listMissions({
          cwd: resolveCwd(cwd),
          all,
          state,
          limit,
        });
        return createJsonResponse({ count: missions.length, missions });
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_mission_status",
    {
      description:
        "Get full status for a mission (accepts either mis_xxx or the directory uuid). Returns state, completed/total features, current worker session, and recent progress events. Handoffs are summarized by default — set include_handoffs=true to include the full (potentially 10KB+) payload.",
      inputSchema: {
        mission_id: z.string(),
        include_progress: z.boolean().optional(),
        progress_limit: z.number().int().positive().optional(),
        include_handoffs: z.boolean().optional(),
        include_features: z.boolean().optional(),
      },
    },
    async ({
      mission_id,
      include_progress,
      progress_limit,
      include_handoffs,
      include_features,
    }): Promise<McpToolResponse> => {
      try {
        const status = await getMissionStatus(mission_id, {
          include_progress,
          progress_limit,
          include_handoffs,
          include_features,
        });
        if (!status) {
          return createErrorResponse(
            `mission not found: ${mission_id}. Use droid_mission_list to see available missions.`,
          );
        }
        return createJsonResponse(status);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_mission_progress",
    {
      description:
        "Poll progress events for a mission. Returns a paginated slice of events from progress_log.jsonl. Pass since_offset or since_timestamp from the previous response to get only new events.",
      inputSchema: {
        mission_id: z.string(),
        since_offset: z.number().int().nonnegative().optional(),
        since_timestamp: z.string().optional(),
        limit: z.number().int().positive().optional(),
        event_types: z.array(z.string()).optional(),
        exclude_handoffs: z.boolean().optional(),
      },
    },
    async ({
      mission_id,
      since_offset,
      since_timestamp,
      limit,
      event_types,
      exclude_handoffs,
    }): Promise<McpToolResponse> => {
      try {
        const progress = await getMissionProgress(mission_id, {
          since_offset,
          since_timestamp,
          limit,
          event_types,
          exclude_handoffs,
        });
        if (!progress) {
          return createErrorResponse(`mission not found: ${mission_id}`);
        }
        return createJsonResponse(progress);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
