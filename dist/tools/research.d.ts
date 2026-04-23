/**
 * do_research — unified web research tool.
 *
 * One tool, two depths:
 *   depth: "deep" (default) — thorough, parallel web search, GLM-5-Turbo,
 *     structured Key Findings / Sources / Confidence / Open Questions report.
 *   depth: "fast" — quick lookup, <200 words, MiniMax-M2.7.
 *
 * Previously shipped as two tools (do_research + do_research_fast). Merged
 * in April 2026 because the only difference was model + prompt template.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerResearchTool(server: McpServer): void;
