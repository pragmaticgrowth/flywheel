/**
 * Input schema for do_cross_review — runs the same review prompt through
 * multiple models in parallel. Unified: works with both droid and opencode.
 */
import { z } from "zod";
import { ProviderSchema } from "./preset.js";
export const CrossReviewInputShape = {
    prompt: z
        .string()
        .describe("The review prompt. Sent to all models in parallel. Be specific about what to review."),
    provider: ProviderSchema,
    cwd: z
        .string()
        .optional()
        .describe("Working directory. Defaults to the MCP server's cwd."),
    models: z
        .array(z.string())
        .optional()
        .describe("Override the default model set. Defaults depend on the provider."),
    agent: z
        .string()
        .optional()
        .describe("Agent to use per model (opencode only). Defaults to 'review'."),
    timeout_ms: z
        .number()
        .int()
        .positive()
        .optional()
        .describe("Per-model timeout in milliseconds. Defaults to 240000 (4 min)."),
};
export const CrossReviewInputSchema = z.object(CrossReviewInputShape);
//# sourceMappingURL=cross-review.js.map