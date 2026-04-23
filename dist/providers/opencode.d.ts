/**
 * OpenCode provider adapter — wraps spawnOpencodeRun into the unified RunResult.
 */
import type { RunOptions, RunResult } from "./types.js";
export declare function runOpencode(opts: RunOptions): Promise<RunResult>;
