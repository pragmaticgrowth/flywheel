/**
 * Mission tools: start, list, status, progress. droid_mission_cancel is
 * intentionally NOT implemented in v1 — cancellation semantics need
 * investigation (spec §6.3).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { spawn } from "node:child_process";
import { closeSync, openSync } from "node:fs";
import { tmpdir } from "node:os";
import { join as joinPath } from "node:path";
import { z } from "zod";
import { DEFAULT_MODEL } from "../droid/defaults.js";
import { buildDroidExecArgs, type DroidExecFlags } from "../droid/flags.js";
import {
  getMissionProgress,
  getMissionStatus,
  listMissions,
  missionStateFile,
  pollForNewMissionDir,
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
        "Start a new droid mission — spawns `droid exec --mission` as a DETACHED background process and polls ~/.factory/missions/ for the new directory. Returns as soon as the directory appears (typically 10–30 seconds), leaving the mission running independently. The mission directory is recognized by its working_directory.txt file (which droid writes BEFORE state.json — state.json may not exist for many seconds, sometimes never). IMPORTANT: droid only triggers real mission orchestration for SUBSTANTIAL prompts (multi-feature work, refactors, implementations). Trivial prompts ('say hi') complete as a plain exec and never create a mission directory — the tool detects this and returns mission_triggered=false. Poll progress later with droid_mission_status / droid_mission_progress using the returned uuid.",
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
            "How long to wait for the new mission directory to appear before giving up. The mission keeps running in the background after this returns either way. Default 120 seconds.",
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
        const pollTimeout = timeout_ms ?? 120_000;

        // Snapshot existing mission uuids — anything new during the poll
        // window with our cwd is our mission.
        const beforeUuids = new Set(
          (await listMissions({ all: true, limit: 100_000 })).map((m) => m.uuid),
        );

        // Build droid exec argv ourselves so we can spawn detached.
        // spawnDroidExec helper awaits process exit, which would block
        // for the entire mission duration (minutes to hours).
        const flags: DroidExecFlags = {
          prompt,
          model: model ?? DEFAULT_MODEL,
          mission: true,
          output_format: "stream-json",
          ...(allow_unsafe ? { allow_unsafe: true } : { auto: "high" }),
          tags,
        };
        const argv = ["exec", ...buildDroidExecArgs(flags)];

        // Log stdout/stderr to disk — detached children can't inherit our pipes.
        const logPath = joinPath(
          tmpdir(),
          `mcp-droid-mission-${Date.now()}.log`,
        );
        const logFd = openSync(logPath, "w");

        const child = spawn("droid", argv, {
          cwd: resolvedCwd,
          env: process.env,
          stdio: ["ignore", logFd, logFd],
          detached: true,
        });
        // The child has dup'd logFd into its own stdout/stderr; the parent's
        // copy is no longer needed and would otherwise leak one fd per call.
        closeSync(logFd);
        // unref() lets the parent (mcp-droid server) exit independently of
        // the mission. The mission keeps running under launchd / init.
        child.unref();
        let spawnError: string | null = null;
        child.on("error", (err) => {
          spawnError = `failed to spawn droid: ${err.message}`;
        });

        // Poll for the new mission directory. The polling logic accepts
        // ANY new mission dir — droid can set a different working
        // directory than our spawn cwd if the prompt contains absolute
        // paths (verified with a prompt mentioning /tmp/foo/step1.txt —
        // droid set wd=/tmp/foo, not our spawn cwd). Exact cwd match is
        // preferred but not required.
        const poll = await pollForNewMissionDir(beforeUuids, resolvedCwd, {
          timeout_ms: pollTimeout,
          interval_ms: 500,
        });

        if (!poll) {
          return createJsonResponse({
            mission_triggered: false,
            reason: spawnError
              ? `spawn failed: ${spawnError}`
              : "no new mission directory appeared within the poll window. Common cause: prompt was too trivial to trigger multi-feature orchestration. Try a prompt that explicitly asks for multi-feature planning (e.g. 'use ProposeMission with 3 features...'). Droid is running detached — check the droid_log file or ~/.factory/missions/ manually.",
            working_directory: resolvedCwd,
            droid_pid: child.pid,
            droid_log: logPath,
            poll_timeout_ms: pollTimeout,
          });
        }

        // Got a new mission. Read its current status (may have only
        // working_directory.txt + mission.md so far, no state.json yet —
        // readMissionDirState handles that gracefully).
        const status = await getMissionStatus(poll.uuid, {
          include_progress: true,
          progress_limit: 5,
        });

        return createJsonResponse({
          mission_triggered: true,
          uuid: poll.uuid,
          mission_id: status?.mission_id,
          working_directory: poll.working_directory,
          spawn_cwd: resolvedCwd,
          working_directory_matches_spawn_cwd: poll.matched_expected_cwd,
          state_file: missionStateFile(poll.uuid),
          state_file_exists_yet: status?.state !== "initializing",
          initial_status: status,
          droid_pid: child.pid,
          droid_log: logPath,
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
