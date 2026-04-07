/**
 * Read droid missions from `~/.factory/missions/<uuid>/`.
 *
 * Mission directory lifecycle (verified empirically by triggering a real
 * `droid exec --mission` and watching the directory):
 *
 *   t=0..N s   directory created with:
 *     - working_directory.txt    (the absolute cwd, plaintext)
 *     - mission.md               (the mission prompt + plan, markdown)
 *     - progress_log.jsonl       (one or more events, starting with
 *                                 `mission_accepted`)
 *
 *   t=N..M s   factoryd spawns workers, eventually writing:
 *     - state.json               (the structured high-level state, only
 *                                 once a worker actually runs)
 *     - features.json
 *     - handoffs/
 *     - evidence/
 *
 * The OLD code keyed off state.json existence — which meant freshly-spawned
 * missions were invisible until a worker actually wrote state.json (could
 * be many seconds, sometimes never if the mission stalls). The new code
 * recognizes a mission dir by the presence of working_directory.txt
 * (always written first) and falls back gracefully when state.json is
 * missing — so list/status work for in-flight missions too.
 */

import { readdir, readFile, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export interface MissionState {
  mission_id: string;
  uuid: string;
  base_session_id?: string;
  state: string;
  working_directory: string;
  current_feature_id: string | null;
  current_worker_session_id: string | null;
  current_worker_pid: number | null;
  worker_session_ids: string[];
  completed_features: number;
  total_features: number;
  created_at: string;
  updated_at: string;
  title?: string;
}

interface RawStateJson {
  missionId: string;
  baseSessionId?: string;
  state: string;
  workingDirectory: string;
  currentFeatureId: string | null;
  currentWorkerSessionId: string | null;
  currentWorkerPid: number | null;
  workerSessionIds?: string[];
  completedFeatures?: number;
  totalFeatures?: number;
  createdAt: string;
  updatedAt: string;
}

export interface MissionFeature {
  id: string;
  description?: string;
  milestone?: string;
  status?: string;
  [key: string]: unknown;
}

export interface MissionProgressEvent {
  timestamp: string;
  type: string;
  [key: string]: unknown;
}

export const MISSIONS_DIR_DEFAULT = join(homedir(), ".factory", "missions");

function missionsDir(override?: string): string {
  return override ?? MISSIONS_DIR_DEFAULT;
}

export function missionStateFile(uuid: string, baseDir?: string): string {
  return join(missionsDir(baseDir), uuid, "state.json");
}

async function readMissionTitle(uuid: string, baseDir: string): Promise<string | undefined> {
  try {
    const md = await readFile(join(baseDir, uuid, "mission.md"), "utf8");
    const firstLine = md.split("\n").find((l) => l.trim() !== "");
    return firstLine?.replace(/^#+\s*/, "").trim();
  } catch {
    return undefined;
  }
}

async function readWorkingDirectoryTxt(
  uuid: string,
  baseDir: string,
): Promise<string | undefined> {
  try {
    const txt = await readFile(join(baseDir, uuid, "working_directory.txt"), "utf8");
    const trimmed = txt.trim();
    return trimmed || undefined;
  } catch {
    return undefined;
  }
}

/**
 * Read a mission directory and return its high-level state. Tolerates
 * missions that haven't written state.json yet (early stage / stalled /
 * killed) by falling back to working_directory.txt + mission.md + dir
 * mtime. Returns null only if the directory has neither state.json NOR
 * working_directory.txt (meaning it's not a real mission dir at all).
 */
async function readStateJson(
  uuid: string,
  baseDir: string,
  withTitle = false,
): Promise<MissionState | null> {
  // Fast path: real state.json exists.
  let raw: string | null = null;
  try {
    raw = await readFile(join(baseDir, uuid, "state.json"), "utf8");
  } catch {
    raw = null;
  }
  if (raw !== null) {
    let parsed: RawStateJson;
    try {
      parsed = JSON.parse(raw) as RawStateJson;
    } catch {
      // state.json exists but is corrupt — fall through to the partial path.
      raw = null;
    }
    if (raw !== null) {
      const parsedAgain = JSON.parse(raw) as RawStateJson;
      const state: MissionState = {
        mission_id: parsedAgain.missionId,
        uuid,
        base_session_id: parsedAgain.baseSessionId,
        state: parsedAgain.state,
        working_directory: parsedAgain.workingDirectory,
        current_feature_id: parsedAgain.currentFeatureId,
        current_worker_session_id: parsedAgain.currentWorkerSessionId,
        current_worker_pid: parsedAgain.currentWorkerPid,
        worker_session_ids: parsedAgain.workerSessionIds ?? [],
        completed_features: parsedAgain.completedFeatures ?? 0,
        total_features: parsedAgain.totalFeatures ?? 0,
        created_at: parsedAgain.createdAt,
        updated_at: parsedAgain.updatedAt,
      };
      if (withTitle) {
        const title = await readMissionTitle(uuid, baseDir);
        if (title) state.title = title;
      }
      return state;
    }
  }

  // Slow path: state.json missing or corrupt. If working_directory.txt
  // exists, this IS a mission dir — just early-stage. Build a partial
  // MissionState from whatever's available.
  const workingDirectory = await readWorkingDirectoryTxt(uuid, baseDir);
  if (workingDirectory === undefined) {
    return null; // not a mission dir at all
  }

  let createdAtIso = "";
  let updatedAtIso = "";
  try {
    const st = await stat(join(baseDir, uuid));
    createdAtIso = st.birthtime.toISOString();
    updatedAtIso = st.mtime.toISOString();
  } catch {
    // ignore
  }

  const state: MissionState = {
    mission_id: `pending-${uuid}`,
    uuid,
    base_session_id: undefined,
    state: "initializing",
    working_directory: workingDirectory,
    current_feature_id: null,
    current_worker_session_id: null,
    current_worker_pid: null,
    worker_session_ids: [],
    completed_features: 0,
    total_features: 0,
    created_at: createdAtIso,
    updated_at: updatedAtIso,
  };
  if (withTitle) {
    const title = await readMissionTitle(uuid, baseDir);
    if (title) state.title = title;
  }
  return state;
}

/**
 * Poll ~/.factory/missions/ for a new directory whose working_directory.txt
 * matches the expected cwd. Used by droid_mission_start to detect mission
 * orchestration kicking in without waiting for state.json (which appears
 * much later, sometimes never).
 *
 * Returns the new directory uuid as soon as one is found, or null on
 * timeout. Polls every `interval_ms` (default 500 ms).
 */
export async function pollForNewMissionDir(
  beforeUuids: ReadonlySet<string>,
  expectedCwd: string,
  opts: {
    timeout_ms?: number;
    interval_ms?: number;
    missions_dir?: string;
  } = {},
): Promise<string | null> {
  const base = missionsDir(opts.missions_dir);
  const timeoutMs = opts.timeout_ms ?? 60_000;
  const intervalMs = opts.interval_ms ?? 500;
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    let entries: string[] = [];
    try {
      entries = await readdir(base);
    } catch {
      // missions dir doesn't exist yet — keep polling
    }
    for (const entry of entries) {
      if (beforeUuids.has(entry)) continue;
      const wd = await readWorkingDirectoryTxt(entry, base);
      if (wd === expectedCwd) {
        return entry;
      }
    }
    // Brief sleep before next poll
    await new Promise<void>((resolve) => setTimeout(resolve, intervalMs));
  }
  return null;
}

export interface ListMissionsOptions {
  cwd?: string;
  all?: boolean;
  state?: string;
  limit?: number;
  missions_dir?: string;
}

export async function listMissions(
  opts: ListMissionsOptions = {},
): Promise<MissionState[]> {
  const base = missionsDir(opts.missions_dir);
  let entries: string[];
  try {
    entries = await readdir(base);
  } catch {
    return [];
  }

  // readStateJson returns null for non-mission entries (e.g. files instead
  // of dirs, or dirs without state.json) — so we don't need an upfront stat.
  const states = await Promise.all(
    entries.map((entry) => readStateJson(entry, base, true)),
  );

  const filtered = states.filter((state): state is MissionState => {
    if (!state) return false;
    if (!opts.all && opts.cwd !== undefined && state.working_directory !== opts.cwd) {
      return false;
    }
    if (opts.state !== undefined && state.state !== opts.state) return false;
    return true;
  });

  filtered.sort(
    (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
  );

  return filtered.slice(0, opts.limit ?? 50);
}

/**
 * Resolve a user-provided id (either mis_xxx or a directory uuid) to the
 * on-disk directory uuid.
 */
export async function resolveMissionDir(
  idOrUuid: string,
  missions_dir?: string,
): Promise<string | null> {
  const base = missionsDir(missions_dir);
  try {
    const st = await stat(join(base, idOrUuid));
    if (st.isDirectory()) return idOrUuid;
  } catch {
    // not a directory name — search by mission_id
  }

  let entries: string[] = [];
  try {
    entries = await readdir(base);
  } catch {
    return null;
  }
  for (const entry of entries) {
    try {
      const raw = await readFile(join(base, entry, "state.json"), "utf8");
      const parsed = JSON.parse(raw) as { missionId?: string };
      if (parsed.missionId === idOrUuid) return entry;
    } catch {
      // ignore
    }
  }
  return null;
}

async function readFeatures(
  uuid: string,
  base: string,
): Promise<MissionFeature[]> {
  try {
    const raw = await readFile(join(base, uuid, "features.json"), "utf8");
    const parsed = JSON.parse(raw) as { features?: MissionFeature[] };
    return parsed.features ?? [];
  } catch {
    return [];
  }
}

async function readProgressLog(
  uuid: string,
  base: string,
): Promise<MissionProgressEvent[]> {
  try {
    const raw = await readFile(join(base, uuid, "progress_log.jsonl"), "utf8");
    const events: MissionProgressEvent[] = [];
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (trimmed === "") continue;
      try {
        events.push(JSON.parse(trimmed) as MissionProgressEvent);
      } catch {
        // skip malformed
      }
    }
    return events;
  } catch {
    return [];
  }
}

/**
 * Replace the giant `handoff` field on worker_completed events with a
 * compact summary — handoffs can be 10KB+ each.
 */
function summarizeHandoff(event: MissionProgressEvent): MissionProgressEvent {
  if (event.type !== "worker_completed") return event;
  const handoff = event.handoff as
    | { salientSummary?: unknown; whatWasImplemented?: unknown }
    | undefined;
  if (!handoff || typeof handoff !== "object") return event;

  const whatStr =
    typeof handoff.whatWasImplemented === "string"
      ? handoff.whatWasImplemented.slice(0, 200)
      : undefined;
  const { handoff: _drop, ...rest } = event;
  return {
    ...rest,
    handoff_summary: {
      summary:
        typeof handoff.salientSummary === "string"
          ? handoff.salientSummary
          : undefined,
      what_implemented: whatStr,
    },
  };
}

export interface GetMissionStatusOptions {
  include_progress?: boolean;
  progress_limit?: number;
  include_handoffs?: boolean;
  include_features?: boolean;
  missions_dir?: string;
}

export interface MissionStatus extends MissionState {
  features?: MissionFeature[];
  recent_events?: MissionProgressEvent[];
}

export async function getMissionStatus(
  idOrUuid: string,
  opts: GetMissionStatusOptions = {},
): Promise<MissionStatus | null> {
  const base = missionsDir(opts.missions_dir);
  const uuid = await resolveMissionDir(idOrUuid, opts.missions_dir);
  if (!uuid) return null;

  const state = await readStateJson(uuid, base, true);
  if (!state) return null;

  const status: MissionStatus = { ...state };

  if (opts.include_features !== false) {
    const features = await readFeatures(uuid, base);
    // Strip verbose description unless caller asks — keep id + milestone + status.
    status.features = features.map((f) => ({
      id: f.id,
      milestone: f.milestone,
      status: f.status,
    }));
  }

  if (opts.include_progress !== false) {
    const events = await readProgressLog(uuid, base);
    const recent = events.slice(-(opts.progress_limit ?? 20));
    status.recent_events = opts.include_handoffs
      ? recent
      : recent.map(summarizeHandoff);
  }

  return status;
}

export interface GetMissionProgressOptions {
  since_timestamp?: string;
  since_offset?: number;
  limit?: number;
  event_types?: string[];
  exclude_handoffs?: boolean;
  missions_dir?: string;
}

export interface MissionProgressResult {
  events: MissionProgressEvent[];
  next_offset: number;
  next_timestamp?: string;
  is_complete: boolean;
}

const TERMINAL_STATES = new Set(["completed", "failed", "cancelled"]);

export async function getMissionProgress(
  idOrUuid: string,
  opts: GetMissionProgressOptions = {},
): Promise<MissionProgressResult | null> {
  const base = missionsDir(opts.missions_dir);
  const uuid = await resolveMissionDir(idOrUuid, opts.missions_dir);
  if (!uuid) return null;

  const events = await readProgressLog(uuid, base);

  let startIdx = 0;
  if (typeof opts.since_offset === "number") {
    startIdx = opts.since_offset;
  } else if (opts.since_timestamp !== undefined) {
    const cutoff = Date.parse(opts.since_timestamp);
    startIdx = events.findIndex((e) => Date.parse(e.timestamp) > cutoff);
    if (startIdx === -1) startIdx = events.length;
  }

  let slice = events.slice(startIdx);
  if (opts.event_types !== undefined && opts.event_types.length > 0) {
    const set = new Set(opts.event_types);
    slice = slice.filter((e) => set.has(e.type));
  }

  const limit = opts.limit ?? 50;
  const page = slice.slice(0, limit);
  const transformed =
    opts.exclude_handoffs !== false ? page.map(summarizeHandoff) : page;

  const nextOffset = startIdx + page.length;
  const state = await readStateJson(uuid, base);
  const isComplete =
    (state !== null && TERMINAL_STATES.has(state.state)) ||
    (page.length > 0 && page[page.length - 1]?.type === "mission_completed");

  const result: MissionProgressResult = {
    events: transformed,
    next_offset: nextOffset,
    is_complete: isComplete,
  };
  const last = page[page.length - 1];
  if (last !== undefined) {
    result.next_timestamp = last.timestamp;
  }
  return result;
}
