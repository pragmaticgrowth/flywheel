/**
 * Provider dispatcher — routes to droid or opencode based on ProviderName.
 */
import type { ProviderName, RunOptions, RunResult } from "./types.js";
export type { ProviderName, RunOptions, RunResult } from "./types.js";
export declare function runWithProvider(provider: ProviderName, opts: RunOptions): Promise<RunResult>;
