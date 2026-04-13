/**
 * Centralised default values shared by every tool that doesn't take an
 * explicit override from the caller. Tweak in one place to retune.
 *
 * `DEFAULT_MODEL` is the universal fallback. We never let droid pick its
 * own default (claude-opus-4-6) because the user uses BYOK custom models
 * exclusively — see ~/.claude/projects/-Users-serkan-mcp-do/memory/.
 */

export const DEFAULT_MODEL = "custom:glm-5-turbo";
export const DEFAULT_SPEC_MODEL = "custom:glm-5.1";
