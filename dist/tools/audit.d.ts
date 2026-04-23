/**
 * do_audit — post-delivery auditor. Runs via the persistent Codex MCP
 * backend (same subprocess as do_discuss).
 *
 * Returns a fully-typed structured verdict: pass / concerns / blockers, plus
 * blockers, concerns, missed_requirements, strengths, next_steps — all as
 * typed arrays in structuredContent.
 *
 * Pass thread_id from a prior do_discuss to audit against the plan the same
 * Codex session already critiqued (it has the full prior conversation).
 *
 * Read-only sandbox. Default reasoning effort: high.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
type AuditVerdict = "pass" | "concerns" | "blockers";
export interface AuditStructured {
    verdict?: AuditVerdict;
    blockers: string[];
    concerns: string[];
    missed_requirements: string[];
    strengths: string[];
    next_steps: string[];
}
export declare function parseAuditJson(text: string): AuditStructured;
export declare function stripAuditJsonBlock(text: string): string;
export interface AuditBodyInput {
    context: string;
    diff?: string;
    paths?: string[];
    base_ref?: string;
}
/**
 * Build the user-facing body for do_audit. Pure function — easy to test.
 *
 * Scope resolution (at least one required):
 *   - diff:      use the inline diff verbatim
 *   - paths:     tell Codex to read the listed files/dirs itself
 *   - base_ref:  tell Codex to run `git diff <ref>...HEAD [-- paths]` itself
 *
 * diff + (paths|base_ref) can coexist — Codex will use both. paths + base_ref
 * scope the diff to those paths.
 */
export declare function buildAuditBody(input: AuditBodyInput): string;
export declare function registerAuditTool(server: McpServer): void;
export {};
