/**
 * do_discuss — iterative plan/architecture discussion with GPT-5.4 via the
 * persistent `codex mcp-server` backend.
 *
 * First turn:  args { prompt }                    → codex tool
 * Follow-up:   args { prompt, thread_id }         → codex-reply tool
 *
 * The Codex subprocess persists across turns, so follow-up turns are 10x
 * faster than `codex exec` (no cold start, no config reload).
 *
 * Read-only sandbox — this tool is a thinking partner, not a coder.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export interface DiscussStructured {
    objective?: string;
    risks: string[];
    blockers: string[];
    alternatives: string[];
    missing: string[];
    verdict?: "proceed" | "proceed-with-changes" | "reconsider";
}
export declare function parseDiscussJson(text: string): DiscussStructured;
export declare function stripDiscussJsonBlock(text: string): string;
export declare function registerDiscussTool(server: McpServer): void;
