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

import { spawn } from "node:child_process";
import {
  buildDroidExecArgs,
  type DroidExecFlags,
  DroidFlagsError,
} from "./flags.js";
import { parseStreamJson, type ParsedStreamJson } from "./output.js";

const DEFAULT_TIMEOUT_MS = 600_000;
const SIGKILL_GRACE_MS = 5_000;

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
export function runDroidProcess(
  argv: string[],
  opts: DroidProcessOptions = {},
): Promise<DroidProcessResult> {
  const startedAt = Date.now();
  const bin = opts.droid_bin ?? "droid";
  const timeoutMs = opts.timeout_ms ?? DEFAULT_TIMEOUT_MS;

  return new Promise<DroidProcessResult>((resolve) => {
    const child = spawn(bin, argv, {
      cwd: opts.cwd,
      env: opts.env ?? process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let sigkillTimer: NodeJS.Timeout | null = null;

    const timeoutTimer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
      sigkillTimer = setTimeout(() => {
        child.kill("SIGKILL");
      }, SIGKILL_GRACE_MS);
    }, timeoutMs);

    const finalize = (
      override: Partial<DroidProcessResult> = {},
    ): DroidProcessResult => ({
      argv,
      exit_code: null,
      signal: null,
      duration_ms: Date.now() - startedAt,
      stdout,
      stderr,
      timed_out: timedOut,
      spawn_error: null,
      ...override,
    });

    child.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
    });

    child.on("error", (err: Error) => {
      clearTimeout(timeoutTimer);
      if (sigkillTimer) clearTimeout(sigkillTimer);
      resolve(
        finalize({ spawn_error: `failed to spawn ${bin}: ${err.message}` }),
      );
    });

    child.on("close", (code, signal) => {
      clearTimeout(timeoutTimer);
      if (sigkillTimer) clearTimeout(sigkillTimer);
      resolve(finalize({ exit_code: code, signal }));
    });
  });
}

export type SpawnDroidExecOptions = DroidProcessOptions;

export type DroidExecFailure =
  | "spawn_error"
  | "nonzero_exit"
  | "stream_errors"
  | "timeout"
  | "flags_error";

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

function emptyParsed(): ParsedStreamJson {
  return { text: "", events: [], errors: [] };
}

export async function spawnDroidExec(
  flags: DroidExecFlags,
  opts: SpawnDroidExecOptions = {},
): Promise<SpawnDroidExecResult> {
  const startedAt = Date.now();

  const effectiveFlags: DroidExecFlags = {
    ...flags,
    output_format: flags.output_format ?? "stream-json",
  };

  let argv: string[];
  try {
    argv = buildDroidExecArgs(effectiveFlags);
  } catch (err) {
    const message =
      err instanceof DroidFlagsError
        ? err.message
        : err instanceof Error
          ? err.message
          : String(err);
    return {
      argv: [],
      exit_code: null,
      signal: null,
      duration_ms: Date.now() - startedAt,
      stdout: "",
      stderr: "",
      parsed: emptyParsed(),
      ok: false,
      failure: "flags_error",
      error_message: message,
    };
  }

  const proc = await runDroidProcess(["exec", ...argv], opts);

  const parsed =
    effectiveFlags.output_format === "stream-json"
      ? parseStreamJson(proc.stdout)
      : emptyParsed();

  const base: Omit<SpawnDroidExecResult, "ok" | "failure" | "error_message"> = {
    argv: proc.argv,
    exit_code: proc.exit_code,
    signal: proc.signal,
    duration_ms: proc.duration_ms,
    stdout: proc.stdout,
    stderr: proc.stderr,
    parsed,
  };

  if (proc.spawn_error !== null) {
    return { ...base, ok: false, failure: "spawn_error", error_message: proc.spawn_error };
  }
  if (proc.timed_out) {
    return {
      ...base,
      ok: false,
      failure: "timeout",
      error_message: `droid exec timed out after ${opts.timeout_ms ?? DEFAULT_TIMEOUT_MS}ms`,
    };
  }
  if (proc.exit_code !== 0) {
    return {
      ...base,
      ok: false,
      failure: "nonzero_exit",
      error_message: proc.stderr.trim() || `droid exec exited with code ${proc.exit_code}`,
    };
  }
  if (parsed.errors.length > 0) {
    const summary = parsed.errors
      .map((e) =>
        typeof e.message === "string" ? e.message : JSON.stringify(e),
      )
      .join("\n");
    return { ...base, ok: false, failure: "stream_errors", error_message: summary };
  }

  return { ...base, ok: true };
}
