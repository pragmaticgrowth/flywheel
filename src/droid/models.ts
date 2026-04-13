/**
 * Read the catalog of **custom** models available to droid.
 *
 * Factory's built-in models (claude-*, gpt-*, gemini-*, glm-5, kimi-k2.5,
 * minimax-m2.5, …) are intentionally NOT listed — the user exclusively
 * uses BYOK custom models and does not want built-ins surfaced.
 *
 * Source: ~/.factory/settings.json `customModels[]`. Each entry is
 * returned with its canonical id (`custom:BYOK-GLM-5-Turbo-33`) plus a
 * short alias (`custom:glm-5-turbo`) when one is known. Verified during
 * planning: droid accepts both forms, so callers can use whichever is
 * more readable.
 */

import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export interface ModelInfo {
  id: string;
  display_name?: string;
  /** Short alias droid also accepts. */
  alias?: string;
  provider?: string;
  base_url?: string;
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
 * Static map from canonical custom model id to the short alias droid also
 * accepts (verified during planning, see CLAUDE.md §Available Models).
 */
export const CUSTOM_MODEL_ALIASES: Record<string, string> = {
  // BYOK
  "custom:BYOK-MiniMax-M2.7-30": "custom:MiniMax-M2.7",
  "custom:BYOK-GLM-5-Turbo-33": "custom:glm-5-turbo",
  "custom:BYOK-GLM-5.1-31": "custom:glm-5.1",
  "custom:BYOK-GLM-5-32": "custom:glm-5",
  // YK — OpenAI (your key, preferred for GPT)
  "custom:YK-GPT-5.4-60": "custom:gpt-5.4",
  "custom:YK-GPT-5.4-Low-61": "custom:gpt-5.4-low",
  "custom:YK-GPT-5.4-Med-62": "custom:gpt-5.4-med",
  "custom:YK-GPT-5.4-High-63": "custom:gpt-5.4-high",
  "custom:YK-GPT-5.4-xHigh-64": "custom:gpt-5.4-xhigh",
  // VP (fallback — no YK Mini exists)
  "custom:VP-GPT-5.4-Mini-48": "custom:gpt-5.4-mini",
};

export interface ListModelsOptions {
  settings_path?: string; // override for tests
}

export async function listModels(
  opts: ListModelsOptions = {},
): Promise<ModelInfo[]> {
  const settingsPath =
    opts.settings_path ?? join(homedir(), ".factory", "settings.json");

  let raw = "";
  try {
    raw = await readFile(settingsPath, "utf8");
  } catch {
    return [];
  }

  let parsed: RawSettingsJson;
  try {
    parsed = JSON.parse(raw) as RawSettingsJson;
  } catch {
    return [];
  }

  return (parsed.customModels ?? []).map((m) => {
    const info: ModelInfo = {
      id: m.id,
      display_name: m.displayName,
    };
    if (CUSTOM_MODEL_ALIASES[m.id] !== undefined) {
      info.alias = CUSTOM_MODEL_ALIASES[m.id];
    }
    if (m.provider !== undefined) info.provider = m.provider;
    if (m.baseUrl !== undefined) info.base_url = m.baseUrl;
    return info;
  });
}
