/**
 * Spawn helpers for the `droid` CLI.
 *
 *   runDroidProcess(argv, opts) → low-level child_process wrapper. Buffers
 *     stdout/stderr, enforces a timeout with SIGTERM + 5s SIGKILL escalation,
 *     never throws. Used by anything that needs to run `droid <subcommand>`.
 *
 *   spawnDroidExec(flags, opts) → high-level wrapper for `droid exec`. Builds
 *     argv from typed DroidExecFlags, injects --output-format stream-json by
 *     default, parses the resulting stream-json, and returns a facts-only
 *     SpawnDroidExecResult with `ok` + a typed failure discriminator.
 */
import { type DroidExecFlags } from "./flags.js";
import { type ParsedStreamJson } from "./output.js";
export interface DroidProcessOptions {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
    timeout_ms?: number;
    droid_bin?: string;
}
export interface DroidProcessResult {
    argv: string[];
    exit_code: number | null;
    signal: NodeJS.Signals | null;
    duration_ms: number;
    stdout: string;
    stderr: string;
    timed_out: boolean;
    /** Set when child_process.spawn itself failed (binary missing, etc). */
    spawn_error: string | null;
}
/**
 * Low-level wrapper around `spawn("droid", argv, ...)`. Caller decides what
 * "success" means — this function just collects facts.
 */
export declare function runDroidProcess(argv: string[], opts?: DroidProcessOptions): Promise<DroidProcessResult>;
export type SpawnDroidExecOptions = DroidProcessOptions;
export type DroidExecFailure = "spawn_error" | "nonzero_exit" | "stream_errors" | "timeout" | "flags_error";
export interface SpawnDroidExecResult {
    argv: string[];
    exit_code: number | null;
    signal: NodeJS.Signals | null;
    duration_ms: number;
    stdout: string;
    stderr: string;
    parsed: ParsedStreamJson;
    /** Always equivalent to `failure === undefined`. */
    ok: boolean;
    failure?: DroidExecFailure;
    error_message?: string;
}
export declare function spawnDroidExec(flags: DroidExecFlags, opts?: SpawnDroidExecOptions): Promise<SpawnDroidExecResult>;
