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
  killProcessGracefully,
  listMissions,
  markMissionState,
  missionStateFile,
  pollForNewMissionDir,
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

        // readStateJson returns mission_id="pending-<uuid>" when state.json
        // hasn't been written yet (only working_directory.txt + mission.md
        // exist). That's the authoritative signal — don't key off the
        // `state` field, since "initializing" is ALSO a real droid state
        // emitted by state.json once factoryd starts up.
        const stateJsonExists = !(
          status?.mission_id?.startsWith("pending-") ?? true
        );

        return createJsonResponse({
          mission_triggered: true,
          uuid: poll.uuid,
          mission_id: status?.mission_id,
          working_directory: poll.working_directory,
          spawn_cwd: resolvedCwd,
          working_directory_matches_spawn_cwd: poll.matched_expected_cwd,
          state_file: missionStateFile(poll.uuid),
          state_file_exists_yet: stateJsonExists,
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
    "droid_mission_cancel",
    {
      description:
        "Best-effort cancel of a running droid mission. Sends SIGTERM → (wait 2s) → SIGKILL to the orchestrator process (via droid_pid, if provided) and the current worker process (via currentWorkerPid read from state.json). Then writes state.json with state='cancelled'. IMPORTANT: droid has no official cancel API — this is a pragmatic kill + manual state update. If the orchestrator or factoryd is still alive and touching state.json, our write may race. If you didn't save the droid_pid from the original droid_mission_start call, we can only kill the current worker (if state.json has currentWorkerPid) and mark state.json cancelled. Residual factoryd-spawned processes may need manual cleanup via pkill -f droid.",
      inputSchema: {
        mission_id: z
          .string()
          .describe("The mission id (mis_xxx) OR the directory uuid."),
        droid_pid: z
          .number()
          .int()
          .positive()
          .optional()
          .describe(
            "The orchestrator pid returned by droid_mission_start. Optional but strongly recommended — without it we can only kill the currently-running worker, not the orchestrator that will spawn the next one.",
          ),
        force: z
          .boolean()
          .optional()
          .describe(
            "If true, skip SIGTERM and go straight to SIGKILL. Use for truly stuck processes that ignore SIGTERM. Default false.",
          ),
        write_state: z
          .boolean()
          .optional()
          .describe(
            "Write state.json with state='cancelled' after killing processes. Default true. Set to false if you want to preserve the raw state for investigation.",
          ),
      },
    },
    async ({
      mission_id,
      droid_pid,
      force,
      write_state,
    }): Promise<McpToolResponse> => {
      try {
        const uuid = await resolveMissionDir(mission_id);
        if (!uuid) {
          return createErrorResponse(
            `mission not found: ${mission_id}. Use droid_mission_list to see available missions.`,
          );
        }

        // Read current state for currentWorkerPid before we kill anything.
        const beforeState = await getMissionStatus(uuid, {
          include_progress: false,
          include_features: false,
        });

        const workerPid = beforeState?.current_worker_pid ?? null;
        const pidsToKill: Array<{ pid: number; role: string }> = [];
        if (typeof droid_pid === "number") {
          pidsToKill.push({ pid: droid_pid, role: "orchestrator" });
        }
        if (typeof workerPid === "number" && workerPid !== droid_pid) {
          pidsToKill.push({ pid: workerPid, role: "worker" });
        }

        const killResults = await Promise.all(
          pidsToKill.map(async ({ pid, role }) => {
            // force=true: skip SIGTERM entirely and send SIGKILL
            // immediately. Useful for processes that ignore SIGTERM
            // or when the caller wants instant teardown.
            const result = await killProcessGracefully(pid, {
              force: force === true,
              graceful_ms: 2_000,
            });
            return { pid, role, ...result };
          }),
        );

        let stateUpdated = false;
        if (write_state !== false) {
          stateUpdated = await markMissionState(uuid, "cancelled");
        }

        const warnings: string[] = [];
        if (pidsToKill.length === 0) {
          warnings.push(
            "no pids to kill: droid_pid not provided and state.json had no currentWorkerPid. Mission may still be running under factoryd — check `pgrep -f 'droid exec --mission'`.",
          );
        }
        if (write_state !== false && !stateUpdated) {
          warnings.push(
            "failed to write state.json with state='cancelled'. The mission may not show as cancelled in droid_mission_list until something else updates it.",
          );
        }

        const afterState = await getMissionStatus(uuid, {
          include_progress: false,
          include_features: false,
        });

        return createJsonResponse({
          mission_id: beforeState?.mission_id ?? `pending-${uuid}`,
          uuid,
          killed: killResults,
          state_before: beforeState?.state,
          state_after: afterState?.state,
          state_file_updated: stateUpdated,
          warnings,
        });
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
