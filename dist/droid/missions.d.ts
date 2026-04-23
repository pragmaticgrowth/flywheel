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
export declare function missionStateFile(uuid: string, baseDir?: string): string;
export interface PollForNewMissionResult {
    uuid: string;
    working_directory: string;
    matched_expected_cwd: boolean;
}
/**
 * Poll ~/.factory/missions/ for a new mission directory. Returns the
 * first match AS SOON AS one is found. Polls every `interval_ms`
 * (default 500 ms) until timeout_ms.
 *
 * Matching rules (in order of preference):
 *
 *   1. A new uuid (not in beforeUuids) whose working_directory.txt
 *      content EQUALS `expectedCwd`. This is the ideal case: we spawned
 *      droid in cwd X and droid created a mission with working
 *      directory X. Return immediately with matched_expected_cwd=true.
 *
 *   2. A new uuid whose working_directory.txt is populated with
 *      ANYTHING — droid can set a different working directory based on
 *      paths it sees in the prompt (verified: prompt mentioning
 *      "/tmp/foo/step1.txt" causes droid to set wd=/tmp/foo, not our
 *      spawn cwd). Remember as a fallback and keep looking briefly
 *      for the exact match, but return the fallback if no exact
 *      match appears. matched_expected_cwd=false.
 *
 *   3. A new uuid with no working_directory.txt yet (file still being
 *      written). Skip it this tick and retry next tick — the file
 *      appears within the same ~1s window that the directory is created.
 *
 *  After `fallback_hold_ms` from first sighting a fallback, commit
 *  to it rather than waiting forever for a perfect match. Default 5 s.
 */
export declare function pollForNewMissionDir(beforeUuids: ReadonlySet<string>, expectedCwd: string, opts?: {
    timeout_ms?: number;
    interval_ms?: number;
    fallback_hold_ms?: number;
    missions_dir?: string;
}): Promise<PollForNewMissionResult | null>;
export interface ListMissionsOptions {
    cwd?: string;
    all?: boolean;
    state?: string;
    limit?: number;
    missions_dir?: string;
}
export declare function listMissions(opts?: ListMissionsOptions): Promise<MissionState[]>;
/**
 * Resolve a user-provided id (either mis_xxx or a directory uuid) to the
 * on-disk directory uuid.
 */
export declare function resolveMissionDir(idOrUuid: string, missions_dir?: string): Promise<string | null>;
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
export declare function getMissionStatus(idOrUuid: string, opts?: GetMissionStatusOptions): Promise<MissionStatus | null>;
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
/**
 * Best-effort process kill.
 *
 * Default path (force=false): SIGTERM → wait up to gracefulMs →
 * SIGKILL if still alive. Returns `required_sigkill: false` when
 * SIGTERM was enough, `true` when we had to escalate.
 *
 * Force path (force=true): skip SIGTERM entirely and send SIGKILL
 * immediately. Always reports `required_sigkill: true`. Use for
 * processes that ignore SIGTERM or when you need instant cleanup.
 *
 * Never throws — all errors are folded into the result object.
 *
 * `process.kill(pid, 0)` is the standard Node trick for "check whether
 * this pid exists without signalling it" — it throws ESRCH if the
 * process is gone, no-ops if it's alive.
 */
export declare function killProcessGracefully(pid: number, opts?: {
    graceful_ms?: number;
    check_interval_ms?: number;
    force?: boolean;
}): Promise<{
    killed: boolean;
    required_sigkill: boolean;
    reason?: string;
}>;
/**
 * Mark a mission's state by writing state.json. Create-or-update:
 *
 *   - If state.json already exists and parses, update its state field
 *     + updatedAt + null out the transient currentFeatureId /
 *     currentWorkerSessionId / currentWorkerPid. Preserves
 *     missionId, baseSessionId, workerSessionIds, feature counts,
 *     createdAt.
 *
 *   - If state.json doesn't exist (early-stage mission: directory
 *     has only working_directory.txt + mission.md + progress_log.jsonl
 *     because factoryd hasn't spawned a worker yet), synthesize a
 *     minimal state.json from working_directory.txt + the directory's
 *     birthtime. missionId becomes "pending-<uuid>" to match the
 *     convention in readStateJson's slow path.
 *
 *   - If neither state.json nor working_directory.txt exists, or if
 *     the mission directory itself is missing, return false without
 *     writing anything (can't synthesize a meaningful state file with
 *     no ground truth).
 *
 *   - If state.json exists but is corrupt JSON, also return false
 *     rather than silently overwriting the corrupt file (caller
 *     should investigate).
 *
 * WARNING: if the mission orchestrator is still alive when this is
 * called, it may overwrite state.json again (or the synthesized file
 * we just wrote). Always kill the orchestrator FIRST, then write
 * state. droid_mission_cancel follows that ordering.
 */
export declare function markMissionState(uuid: string, newState: string, opts?: {
    missions_dir?: string;
}): Promise<boolean>;
export declare function getMissionProgress(idOrUuid: string, opts?: GetMissionProgressOptions): Promise<MissionProgressResult | null>;
