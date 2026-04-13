/**
 * Provider-agnostic interfaces for executing prompts.
 */

import type { ProviderName } from "../config.js";
import type { AutoLevel, ReasoningEffort } from "../droid/flags.js";

export type { ProviderName } from "../config.js";

export interface RunOptions {
  prompt: string;
  model: string;
  cwd: string;
  timeout_ms?: number;
  // Droid-specific (ignored by opencode)
  auto?: AutoLevel;
  reasoning_effort?: ReasoningEffort;
  session_id?: string;
  tags?: Array<string | { name: string; metadata?: Record<string, unknown> }>;
  system_prompt_file?: string;
  // Opencode-specific (ignored by droid)
  agent?: string;
}

export interface RunResult {
  provider: ProviderName;
  ok: boolean;
  text: string;
  error_message?: string;
  duration_ms: number;
  session_id?: string;
  model: string;
}
