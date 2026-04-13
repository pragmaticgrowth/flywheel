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
export interface ModelInfo {
    id: string;
    display_name?: string;
    /** Short alias droid also accepts. */
    alias?: string;
    provider?: string;
    base_url?: string;
}
/**
 * Static map from canonical custom model id to the short alias droid also
 * accepts (verified during planning, see CLAUDE.md §Available Models).
 */
export declare const CUSTOM_MODEL_ALIASES: Record<string, string>;
export interface ListModelsOptions {
    settings_path?: string;
}
export declare function listModels(opts?: ListModelsOptions): Promise<ModelInfo[]>;
