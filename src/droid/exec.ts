/**
 * Thin wrapper around `child_process.spawn("droid", ["exec", ...])` that:
 *   - builds argv from a typed DroidExecFlags object (via flags.ts)
 *   - injects `--output-format stream-json` as the default (spec §7)
 *   - buffers stdout + stderr
 *   - parses stdout as stream-json (when that format is used)
 *   - enforces a timeout (default 10 minutes) with SIGTERM + SIGKILL escalation
 *   - NEVER throws across the call boundary — returns a facts-only result
 *     and lets the MCP tool layer decide isError semantics (spec §9)
 */

import { spawn } from "node:child_process";
import {
  buildDroidExecArgs,
  type DroidExecFlags,
  DroidFlagsError,
} from "./flags.js";
import { parseStreamJson, type ParsedStreamJson } from "./output.js";

export interface SpawnDroidExecOptions {
  /** Working directory for the spawned droid process. */
  cwd?: string;
  /** Full environment to pass. Defaults to `process.env`. */
  env?: NodeJS.ProcessEnv;
  /** Kill the process after this many ms. Default 600_000 (10 min). */
  timeout_ms?: number;
  /** Override the droid binary name/path. Default: "droid". */
  droid_bin?: string;
}

export type DroidExecFailure =
  | "spawn_error"
  | "nonzero_exit"
  | "stream_errors"
  | "timeout"
  | "flags_error";

export interface SpawnDroidExecResult {
  /** The full argv passed to droid exec (useful for debugging). */
  argv: string[];
  /** Exit code, or null if the process was killed / never exited. */
  exit_code: number | null;
  /** Signal name if the process was killed. */
  signal: NodeJS.Signals | null;
  /** Wall-clock duration of the spawn in ms. */
  duration_ms: number;
  /** Raw stdout captured from droid. */
  stdout: string;
  /** Raw stderr captured from droid. */
  stderr: string;
  /**
   * Parsed stream-json output. Always populated — if the format wasn't
   * stream-json or stdout had no JSONL, this will just be the empty shape
   * (text: "", events: [], errors: []).
   */
  parsed: ParsedStreamJson;
  /**
   * Did the call succeed overall? False when:
   *   - exit_code !== 0, OR
   *   - parsed.errors.length > 0, OR
   *   - the process was killed (timeout), OR
   *   - droid could not be spawned, OR
   *   - buildDroidExecArgs rejected the input (DroidFlagsError)
   */
  ok: boolean;
  /** Reason for failure, when ok is false. */
  failure?: DroidExecFailure;
  /** Human-readable error summary. */
  error_message?: string;
}

const DEFAULT_TIMEOUT_MS = 600_000;
const SIGKILL_GRACE_MS = 5_000;

function emptyParsed(): ParsedStreamJson {
  return { text: "", events: [], errors: [] };
}

export async function spawnDroidExec(
  flags: DroidExecFlags,
  opts: SpawnDroidExecOptions = {},
): Promise<SpawnDroidExecResult> {
  const startedAt = Date.now();

  // Apply the stream-json default unless the caller explicitly overrode it.
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

  const fullArgv = ["exec", ...argv];
  const bin = opts.droid_bin ?? "droid";
  const timeoutMs = opts.timeout_ms ?? DEFAULT_TIMEOUT_MS;

  return new Promise<SpawnDroidExecResult>((resolve) => {
    const child = spawn(bin, fullArgv, {
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

    child.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
    });

    child.on("error", (err: Error) => {
      clearTimeout(timeoutTimer);
      if (sigkillTimer) clearTimeout(sigkillTimer);
      resolve({
        argv: fullArgv,
        exit_code: null,
        signal: null,
        duration_ms: Date.now() - startedAt,
        stdout,
        stderr,
        parsed: emptyParsed(),
        ok: false,
        failure: "spawn_error",
        error_message: `failed to spawn ${bin}: ${err.message}`,
      });
    });

    child.on("close", (code, signal) => {
      clearTimeout(timeoutTimer);
      if (sigkillTimer) clearTimeout(sigkillTimer);

      const parsed =
        effectiveFlags.output_format === "stream-json"
          ? parseStreamJson(stdout)
          : emptyParsed();

      const duration_ms = Date.now() - startedAt;

      // Decide ok/failure
      if (timedOut) {
        resolve({
          argv: fullArgv,
          exit_code: code,
          signal,
          duration_ms,
          stdout,
          stderr,
          parsed,
          ok: false,
          failure: "timeout",
          error_message: `droid exec timed out after ${timeoutMs}ms`,
        });
        return;
      }

      if (code !== 0) {
        resolve({
          argv: fullArgv,
          exit_code: code,
          signal,
          duration_ms,
          stdout,
          stderr,
          parsed,
          ok: false,
          failure: "nonzero_exit",
          error_message:
            stderr.trim() !== ""
              ? stderr.trim()
              : `droid exec exited with code ${code}`,
        });
        return;
      }

      if (parsed.errors.length > 0) {
        const summary = parsed.errors
          .map((e) => {
            if (typeof e.message === "string") return e.message;
            return JSON.stringify(e);
          })
          .join("\n");
        resolve({
          argv: fullArgv,
          exit_code: code,
          signal,
          duration_ms,
          stdout,
          stderr,
          parsed,
          ok: false,
          failure: "stream_errors",
          error_message: summary,
        });
        return;
      }

      resolve({
        argv: fullArgv,
        exit_code: code,
        signal,
        duration_ms,
        stdout,
        stderr,
        parsed,
        ok: true,
      });
    });
  });
}
