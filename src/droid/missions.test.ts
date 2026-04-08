/**
 * Unit tests for mission directory reading and polling.
 *
 * Uses a temp directory as a fake ~/.factory/missions/ so we can
 * deterministically exercise scenarios (mismatched working_directory.txt,
 * state.json present/absent, etc.) without spawning real droid missions.
 */

import { spawn } from "node:child_process";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  getMissionProgress,
  getMissionStatus,
  killProcessGracefully,
  listMissions,
  markMissionState,
  pollForNewMissionDir,
  resolveMissionDir,
} from "./missions.js";

let tmpMissions: string;

beforeEach(async () => {
  tmpMissions = await mkdtemp(join(tmpdir(), "mcp-droid-missions-test-"));
});

afterEach(async () => {
  await rm(tmpMissions, { recursive: true, force: true });
});

async function createMissionDir(
  uuid: string,
  workingDirectory: string,
  extras: { missionMd?: string } = {},
): Promise<void> {
  const dir = join(tmpMissions, uuid);
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, "working_directory.txt"), workingDirectory);
  if (extras.missionMd) {
    await writeFile(join(dir, "mission.md"), extras.missionMd);
  }
}

interface FullMissionFiles {
  state?: Record<string, unknown>;
  missionMd?: string;
  features?: { features: Array<Record<string, unknown>> };
  progressLog?: Array<Record<string, unknown>>;
}

/** Create a complete mission dir with state.json + supporting files. */
async function createFullMissionDir(
  uuid: string,
  files: FullMissionFiles,
): Promise<void> {
  const dir = join(tmpMissions, uuid);
  await mkdir(dir, { recursive: true });
  if (files.state) {
    await writeFile(join(dir, "state.json"), JSON.stringify(files.state));
    if (typeof files.state.workingDirectory === "string") {
      await writeFile(
        join(dir, "working_directory.txt"),
        files.state.workingDirectory,
      );
    }
  }
  if (files.missionMd) {
    await writeFile(join(dir, "mission.md"), files.missionMd);
  }
  if (files.features) {
    await writeFile(join(dir, "features.json"), JSON.stringify(files.features));
  }
  if (files.progressLog) {
    await writeFile(
      join(dir, "progress_log.jsonl"),
      files.progressLog.map((e) => JSON.stringify(e)).join("\n"),
    );
  }
}

const sampleState = (overrides: Record<string, unknown> = {}) => ({
  missionId: "mis_abc123",
  baseSessionId: "session-uuid-1",
  state: "running",
  workingDirectory: "/Users/serkan/nt-dev",
  currentFeatureId: "feat-1",
  currentWorkerSessionId: "worker-1",
  currentWorkerPid: 12345,
  workerSessionIds: ["worker-1"],
  completedFeatures: 2,
  totalFeatures: 5,
  createdAt: "2026-04-01T10:00:00.000Z",
  updatedAt: "2026-04-01T11:00:00.000Z",
  ...overrides,
});

