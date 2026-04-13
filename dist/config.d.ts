/**
 * Configuration — default provider, model mapping, labels.
 *
 * Resolution order:
 *   1. Environment variable DO_DEFAULT_PROVIDER
 *   2. Config file ~/.config/mcp-do/config.json
 *   3. Built-in default ("droid")
 */
export type ProviderName = "droid" | "opencode";
export interface McpDroidConfig {
    default_provider: ProviderName;
}
export declare function loadConfig(): Promise<McpDroidConfig>;
export declare function resolveProvider(explicit?: string): ProviderName;
/**
 * Resolve a model alias to the provider-specific model ID.
 * If the input already looks provider-specific (contains "custom:" or "/"),
 * it's returned as-is.
 */
export declare function resolveModel(alias: string, provider: ProviderName): string;
export declare const DEFAULT_MODELS: Record<ProviderName, string>;
export declare const DEEP_MODELS: Record<ProviderName, string>;
export declare const FAST_MODELS: Record<ProviderName, string>;
export declare const CROSS_REVIEW_MODELS: Record<ProviderName, string[]>;
export declare const PR_REVIEW_MODELS: Record<ProviderName, string>;
export declare const MODEL_LABELS: Record<string, string>;
export declare function labelFor(model: string): string;
