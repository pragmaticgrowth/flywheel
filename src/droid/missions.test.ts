/**
 * Unit tests for mission directory reading and polling.
 *
 * Uses a temp directory as a fake ~/.factory/missions/ so we can
 * deterministically exercise scenarios (mismatched working_directory.txt,
 * state.json present/absent, etc.) without spawning real droid missions.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pollForNewMissionDir } from "./missions.js";

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