describe("pollForNewMissionDir", () => {
  it("returns matched_expected_cwd=true when a new dir's working_directory.txt matches spawn cwd", async () => {
    const beforeUuids = new Set<string>();
    // Create the matching mission dir before starting the poll to simulate
    // "droid already created the dir before we started polling".
    await createMissionDir("mission-a", "/Users/serkan/nt-dev");

    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 2000,
        interval_ms: 50,
        missions_dir: tmpMissions,
      },
    );

    expect(result).not.toBeNull();
    expect(result?.uuid).toBe("mission-a");
    expect(result?.working_directory).toBe("/Users/serkan/nt-dev");
    expect(result?.matched_expected_cwd).toBe(true);
  });

  it("skips directories that existed before (beforeUuids set)", async () => {
    // Simulate a mission dir that already existed when we started polling.
    await createMissionDir("existing", "/Users/serkan/nt-dev");
    const beforeUuids = new Set(["existing"]);

    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 500,
        interval_ms: 50,
        missions_dir: tmpMissions,
      },
    );

    // No new dir to find → timeout → null
    expect(result).toBeNull();
  });

  it("returns the fallback (matched_expected_cwd=false) when a new dir has a different working_directory.txt and fallback_hold_ms elapses", async () => {
    const beforeUuids = new Set<string>();
    await createMissionDir("mission-b", "/tmp/somewhere-else");

    // fallback_hold_ms=100 means: after 100ms of seeing the fallback
    // without a better match, return it.
    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 2000,
        interval_ms: 20,
        fallback_hold_ms: 100,
        missions_dir: tmpMissions,
      },
    );

    expect(result).not.toBeNull();
    expect(result?.uuid).toBe("mission-b");
    expect(result?.working_directory).toBe("/tmp/somewhere-else");
    expect(result?.matched_expected_cwd).toBe(false);
  });

  it("prefers the exact match if both a match and a fallback appear in the same poll tick", async () => {
    const beforeUuids = new Set<string>();
    // Create both simultaneously — the exact match must win regardless
    // of readdir order.
    await createMissionDir("mission-mismatch", "/tmp/wrong");
    await createMissionDir("mission-match", "/Users/serkan/nt-dev");

    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 2000,
        interval_ms: 50,
        missions_dir: tmpMissions,
      },
    );

    expect(result?.uuid).toBe("mission-match");
    expect(result?.matched_expected_cwd).toBe(true);
  });

  it("skips dirs without working_directory.txt but still catches them on a later tick", async () => {
    const beforeUuids = new Set<string>();

    // Create an incomplete mission dir (no working_directory.txt yet).
    const incompleteDir = join(tmpMissions, "mission-slow");
    await mkdir(incompleteDir);

    // Start polling in the background.
    const pollPromise = pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 2000,
        interval_ms: 50,
        missions_dir: tmpMissions,
      },
    );

    // After 100ms, write the working_directory.txt so the next tick
    // catches it.
    await new Promise((resolve) => setTimeout(resolve, 100));
    await writeFile(
      join(incompleteDir, "working_directory.txt"),
      "/Users/serkan/nt-dev",
    );

    const result = await pollPromise;
    expect(result?.uuid).toBe("mission-slow");
    expect(result?.matched_expected_cwd).toBe(true);
  });

  it("returns null if no new directories appear within timeout", async () => {
    const beforeUuids = new Set<string>();
    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 300,
        interval_ms: 50,
        missions_dir: tmpMissions,
      },
    );
    expect(result).toBeNull();
  });

  it("returns a fallback at timeout even if fallback_hold_ms hasn't elapsed", async () => {
    const beforeUuids = new Set<string>();

    // Create the fallback right before timeout so fallback_hold_ms
    // hasn't passed yet when the timeout hits.
    setTimeout(() => {
      void createMissionDir("mission-late", "/tmp/elsewhere");
    }, 150);

    const result = await pollForNewMissionDir(
      beforeUuids,
      "/Users/serkan/nt-dev",
      {
        timeout_ms: 400,
        interval_ms: 50,
        fallback_hold_ms: 10_000, // intentionally longer than timeout
        missions_dir: tmpMissions,
      },
    );

    expect(result).not.toBeNull();
    expect(result?.uuid).toBe("mission-late");
    expect(result?.matched_expected_cwd).toBe(false);
  });
});

