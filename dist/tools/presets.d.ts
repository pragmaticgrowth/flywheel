/**
 * Unified preset tools — each wraps a structured prompt template + provider
 * dispatch. Works with both droid (via profile files) and opencode (via agents).
 *
 * Intelligent prompts (Codex-inspired: task + output_contract + grounding_rules)
 * are prepended to the user's prompt automatically. Tool descriptions stay brief.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerPresetTools(server: McpServer): void;
