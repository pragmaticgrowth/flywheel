/**
 * Input schema for opencode_cross_review — runs the same review prompt through
 * multiple opencode models in parallel and returns a merged report.
 */
import { z } from "zod";
export const OpencodeCrossReviewInputShape = {
    prompt: z
        .string()
        .describe("The review prompt. Sent to all models in parallel. Be specific about what to review and what to look for."),
    cwd: z
        .string()
        .optional()
        .describe("Working directory for opencode. Defaults to the MCP server's cwd."),
    models: z
        .array(z.string())
        .optional()
        .describe('Override the default model set. Defaults to ["zai-coding-plan/glm-5-turbo", "openai/gpt-5.4-mini", "minimax-coding-plan/MiniMax-M2.7"].'),
    agent: z
        .string()
        .optional()
        .describe("Opencode agent to invoke per model. Defaults to 'review'. Must exist in ~/.config/opencode/agents/ or .opencode/agents/."),
    timeout_ms: z
        .number()
        .int()
        .positive()
        .optional()
        .describe("Per-model timeout in milliseconds. Defaults to 240000 (4 min)."),
};
export const OpencodeCrossReviewInputSchema = z.object(OpencodeCrossReviewInputShape);
//# sourceMappingURL=opencode-cross-review.js.map