describe("listMissions (via state.json fast path + working_directory.txt slow path)", () => {
  it("returns an empty array when the missions dir does not exist", async () => {
    const result = await listMissions({ missions_dir: join(tmpMissions, "nope") });
    expect(result).toEqual([]);
  });

  it("returns missions with full state.json populated", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState({ missionId: "mis_one" }),
      missionMd: "# First Mission\n\nDoes things",
    });
    const result = await listMissions({ missions_dir: tmpMissions, all: true });
    expect(result).toHaveLength(1);
    expect(result[0]?.mission_id).toBe("mis_one");
    expect(result[0]?.uuid).toBe("uuid-1");
    expect(result[0]?.state).toBe("running");
    expect(result[0]?.completed_features).toBe(2);
    expect(result[0]?.total_features).toBe(5);
    expect(result[0]?.title).toBe("First Mission");
  });

  it("returns 'pending-<uuid>' state for partial missions (no state.json yet)", async () => {
    // Only working_directory.txt + mission.md — no state.json. This is the
    // freshly-spawned mission lifecycle stage.
    await createMissionDir("uuid-pending", "/Users/serkan/foo", {
      missionMd: "# Pending Mission",
    });
    const result = await listMissions({ missions_dir: tmpMissions, all: true });
    expect(result).toHaveLength(1);
    expect(result[0]?.mission_id).toBe("pending-uuid-pending");
    expect(result[0]?.state).toBe("initializing");
    expect(result[0]?.working_directory).toBe("/Users/serkan/foo");
    expect(result[0]?.title).toBe("Pending Mission");
  });

  it("filters by exact cwd when not all=true", async () => {
    await createFullMissionDir("uuid-a", {
      state: sampleState({ workingDirectory: "/Users/serkan/nt-dev" }),
    });
    await createFullMissionDir("uuid-b", {
      state: sampleState({ workingDirectory: "/Users/serkan/hetzner" }),
    });
    const result = await listMissions({
      missions_dir: tmpMissions,
      cwd: "/Users/serkan/nt-dev",
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.uuid).toBe("uuid-a");
  });

  it("filters by state when state option is given", async () => {
    await createFullMissionDir("uuid-running", {
      state: sampleState({ state: "running" }),
    });
    await createFullMissionDir("uuid-paused", {
      state: sampleState({ state: "paused" }),
    });
    const result = await listMissions({
      missions_dir: tmpMissions,
      all: true,
      state: "paused",
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.state).toBe("paused");
  });

  it("sorts by updated_at descending", async () => {
    await createFullMissionDir("uuid-old", {
      state: sampleState({
        missionId: "mis_old",
        updatedAt: "2026-01-01T00:00:00.000Z",
      }),
    });
    await createFullMissionDir("uuid-new", {
      state: sampleState({
        missionId: "mis_new",
        updatedAt: "2026-04-01T00:00:00.000Z",
      }),
    });
    const result = await listMissions({ missions_dir: tmpMissions, all: true });
    expect(result.map((m) => m.mission_id)).toEqual(["mis_new", "mis_old"]);
  });

  it("respects the limit option", async () => {
    for (let i = 0; i < 5; i++) {
      await createFullMissionDir(`uuid-${i}`, {
        state: sampleState({
          missionId: `mis_${i}`,
          updatedAt: `2026-04-0${i + 1}T00:00:00.000Z`,
        }),
      });
    }
    const result = await listMissions({
      missions_dir: tmpMissions,
      all: true,
      limit: 2,
    });
    expect(result).toHaveLength(2);
    // Loop creates mis_0..mis_4 with strictly increasing updatedAt;
    // newest first → mis_4, then mis_3 (limited to 2).
    expect(result[0]?.mission_id).toBe("mis_4");
    expect(result[1]?.mission_id).toBe("mis_3");
  });

  it("skips entries that are neither valid mission dirs nor have working_directory.txt", async () => {
    // Create a stray file (not a directory) under the missions dir.
    await writeFile(join(tmpMissions, "stray-file.txt"), "not a mission");
    // And a directory that's not a mission (no state.json, no wd txt).
    await mkdir(join(tmpMissions, "not-a-mission"));

    const result = await listMissions({ missions_dir: tmpMissions, all: true });
    expect(result).toEqual([]);
  });
});

