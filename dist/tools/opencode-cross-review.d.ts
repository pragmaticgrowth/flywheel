/**
 * opencode_cross_review — parallel code review through 3 opencode models
 * spanning distinct training lineages. Mirrors droid_cross_review but routes
 * through `opencode run --agent review` instead of `droid exec`.
 *
 * Default models: GLM-5-Turbo (Zhipu), GPT-5.4-Mini (OpenAI), MiniMax-M2.7
 * (MiniMax / Alibaba lineage). Three distinct families for maximum blind-spot
 * coverage — picked from providers the user has already authed in opencode
 * (zai-coding-plan, openai, minimax-coding-plan).
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerOpencodeCrossReviewTool(server: McpServer): void;
