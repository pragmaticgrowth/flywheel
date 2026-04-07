/**
 * Mission tools: start, list, status, progress.
 *
 * droid_mission_start — wraps `droid exec --mission --auto high "..."`.
 *   Captures the new mission_id by first trying the stream-json init event,
 *   then falling back to scanning ~/.factory/missions/ for a newly created
 *   directory whose workingDirectory matches our cwd.
 *
 * droid_mission_list / status / progress — all fs readers that delegate to
 * src/droid/missions.ts.
 *
 * droid_mission_cancel is intentionally NOT implemented in v1 (spec §6.3) —
 * cancellation semantics are fuzzy and need investigation.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdir, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawnDroidExec } from "../droid/exec.js";
import {
  getMissionProgress,
  getMissionStatus,
  listMissions,
  resolveMissionDir,
} from "../droid/missions.js";
import { TagSpecSchema } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createJsonResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

const MISSIONS_DIR = join(homedir(), ".factory", "missions");

export function registerMissionTools(server: McpServer): void {
  server.registerTool(
    "droid_mission_start",
    {
      description:
        "Start a new droid mission — spawns `droid exec --mission --auto high \"...\"` in the given cwd, captures the new mission_id from the stream-json init event (or falls back to a directory scan), and returns immediately with the mission metadata. The mission runs in the background; poll progress with droid_mission_status / droid_mission_progress.",
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
            "How long to wait for the init event before giving up on capturing mission_id. Default 30 seconds.",
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
        const beforeDirs = await snapshotMissionDirs();
        const initTimeout = timeout_ms ?? 30_000;

        // Run droid with --mission + the appropriate autonomy flag. We bound
        // the spawn to initTimeout — it's a mission launch, not the full
        // mission run. The mission keeps running inside factoryd after
        // we capture the id.
        const result = await spawnDroidExec(
          {
            prompt,
            model: model ?? "custom:glm-5-turbo",
            mission: true,
            ...(allow_unsafe ? { allow_unsafe: true } : { auto: "high" }),
            tags,
          },
          { cwd: resolvedCwd, timeout_ms: initTimeout },
        );

        // Primary: session_id from init event.
        let missionUuid: string | undefined;
        const sessionId = result.parsed.session_id;

        // Fallback: scan missions dir for a new directory whose
        // workingDirectory matches resolvedCwd.
        const afterDirs = await snapshotMissionDirs();
        const newDirs: string[] = [];
        for (const d of afterDirs) {
          if (!beforeDirs.has(d)) newDirs.push(d);
        }
        if (newDirs.length > 0) {
          // Find one whose state.json has workingDirectory == resolvedCwd.
          for (const dir of newDirs) {
            const status = await getMissionStatus(dir, {
              include_progress: false,
              include_features: false,
            });
            if (status && status.working_directory === resolvedCwd) {
              missionUuid = dir;
              break;
            }
          }
          if (!missionUuid) missionUuid = newDirs[0];
        }

        if (!missionUuid && sessionId) {
          // Try to resolve by baseSessionId (which equals our session_id).
          const missions = await listMissions({ cwd: resolvedCwd, all: true, limit: 200 });
          const match = missions.find((m) => m.base_session_id === sessionId);
          if (match) missionUuid = match.uuid;
        }

        if (!missionUuid) {
          return createErrorResponse(
            `mission launched but couldn't capture mission_id within ${initTimeout}ms. Check ~/.factory/missions/ for the newest directory. Spawn status: ok=${result.ok}, failure=${result.failure ?? "none"}, stderr=${result.stderr.slice(0, 300)}`,
          );
        }

        const status = await getMissionStatus(missionUuid, {
          include_progress: true,
          progress_limit: 5,
        });

        return createJsonResponse({
          mission_id: status?.mission_id,
          uuid: missionUuid,
          base_session_id: sessionId,
          working_directory: resolvedCwd,
          state_file: join(MISSIONS_DIR, missionUuid, "state.json"),
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

async function snapshotMissionDirs(): Promise<Set<string>> {
  try {
    const entries = await readdir(MISSIONS_DIR);
    const dirs = new Set<string>();
    for (const entry of entries) {
      try {
        const s = await stat(join(MISSIONS_DIR, entry));
        if (s.isDirectory()) dirs.add(entry);
      } catch {
        continue;
      }
    }
    return dirs;
  } catch {
    return new Set();
  }
}