describe("resolveMissionDir", () => {
  it("returns the uuid when given a directory name that exists", async () => {
    await createFullMissionDir("uuid-x", {
      state: sampleState({ missionId: "mis_x" }),
    });
    const result = await resolveMissionDir("uuid-x", tmpMissions);
    expect(result).toBe("uuid-x");
  });

  it("returns the uuid when given a mission_id that maps to it", async () => {
    await createFullMissionDir("uuid-x", {
      state: sampleState({ missionId: "mis_target" }),
    });
    const result = await resolveMissionDir("mis_target", tmpMissions);
    expect(result).toBe("uuid-x");
  });

  it("returns null when neither a directory nor a mission_id matches", async () => {
    await createFullMissionDir("uuid-x", {
      state: sampleState({ missionId: "mis_x" }),
    });
    const result = await resolveMissionDir("nonexistent", tmpMissions);
    expect(result).toBeNull();
  });

  it("returns null when the missions directory does not exist", async () => {
    const result = await resolveMissionDir(
      "any",
      join(tmpMissions, "nonexistent"),
    );
    expect(result).toBeNull();
  });
});

describe("getMissionStatus", () => {
  it("returns null for an unknown mission_id", async () => {
    const result = await getMissionStatus("nope", { missions_dir: tmpMissions });
    expect(result).toBeNull();
  });

  it("returns the full status with features and recent_events by default", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      features: {
        features: [
          { id: "f1", milestone: "m1", status: "done" },
          { id: "f2", milestone: "m1", status: "pending", description: "long" },
        ],
      },
      progressLog: [
        { timestamp: "2026-04-01T10:00:00Z", type: "mission_accepted" },
        { timestamp: "2026-04-01T10:01:00Z", type: "worker_started" },
      ],
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
    });
    expect(result?.mission_id).toBe("mis_abc123");
    expect(result?.features).toHaveLength(2);
    // description should be stripped from feature output
    expect(result?.features?.[1]).not.toHaveProperty("description");
    expect(result?.recent_events).toHaveLength(2);
    expect(result?.recent_events?.[1]?.type).toBe("worker_started");
  });

  it("respects progress_limit by tail-slicing the events", async () => {
    const events = Array.from({ length: 50 }, (_, i) => ({
      timestamp: `2026-04-01T10:${String(i).padStart(2, "0")}:00Z`,
      type: `event_${i}`,
    }));
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: events,
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
      progress_limit: 5,
    });
    expect(result?.recent_events).toHaveLength(5);
    expect(result?.recent_events?.[0]?.type).toBe("event_45");
    expect(result?.recent_events?.[4]?.type).toBe("event_49");
  });

  it("summarizes worker_completed handoffs by default", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        {
          timestamp: "2026-04-01T10:00:00Z",
          type: "worker_completed",
          handoff: {
            salientSummary: "did the thing",
            whatWasImplemented: "lots of details ".repeat(50),
          },
        },
      ],
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
    });
    const event = result?.recent_events?.[0] as Record<string, unknown>;
    expect(event).not.toHaveProperty("handoff");
    expect(event.handoff_summary).toBeDefined();
    const summary = event.handoff_summary as Record<string, unknown>;
    expect(summary.summary).toBe("did the thing");
    expect((summary.what_implemented as string).length).toBe(200);
  });

  it("returns the full handoff when include_handoffs=true", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        {
          timestamp: "2026-04-01T10:00:00Z",
          type: "worker_completed",
          handoff: { salientSummary: "did it", whatWasImplemented: "details" },
        },
      ],
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
      include_handoffs: true,
    });
    const event = result?.recent_events?.[0] as Record<string, unknown>;
    expect(event.handoff).toBeDefined();
    expect(event).not.toHaveProperty("handoff_summary");
  });

  it("omits features when include_features=false", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      features: { features: [{ id: "f1" }] },
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
      include_features: false,
    });
    expect(result?.features).toBeUndefined();
  });

  it("omits recent_events when include_progress=false", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [{ timestamp: "x", type: "y" }],
    });
    const result = await getMissionStatus("uuid-1", {
      missions_dir: tmpMissions,
      include_progress: false,
    });
    expect(result?.recent_events).toBeUndefined();
  });

  it("works on a partial-state (no state.json) mission", async () => {
    await createMissionDir("uuid-pending", "/Users/serkan/foo", {
      missionMd: "# Pending",
    });
    const result = await getMissionStatus("uuid-pending", {
      missions_dir: tmpMissions,
    });
    expect(result?.mission_id).toBe("pending-uuid-pending");
    expect(result?.state).toBe("initializing");
    expect(result?.title).toBe("Pending");
  });
});

