/**
 * Provider dispatcher — routes to droid or opencode based on ProviderName.
 */

import type { ProviderName, RunOptions, RunResult } from "./types.js";
import { runDroid } from "./droid.js";
import { runOpencode } from "./opencode.js";

export type { ProviderName, RunOptions, RunResult } from "./types.js";

export async function runWithProvider(
  provider: ProviderName,
  opts: RunOptions,
): Promise<RunResult> {
  switch (provider) {
    case "droid":
      return runDroid(opts);
    case "opencode":
      return runOpencode(opts);
  }
}
