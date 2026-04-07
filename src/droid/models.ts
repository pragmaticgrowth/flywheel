/**
 * Read the catalog of available droid models.
 *
 * Two sources:
 *   1. A hardcoded built-in list extracted from `droid exec --help`. Refresh
 *      this constant when droid ships new models.
 *   2. ~/.factory/settings.json `customModels[]` for BYOK + custom models.
 *
 * Custom models from settings.json are returned with both their canonical id
 * (`custom:BYOK-GLM-5-Turbo-33`) and a short alias (`custom:glm-5-turbo`)
 * when one is known. Verified during planning: droid accepts both forms,
 * so callers can use whichever is more readable.
 */

import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export interface ModelInfo {
  id: string;
  display_name?: string;
  kind: "builtin" | "custom";
  /** Short alias droid also accepts (for custom models). */
  alias?: string;
  provider?: string;
  base_url?: string;
  /** True for built-ins where reasoning_effort is supported. */
  supports_reasoning?: boolean;
  /** Supported reasoning effort levels for the model, if known. */
  reasoning_levels?: string[];
  /** Default reasoning effort for the model, if known. */
  default_reasoning?: string;
}

interface RawCustomModel {
  id: string;
  model?: string;
  baseUrl?: string;
  apiKey?: string;
  displayName?: string;
  provider?: string;
}

interface RawSettingsJson {
  customModels?: RawCustomModel[];
}

/**
 * Built-in models, captured from `droid exec --help` (Apr 2026, droid ≥0.95).
 * Refresh when droid ships new models.
 */
export const BUILTIN_MODELS: ModelInfo[] = [
  { id: "claude-opus-4-5-20251101", display_name: "Claude Opus 4.5", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high"], default_reasoning: "off" },
  { id: "claude-opus-4-6", display_name: "Claude Opus 4.6 (default)", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high", "max"], default_reasoning: "high" },
  { id: "claude-opus-4-6-fast", display_name: "Claude Opus 4.6 Fast Mode", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high", "max"], default_reasoning: "high" },
  { id: "claude-sonnet-4-5-20250929", display_name: "Claude Sonnet 4.5", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high"], default_reasoning: "off" },
  { id: "claude-sonnet-4-6", display_name: "Claude Sonnet 4.6", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high", "max"], default_reasoning: "high" },
  { id: "claude-haiku-4-5-20251001", display_name: "Claude Haiku 4.5", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high"], default_reasoning: "off" },
  { id: "gpt-5.2", display_name: "GPT-5.2", kind: "builtin", supports_reasoning: true, reasoning_levels: ["off", "low", "medium", "high", "xhigh"], default_reasoning: "low" },
  { id: "gpt-5.2-codex", display_name: "GPT-5.2-Codex", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "medium" },
  { id: "gpt-5.4", display_name: "GPT-5.4", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "medium" },
  { id: "gpt-5.4-fast", display_name: "GPT-5.4 Fast Mode", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "medium" },
  { id: "gpt-5.4-mini", display_name: "GPT-5.4 Mini", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "high" },
  { id: "gpt-5.3-codex", display_name: "GPT-5.3-Codex", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "medium" },
  { id: "gpt-5.3-codex-fast", display_name: "GPT-5.3-Codex Fast Mode", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high", "xhigh"], default_reasoning: "medium" },
  { id: "gemini-3.1-pro-preview", display_name: "Gemini 3.1 Pro", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high"], default_reasoning: "high" },
  { id: "gemini-3-flash-preview", display_name: "Gemini 3 Flash", kind: "builtin", supports_reasoning: true, reasoning_levels: ["minimal", "low", "medium", "high"], default_reasoning: "high" },
  { id: "glm-5", display_name: "Droid Core (GLM-5)", kind: "builtin", supports_reasoning: false, reasoning_levels: ["none"], default_reasoning: "none" },
  { id: "kimi-k2.5", display_name: "Droid Core (Kimi K2.5)", kind: "builtin", supports_reasoning: false, reasoning_levels: ["none"], default_reasoning: "none" },
  { id: "minimax-m2.5", display_name: "Droid Core (MiniMax M2.5)", kind: "builtin", supports_reasoning: true, reasoning_levels: ["low", "medium", "high"], default_reasoning: "high" },
];

/**
 * Static map from canonical custom model id to the short alias droid also
 * accepts (verified during planning, see CLAUDE.md §Available Models).
 */
export const CUSTOM_MODEL_ALIASES: Record<string, string> = {
  "custom:BYOK-MiniMax-M2.7-30": "custom:MiniMax-M2.7",
  "custom:BYOK-GLM-5-Turbo-33": "custom:glm-5-turbo",
  "custom:BYOK-GLM-5.1-31": "custom:glm-5.1",
  "custom:BYOK-GLM-5-32": "custom:glm-5",
};

export interface ListModelsOptions {
  settings_path?: string; // override for tests
}

export async function listModels(opts: ListModelsOptions = {}): Promise<ModelInfo[]> {
  const settingsPath =
    opts.settings_path ?? join(homedir(), ".factory", "settings.json");
  let raw = "";
  try {
    raw = await readFile(settingsPath, "utf8");
  } catch {
    // No settings.json — return built-ins only.
    return [...BUILTIN_MODELS];
  }

  let parsed: RawSettingsJson;
  try {
    parsed = JSON.parse(raw) as RawSettingsJson;
  } catch {
    return [...BUILTIN_MODELS];
  }

  const customs: ModelInfo[] = (parsed.customModels ?? []).map((m) => {
    const info: ModelInfo = {
      id: m.id,
      display_name: m.displayName,
      kind: "custom",
    };
    if (CUSTOM_MODEL_ALIASES[m.id] !== undefined) {
      info.alias = CUSTOM_MODEL_ALIASES[m.id];
    }
    if (m.provider !== undefined) info.provider = m.provider;
    if (m.baseUrl !== undefined) info.base_url = m.baseUrl;
    return info;
  });

  return [...BUILTIN_MODELS, ...customs];
}
