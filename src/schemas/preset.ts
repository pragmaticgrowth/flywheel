/**
 * Shared input schema for all specialized preset tools
 * (droid_research, droid_review_code, droid_explore_code, ...).
 * Each preset overrides the default model + auto + system prompt file at
 * registration time but accepts the same user-facing input shape.
 */

import { z } from "zod";
import {
  AutoLevelSchema,
  ReasoningEffortSchema,
  TagSpecSchema,
} from "./exec.js";

export const PresetInputShape = {
  prompt: z
    .string()
    .describe("Prompt text. Required — prompt_file is not supported in presets."),
  cwd: z
    .string()
    .optional()
    .describe("Working directory for droid. Defaults to the MCP server's cwd."),
  model: z
    .string()
    .optional()
    .describe("Override the preset's default model."),
  auto: AutoLevelSchema.optional().describe(
    "Override the preset's default autonomy level.",
  ),
  reasoning_effort: ReasoningEffortSchema.optional(),
  session_id: z
    .string()
    .optional()
    .describe("Continue an existing session (threads context forward)."),
  tags: z.array(TagSpecSchema).optional(),
  timeout_ms: z.number().int().positive().optional(),
};

export type PresetInput = {
  prompt: string;
  cwd?: string;
  model?: string;
  auto?: "low" | "medium" | "high";
  reasoning_effort?: z.infer<typeof ReasoningEffortSchema>;
  session_id?: string;
  tags?: z.infer<typeof TagSpecSchema>[];
  timeout_ms?: number;
};
