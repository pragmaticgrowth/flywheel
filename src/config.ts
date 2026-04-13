/**
 * Configuration — default provider, model mapping, labels.
 *
 * Resolution order:
 *   1. Environment variable DO_DEFAULT_PROVIDER
 *   2. Config file ~/.config/mcp-droid/config.json
 *   3. Built-in default ("droid")
 */

import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export type ProviderName = "droid" | "opencode";

export interface McpDroidConfig {
  default_provider: ProviderName;
}

const CONFIG_PATH = join(homedir(), ".config", "mcp-droid", "config.json");

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
  "gpt-5.4-mini": {
    droid: "custom:VP-GPT-5.4-Mini-48",
    opencode: "openai/gpt-5.4-mini",
  },
  "minimax-m2.7": {
    droid: "custom:MiniMax-M2.7",
    opencode: "minimax-coding-plan/MiniMax-M2.7",
  },
  "gpt-5.4": {
    droid: "custom:gpt-5.4",
    opencode: "openai/gpt-5.4",
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
    "custom:VP-GPT-5.4-Mini-48",
    "custom:glm-5.1",
  ],
  opencode: [
    "zai-coding-plan/glm-5-turbo",
    "openai/gpt-5.4-mini",
    "minimax-coding-plan/MiniMax-M2.7",
  ],
};

// ---------------------------------------------------------------------------
// Model labels (human-readable, for reports)
// ---------------------------------------------------------------------------

export const MODEL_LABELS: Record<string, string> = {
  "custom:glm-5-turbo": "GLM-5-Turbo (Zhipu)",
  "custom:BYOK-GLM-5-Turbo-33": "GLM-5-Turbo (Zhipu)",
  "custom:VP-GPT-5.4-Mini-48": "GPT-5.4-Mini (OpenAI)",
  "custom:VP-GPT-5.4-15": "GPT-5.4 (OpenAI)",
  "custom:glm-5.1": "GLM-5.1 (Zhipu Deep)",
  "custom:BYOK-GLM-5.1-31": "GLM-5.1 (Zhipu Deep)",
  "custom:MiniMax-M2.7": "MiniMax M2.7",
  "custom:BYOK-MiniMax-M2.7-30": "MiniMax M2.7",
  "zai-coding-plan/glm-5-turbo": "GLM-5-Turbo (Zhipu)",
  "zai-coding-plan/glm-5.1": "GLM-5.1 (Zhipu Deep)",
  "openai/gpt-5.4-mini": "GPT-5.4-Mini (OpenAI)",
  "openai/gpt-5.4": "GPT-5.4 (OpenAI)",
  "minimax-coding-plan/MiniMax-M2.7": "MiniMax M2.7",
};

export function labelFor(model: string): string {
  return MODEL_LABELS[model] ?? model;
}
