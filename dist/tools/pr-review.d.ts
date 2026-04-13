/**
 * do_pr_review — comprehensive single-pass PR review with auto git context.
 * Gathers git diff, commits, and changed files, then dispatches to GPT-5.4 xHigh.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerPrReviewTool(server: McpServer): void;
