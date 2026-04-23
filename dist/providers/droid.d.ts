/**
 * Droid provider adapter — wraps spawnDroidExec into the unified RunResult.
 */
import type { RunOptions, RunResult } from "./types.js";
export declare function runDroid(opts: RunOptions): Promise<RunResult>;
