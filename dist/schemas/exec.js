/**
 * Zod input schema for droid_exec. Mirrors DroidExecFlags in src/droid/flags.ts.
 * Every flag is optional; mutual exclusion validation happens inside
 * buildDroidExecArgs (which throws DroidFlagsError, caught by the tool handler).
 */
import { z } from "zod";
export const AutoLevelSchema = z.enum(["low", "medium", "high"]);
export const ReasoningEffortSchema = z.enum([
    "off",
    "low",
    "medium",
    "high",
    "max",
    "xhigh",
    "minimal",
    "none",
]);
export const OutputFormatSchema = z.enum(["text", "json", "stream-json"]);
export const InputFormatSchema = z.enum(["text", "stream-json"]);
export const TagSpecSchema = z.union([
    z.string(),
    z.object({
        name: z.string(),
        metadata: z.record(z.string(), z.unknown()).optional(),
    }),
]);
export const DroidExecInputShape = {
    prompt: z.string().optional().describe("Prompt text passed as the last positional argument."),
    prompt_file: z
        .string()
        .optional()
        .describe("Read the prompt from this file (mutually exclusive with prompt)."),
    model: z
        .string()
        .optional()
        .describe("Custom model id. Use canonical form (custom:BYOK-GLM-5-Turbo-33) or short alias (custom:glm-5-turbo, custom:MiniMax-M2.7, custom:glm-5.1). Use only custom: models — factory built-ins are off-limits."),
    auto: AutoLevelSchema.optional().describe("Autonomy level. Omit = read-only (safest). low / medium / high escalate write permissions."),
    allow_unsafe: z
        .boolean()
        .optional()
        .describe("Set --skip-permissions-unsafe. Cannot combine with auto."),
    output_format: OutputFormatSchema.optional().describe("Output format. Defaults to stream-json (recommended — plain json is unsafe)."),
    input_format: InputFormatSchema.optional(),
    session_id: z.string().optional().describe("Continue an existing session (requires prompt)."),
    fork_session_id: z
        .string()
        .optional()
        .describe("Fork an existing session into a new one (requires prompt)."),
    cwd: z
        .string()
        .optional()
        .describe("Working directory for droid. Defaults to the MCP server's cwd."),
    worktree: z
        .union([z.boolean(), z.string()])
        .optional()
        .describe("true → bare --worktree; string → --worktree <name>."),
    worktree_dir: z.string().optional(),
    enabled_tools: z.array(z.string()).optional(),
    disabled_tools: z.array(z.string()).optional(),
    tags: z.array(TagSpecSchema).optional(),
    log_group_id: z.string().optional(),
    mission: z
        .boolean()
        .optional()
        .describe("Enable mission mode. Requires auto: 'high' or allow_unsafe."),
    system_prompt: z.string().optional().describe("Append text to the system prompt."),
    system_prompt_file: z
        .string()
        .optional()
        .describe("Append file contents to the system prompt."),
    reasoning_effort: ReasoningEffortSchema.optional(),
    spec_model: z.string().optional(),
    spec_reasoning_effort: z.string().optional(),
    use_spec: z.boolean().optional(),
    settings_file: z
        .string()
        .optional()
        .describe("Undocumented but accepted: --settings <path> for per-process overrides."),
    list_tools: z.boolean().optional(),
    timeout_ms: z
        .number()
        .int()
        .positive()
        .optional()
        .describe("Server-side spawn timeout in ms. Default 600000 (10 min)."),
};
export const DroidExecInputSchema = z.object(DroidExecInputShape);
//# sourceMappingURL=exec.js.map