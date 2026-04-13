/**
 * Shared input schema for all specialized preset tools (do_research,
 * do_review, do_explore, ...). Each preset overrides defaults at
 * registration time but accepts the same user-facing input shape.
 */

import { z } from "zod";
import {
  AutoLevelSchema,
  ReasoningEffortSchema,
  TagSpecSchema,
} from "./exec.js";

export const ProviderSchema = z
  .enum(["droid", "opencode"])
  .optional()
  .describe(
    "Execution backend. Defaults to the server's configured default (DO_DEFAULT_PROVIDER env or ~/.config/mcp-droid/config.json).",
  );

export const PresetInputShape = {
  prompt: z
    .string()
    .describe("Prompt text — what to research, review, explore, etc."),
  provider: ProviderSchema,
  cwd: z
    .string()
    .optional()
    .describe("Working directory. Defaults to the MCP server's cwd."),
  model: z
    .string()
    .optional()
    .describe(
      "Override model. Accepts short aliases (glm-5-turbo, gpt-5.4-mini) or provider-specific IDs.",
    ),
  auto: AutoLevelSchema.optional().describe(
    "Autonomy level (droid only). low / medium / high.",
  ),
  reasoning_effort: ReasoningEffortSchema.optional(),
  session_id: z
    .string()
    .optional()
    .describe("Continue an existing session (droid only)."),
  tags: z.array(TagSpecSchema).optional(),
  timeout_ms: z.number().int().positive().optional(),
};

export const PresetInputSchema = z.object(PresetInputShape);
export type PresetInput = z.infer<typeof PresetInputSchema>;
