/**
 * Configuration — default provider, model mapping, labels.
 *
 * Resolution order:
 *   1. Environment variable DO_DEFAULT_PROVIDER
 *   2. Config file ~/.config/mcp-do/config.json
 *   3. Built-in default ("droid")
 */

import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export type ProviderName = "droid" | "opencode";

export interface McpDroidConfig {
  default_provider: ProviderName;
}

const CONFIG_PATH = join(homedir(), ".config", "mcp-do", "config.json");

const BUILTIN_DEFAULTS: McpDroidConfig = {
  default_provider: "droid",
};

let cachedConfig: McpDroidConfig | null = null;

async function loadConfigFile(): Promise<Partial<McpDroidConfig>> {
  try {
    const raw = await readFile(CONFIG_PATH, "utf8");
    return JSON.parse(raw) as Partial<McpDroidConfig>;
  } catch {
    return {};
  }
}

export async function loadConfig(): Promise<McpDroidConfig> {
  if (cachedConfig) return cachedConfig;

  const file = await loadConfigFile();
  const envProvider = process.env.DO_DEFAULT_PROVIDER as
    | ProviderName
    | undefined;

  cachedConfig = {
    default_provider:
      envProvider ?? file.default_provider ?? BUILTIN_DEFAULTS.default_provider,
  };
  return cachedConfig;
}

export function resolveProvider(explicit?: string): ProviderName {
  if (explicit === "droid" || explicit === "opencode") return explicit;
  return cachedConfig?.default_provider ?? BUILTIN_DEFAULTS.default_provider;
}

// ---------------------------------------------------------------------------
// Model alias resolution
// ---------------------------------------------------------------------------

const MODEL_ALIASES: Record<string, Record<ProviderName, string>> = {
  "glm-5-turbo": {
    droid: "custom:glm-5-turbo",
    opencode: "zai-coding-plan/glm-5-turbo",
  },
  "glm-5.1": {
    droid: "custom:glm-5.1",
    opencode: "zai-coding-plan/glm-5.1",
  },
  "minimax-m2.7": {
    droid: "custom:MiniMax-M2.7",
    opencode: "minimax-coding-plan/MiniMax-M2.7",
  },
  // GPT — YK (your key) preferred over VP
  "gpt-5.4": {
    droid: "custom:YK-GPT-5.4-60",
    opencode: "yk/gpt-5.4",
  },
  "gpt-5.4-mini": {
    droid: "custom:YK-GPT-5.4-Med-62", // no YK Mini exists, remap to Med
    opencode: "yk/gpt-5.4(medium)",
  },
  "gpt-5.4-low": {
    droid: "custom:YK-GPT-5.4-Low-61",
    opencode: "yk/gpt-5.4(low)",
  },
  "gpt-5.4-med": {
    droid: "custom:YK-GPT-5.4-Med-62",
    opencode: "yk/gpt-5.4(medium)",
  },
  "gpt-5.4-high": {
    droid: "custom:YK-GPT-5.4-High-63",
    opencode: "yk/gpt-5.4(high)",
  },
  "gpt-5.4-xhigh": {
    droid: "custom:YK-GPT-5.4-xHigh-64",
    opencode: "yk/gpt-5.4(xhigh)",
  },
};

/**
 * Resolve a model alias to the provider-specific model ID.
 * If the input already looks provider-specific (contains "custom:" or "/"),
 * it's returned as-is.
 */
export function resolveModel(alias: string, provider: ProviderName): string {
  if (alias.includes("custom:") || alias.includes("/")) return alias;
  const entry = MODEL_ALIASES[alias.toLowerCase()];
  if (entry?.[provider]) return entry[provider];
  return alias;
}

// ---------------------------------------------------------------------------
// Provider-keyed defaults
// ---------------------------------------------------------------------------

export const DEFAULT_MODELS: Record<ProviderName, string> = {
  droid: "custom:glm-5-turbo",
  opencode: "zai-coding-plan/glm-5-turbo",
};

export const DEEP_MODELS: Record<ProviderName, string> = {
  droid: "custom:glm-5.1",
  opencode: "zai-coding-plan/glm-5.1",
};

export const FAST_MODELS: Record<ProviderName, string> = {
  droid: "custom:MiniMax-M2.7",
  opencode: "minimax-coding-plan/MiniMax-M2.7",
};

export const CROSS_REVIEW_MODELS: Record<ProviderName, string[]> = {
  droid: [
    "custom:glm-5-turbo",
    "custom:YK-GPT-5.4-High-63",
    "custom:glm-5.1",
  ],
  opencode: [
    "zai-coding-plan/glm-5-turbo",
    "yk/gpt-5.4(high)",
    "minimax-coding-plan/MiniMax-M2.7",
  ],
};

// ---------------------------------------------------------------------------
// Model labels (human-readable, for reports)
// ---------------------------------------------------------------------------

export const MODEL_LABELS: Record<string, string> = {
  // BYOK — Zhipu
  "custom:glm-5-turbo": "GLM-5-Turbo (Zhipu)",
  "custom:BYOK-GLM-5-Turbo-33": "GLM-5-Turbo (Zhipu)",
  "custom:glm-5.1": "GLM-5.1 (Zhipu Deep)",
  "custom:BYOK-GLM-5.1-31": "GLM-5.1 (Zhipu Deep)",
  // BYOK — MiniMax
  "custom:MiniMax-M2.7": "MiniMax M2.7",
  "custom:BYOK-MiniMax-M2.7-30": "MiniMax M2.7",
  // YK — OpenAI (your key, preferred)
  "custom:YK-GPT-5.4-60": "GPT-5.4 (OpenAI YK)",
  "custom:YK-GPT-5.4-Low-61": "GPT-5.4 Low (OpenAI YK)",
  "custom:YK-GPT-5.4-Med-62": "GPT-5.4 Med (OpenAI YK)",
  "custom:YK-GPT-5.4-High-63": "GPT-5.4 High (OpenAI YK)",
  "custom:YK-GPT-5.4-xHigh-64": "GPT-5.4 xHigh (OpenAI YK)",
  // VP — OpenAI (legacy, not actively used)
  "custom:VP-GPT-5.4-15": "GPT-5.4 (OpenAI VP)",
  // OpenCode providers
  "zai-coding-plan/glm-5-turbo": "GLM-5-Turbo (Zhipu)",
  "zai-coding-plan/glm-5.1": "GLM-5.1 (Zhipu Deep)",
  "minimax-coding-plan/MiniMax-M2.7": "MiniMax M2.7",
  "yk/gpt-5.4": "GPT-5.4 (OpenAI YK)",
  "yk/gpt-5.4(low)": "GPT-5.4 Low (OpenAI YK)",
  "yk/gpt-5.4(medium)": "GPT-5.4 Med (OpenAI YK)",
  "yk/gpt-5.4(high)": "GPT-5.4 High (OpenAI YK)",
  "yk/gpt-5.4(xhigh)": "GPT-5.4 xHigh (OpenAI YK)",
};

export function labelFor(model: string): string {
  return MODEL_LABELS[model] ?? model;
}
