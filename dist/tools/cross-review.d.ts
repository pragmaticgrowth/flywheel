/**
 * do_cross_review — unified cross-model code review.
 * Runs the same review prompt through 3 models from different training
 * lineages in parallel and merges findings. Works with both droid and opencode.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerCrossReviewTool(server: McpServer): void;
