/**
 * Input schema for do_pr_review — comprehensive single-pass PR review
 * with auto git context gathering.
 */

import { z } from "zod";
import { ProviderSchema } from "./preset.js";

export const PrReviewInputShape = {
  base: z
    .string()
    .optional()
    .describe(
      "Base branch to diff against. Default: auto-detect (main → master → develop).",
    ),
  scope: z
    .enum(["full", "staged", "unstaged"])
    .optional()
    .describe(
      "What to review. full = branch diff against base (default). staged = git diff --cached. unstaged = git diff.",
    ),
  focus: z
    .string()
    .optional()
    .describe(
      "Optional focus area: security, performance, types, etc. Emphasized in the review prompt.",
    ),
  cwd: z
    .string()
    .optional()
    .describe("Working directory. Defaults to the MCP server's cwd."),
  provider: ProviderSchema,
  model: z
    .string()
    .optional()
    .describe(
      "Override model. Default: YK-GPT-5.4-xHigh (highest reasoning tier).",
    ),
  timeout_ms: z
    .number()
    .int()
    .positive()
    .optional()
    .describe(
      "Timeout in milliseconds. Default: 300000 (5 min — xHigh needs time).",
    ),
};

export const PrReviewInputSchema = z.object(PrReviewInputShape);
export type PrReviewInput = z.infer<typeof PrReviewInputSchema>;