describe("getMissionProgress", () => {
  it("returns null for an unknown mission_id", async () => {
    const result = await getMissionProgress("nope", {
      missions_dir: tmpMissions,
    });
    expect(result).toBeNull();
  });

  it("returns events from since_offset", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        { timestamp: "2026-04-01T10:00:00Z", type: "a" },
        { timestamp: "2026-04-01T10:01:00Z", type: "b" },
        { timestamp: "2026-04-01T10:02:00Z", type: "c" },
        { timestamp: "2026-04-01T10:03:00Z", type: "d" },
      ],
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
      since_offset: 2,
    });
    expect(result?.events.map((e) => e.type)).toEqual(["c", "d"]);
    expect(result?.next_offset).toBe(4);
  });

  it("returns events strictly after since_timestamp", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        { timestamp: "2026-04-01T10:00:00Z", type: "a" },
        { timestamp: "2026-04-01T10:01:00Z", type: "b" },
        { timestamp: "2026-04-01T10:02:00Z", type: "c" },
      ],
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
      since_timestamp: "2026-04-01T10:00:30Z",
    });
    expect(result?.events.map((e) => e.type)).toEqual(["b", "c"]);
  });

  it("filters by event_types when given", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        { timestamp: "1", type: "worker_started" },
        { timestamp: "2", type: "worker_completed" },
        { timestamp: "3", type: "worker_failed" },
      ],
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
      event_types: ["worker_failed", "worker_started"],
    });
    expect(result?.events.map((e) => e.type)).toEqual([
      "worker_started",
      "worker_failed",
    ]);
  });

  it("respects the limit option", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: Array.from({ length: 10 }, (_, i) => ({
        timestamp: String(i),
        type: `t${i}`,
      })),
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
      limit: 3,
    });
    expect(result?.events).toHaveLength(3);
  });

  it("reports is_complete=true when state is in TERMINAL_STATES", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState({ state: "completed" }),
      progressLog: [{ timestamp: "1", type: "x" }],
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
    });
    expect(result?.is_complete).toBe(true);
  });

  it("reports is_complete=false for an active mission", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState({ state: "running" }),
      progressLog: [{ timestamp: "1", type: "x" }],
    });
    const result = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
    });
    expect(result?.is_complete).toBe(false);
  });

  it("summarizes handoffs by default but keeps them when exclude_handoffs=false", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState(),
      progressLog: [
        {
          timestamp: "1",
          type: "worker_completed",
          handoff: { salientSummary: "yes" },
        },
      ],
    });
    const summarized = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
    });
    expect(summarized?.events[0]).not.toHaveProperty("handoff");

    const unsummarized = await getMissionProgress("uuid-1", {
      missions_dir: tmpMissions,
      exclude_handoffs: false,
    });
    expect(unsummarized?.events[0]).toHaveProperty("handoff");
  });
});

