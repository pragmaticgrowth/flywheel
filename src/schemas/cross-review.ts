/**
 * Input schema for droid_cross_review — runs the same review prompt through
 * multiple model families in parallel and returns a merged report.
 */

import { z } from "zod";

export const CrossReviewInputShape = {
  prompt: z
    .string()
    .describe(
      "The review prompt. Sent to all models in parallel. Be specific about what to review and what to look for.",
    ),
  cwd: z
    .string()
    .optional()
    .describe("Working directory for droid. Defaults to the MCP server's cwd."),
  models: z
    .array(z.string())
    .optional()
    .describe(
      'Override the default model set. Defaults to ["custom:glm-5-turbo", "custom:VP-GPT-5.4-Mini-48", "custom:glm-5.1"].',
    ),
  timeout_ms: z.number().int().positive().optional().describe(
    "Per-model timeout in milliseconds. Defaults to 180000 (3 min).",
  ),
};

export const CrossReviewInputSchema = z.object(CrossReviewInputShape);
export type CrossReviewInput = z.infer<typeof CrossReviewInputSchema>;