describe("markMissionState", () => {
  it("returns false when the mission dir doesn't exist", async () => {
    const result = await markMissionState("nope", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(result).toBe(false);
  });

  // (the "returns false when state.json is missing" test was deleted
  //  — that behavior was a bug, fixed by the synthesis path below)

  it("writes the new state + resets transient fields + updates timestamp", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState({
        state: "running",
        currentFeatureId: "f1",
        currentWorkerSessionId: "worker-session-1",
        currentWorkerPid: 12345,
      }),
    });
    const before = Date.now();
    const result = await markMissionState("uuid-1", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(result).toBe(true);

    const raw = await readFile(
      join(tmpMissions, "uuid-1", "state.json"),
      "utf8",
    );
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    expect(parsed.state).toBe("cancelled");
    expect(parsed.currentFeatureId).toBeNull();
    expect(parsed.currentWorkerSessionId).toBeNull();
    expect(parsed.currentWorkerPid).toBeNull();
    // updatedAt should be a fresh ISO timestamp, within seconds of `before`.
    const updatedAtMs = Date.parse(parsed.updatedAt as string);
    expect(updatedAtMs).toBeGreaterThanOrEqual(before - 100);
    expect(updatedAtMs).toBeLessThanOrEqual(Date.now() + 100);
  });

  it("preserves mission_id and other identifying fields", async () => {
    await createFullMissionDir("uuid-1", {
      state: sampleState({ missionId: "mis_preserved" }),
    });
    await markMissionState("uuid-1", "cancelled", {
      missions_dir: tmpMissions,
    });
    const parsed = JSON.parse(
      await readFile(join(tmpMissions, "uuid-1", "state.json"), "utf8"),
    ) as Record<string, unknown>;
    expect(parsed.missionId).toBe("mis_preserved");
  });

  it("returns false when state.json is corrupt JSON", async () => {
    const dir = join(tmpMissions, "broken");
    await mkdir(dir, { recursive: true });
    await writeFile(join(dir, "working_directory.txt"), "/x");
    await writeFile(join(dir, "state.json"), "not json {{");
    const result = await markMissionState("broken", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(result).toBe(false);
  });

  it("SYNTHESIZES a new state.json from working_directory.txt when state.json is missing", async () => {
    // Partial-mission case: droid created the directory with
    // working_directory.txt + mission.md but factoryd hasn't yet
    // written state.json. Cancel must handle this by creating
    // state.json from scratch, otherwise the mission gets stuck at
    // whatever readStateJson's slow-path returns (initializing).
    await createMissionDir("pending-cancel", "/Users/serkan/foo", {
      missionMd: "# Pending Mission",
    });
    // Confirm there's no state.json to start
    await expect(
      readFile(join(tmpMissions, "pending-cancel", "state.json"), "utf8"),
    ).rejects.toThrow();

    const result = await markMissionState("pending-cancel", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(result).toBe(true);

    // Now verify state.json exists with the synthesized shape
    const raw = await readFile(
      join(tmpMissions, "pending-cancel", "state.json"),
      "utf8",
    );
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    expect(parsed.state).toBe("cancelled");
    expect(parsed.workingDirectory).toBe("/Users/serkan/foo");
    expect(parsed.missionId).toBe("pending-pending-cancel");
    expect(parsed.currentFeatureId).toBeNull();
    expect(parsed.currentWorkerSessionId).toBeNull();
    expect(parsed.currentWorkerPid).toBeNull();
    expect(parsed.workerSessionIds).toEqual([]);
    expect(parsed.completedFeatures).toBe(0);
    expect(parsed.totalFeatures).toBe(0);
    expect(typeof parsed.createdAt).toBe("string");
    expect(typeof parsed.updatedAt).toBe("string");
  });

  it("downstream: getMissionStatus reads the synthesized state as state=cancelled", async () => {
    // End-to-end: synthesize state.json via markMissionState, then
    // verify listMissions / getMissionStatus report the new state.
    await createMissionDir("e2e-cancel", "/Users/serkan/bar", {
      missionMd: "# E2E Mission",
    });
    const wrote = await markMissionState("e2e-cancel", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(wrote).toBe(true);

    const { getMissionStatus, listMissions } = await import("./missions.js");
    const status = await getMissionStatus("e2e-cancel", {
      missions_dir: tmpMissions,
      include_progress: false,
      include_features: false,
    });
    expect(status?.state).toBe("cancelled");
    expect(status?.working_directory).toBe("/Users/serkan/bar");

    const list = await listMissions({
      missions_dir: tmpMissions,
      all: true,
      state: "cancelled",
    });
    expect(list).toHaveLength(1);
    expect(list[0]?.uuid).toBe("e2e-cancel");
  });

  it("returns false when the mission directory doesn't exist at all", async () => {
    // No directory means no working_directory.txt, no way to
    // synthesize anything meaningful.
    const result = await markMissionState("ghost", "cancelled", {
      missions_dir: tmpMissions,
    });
    expect(result).toBe(false);
  });
});

describe("killProcessGracefully", () => {
  it("returns { killed: false, reason: 'process not running' } for a nonexistent pid", async () => {
    // PID 1 is init/launchd; 999999 is very unlikely to exist.
    const result = await killProcessGracefully(999999, { graceful_ms: 100 });
    expect(result.killed).toBe(false);
    expect(result.required_sigkill).toBe(false);
    expect(result.reason).toContain("not running");
  });

  it("gracefully kills a child process that respects SIGTERM", async () => {
    // Spawn a Node process that handles SIGTERM and exits cleanly.
    const child = spawn("node", [
      "-e",
      "process.on('SIGTERM', () => process.exit(0)); setInterval(() => {}, 1000);",
    ]);
    expect(child.pid).toBeDefined();

    // Give it a moment to register its SIGTERM handler.
    await new Promise<void>((resolve) => setTimeout(resolve, 100));

    const result = await killProcessGracefully(child.pid!, {
      graceful_ms: 2_000,
    });
    expect(result.killed).toBe(true);
    expect(result.required_sigkill).toBe(false);
  });

  it("escalates to SIGKILL when SIGTERM is ignored", async () => {
    // Spawn a Node process that explicitly ignores SIGTERM.
    const child = spawn("node", [
      "-e",
      "process.on('SIGTERM', () => { /* ignore */ }); setInterval(() => {}, 1000);",
    ]);
    expect(child.pid).toBeDefined();

    // Give it a moment to register the SIGTERM handler.
    await new Promise<void>((resolve) => setTimeout(resolve, 100));

    const result = await killProcessGracefully(child.pid!, {
      graceful_ms: 300,
      check_interval_ms: 50,
    });
    expect(result.killed).toBe(true);
    expect(result.required_sigkill).toBe(true);
  });

  it("force:true skips SIGTERM entirely and sends SIGKILL immediately", async () => {
    // Spawn a Node process that handles SIGTERM by exiting with a
    // SPECIFIC non-zero code (7) so we can detect whether it received
    // SIGTERM or just SIGKILL.
    //
    // Note: SIGKILL can't be trapped by the process, so its exit
    // isn't observable from the child's own handler — we detect it
    // via the parent tracking the exit code/signal of the child.
    const child = spawn("node", [
      "-e",
      "process.on('SIGTERM', () => process.exit(7)); setInterval(() => {}, 1000);",
    ]);
    expect(child.pid).toBeDefined();

    // Capture the exit signal/code
    let exitCode: number | null = null;
    let exitSignal: NodeJS.Signals | null = null;
    const exitPromise = new Promise<void>((resolve) => {
      child.on("exit", (code, signal) => {
        exitCode = code;
        exitSignal = signal;
        resolve();
      });
    });

    // Give the SIGTERM handler a moment to register
    await new Promise<void>((resolve) => setTimeout(resolve, 100));

    const result = await killProcessGracefully(child.pid!, { force: true });
    await exitPromise;

    expect(result.killed).toBe(true);
    expect(result.required_sigkill).toBe(true);
    // If SIGTERM had been sent first, the child would exit with code 7.
    // If SIGKILL was sent directly (as force:true should), the exit
    // signal should be SIGKILL with no code.
    expect(exitSignal).toBe("SIGKILL");
    expect(exitCode).toBeNull();
  });
});
