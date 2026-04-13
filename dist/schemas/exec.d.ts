/**
 * Zod input schema for droid_exec. Mirrors DroidExecFlags in src/droid/flags.ts.
 * Every flag is optional; mutual exclusion validation happens inside
 * buildDroidExecArgs (which throws DroidFlagsError, caught by the tool handler).
 */
import { z } from "zod";
export declare const AutoLevelSchema: z.ZodEnum<{
    low: "low";
    medium: "medium";
    high: "high";
}>;
export declare const ReasoningEffortSchema: z.ZodEnum<{
    low: "low";
    medium: "medium";
    high: "high";
    off: "off";
    max: "max";
    xhigh: "xhigh";
    minimal: "minimal";
    none: "none";
}>;
export declare const OutputFormatSchema: z.ZodEnum<{
    text: "text";
    json: "json";
    "stream-json": "stream-json";
}>;
export declare const InputFormatSchema: z.ZodEnum<{
    text: "text";
    "stream-json": "stream-json";
}>;
export declare const TagSpecSchema: z.ZodUnion<readonly [z.ZodString, z.ZodObject<{
    name: z.ZodString;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, z.core.$strip>]>;
export declare const DroidExecInputShape: {
    prompt: z.ZodOptional<z.ZodString>;
    prompt_file: z.ZodOptional<z.ZodString>;
    model: z.ZodOptional<z.ZodString>;
    auto: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
    }>>;
    allow_unsafe: z.ZodOptional<z.ZodBoolean>;
    output_format: z.ZodOptional<z.ZodEnum<{
        text: "text";
        json: "json";
        "stream-json": "stream-json";
    }>>;
    input_format: z.ZodOptional<z.ZodEnum<{
        text: "text";
        "stream-json": "stream-json";
    }>>;
    session_id: z.ZodOptional<z.ZodString>;
    fork_session_id: z.ZodOptional<z.ZodString>;
    cwd: z.ZodOptional<z.ZodString>;
    worktree: z.ZodOptional<z.ZodUnion<readonly [z.ZodBoolean, z.ZodString]>>;
    worktree_dir: z.ZodOptional<z.ZodString>;
    enabled_tools: z.ZodOptional<z.ZodArray<z.ZodString>>;
    disabled_tools: z.ZodOptional<z.ZodArray<z.ZodString>>;
    tags: z.ZodOptional<z.ZodArray<z.ZodUnion<readonly [z.ZodString, z.ZodObject<{
        name: z.ZodString;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, z.core.$strip>]>>>;
    log_group_id: z.ZodOptional<z.ZodString>;
    mission: z.ZodOptional<z.ZodBoolean>;
    system_prompt: z.ZodOptional<z.ZodString>;
    system_prompt_file: z.ZodOptional<z.ZodString>;
    reasoning_effort: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
        off: "off";
        max: "max";
        xhigh: "xhigh";
        minimal: "minimal";
        none: "none";
    }>>;
    spec_model: z.ZodOptional<z.ZodString>;
    spec_reasoning_effort: z.ZodOptional<z.ZodString>;
    use_spec: z.ZodOptional<z.ZodBoolean>;
    settings_file: z.ZodOptional<z.ZodString>;
    list_tools: z.ZodOptional<z.ZodBoolean>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
};
export declare const DroidExecInputSchema: z.ZodObject<{
    prompt: z.ZodOptional<z.ZodString>;
    prompt_file: z.ZodOptional<z.ZodString>;
    model: z.ZodOptional<z.ZodString>;
    auto: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
    }>>;
    allow_unsafe: z.ZodOptional<z.ZodBoolean>;
    output_format: z.ZodOptional<z.ZodEnum<{
        text: "text";
        json: "json";
        "stream-json": "stream-json";
    }>>;
    input_format: z.ZodOptional<z.ZodEnum<{
        text: "text";
        "stream-json": "stream-json";
    }>>;
    session_id: z.ZodOptional<z.ZodString>;
    fork_session_id: z.ZodOptional<z.ZodString>;
    cwd: z.ZodOptional<z.ZodString>;
    worktree: z.ZodOptional<z.ZodUnion<readonly [z.ZodBoolean, z.ZodString]>>;
    worktree_dir: z.ZodOptional<z.ZodString>;
    enabled_tools: z.ZodOptional<z.ZodArray<z.ZodString>>;
    disabled_tools: z.ZodOptional<z.ZodArray<z.ZodString>>;
    tags: z.ZodOptional<z.ZodArray<z.ZodUnion<readonly [z.ZodString, z.ZodObject<{
        name: z.ZodString;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, z.core.$strip>]>>>;
    log_group_id: z.ZodOptional<z.ZodString>;
    mission: z.ZodOptional<z.ZodBoolean>;
    system_prompt: z.ZodOptional<z.ZodString>;
    system_prompt_file: z.ZodOptional<z.ZodString>;
    reasoning_effort: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
        off: "off";
        max: "max";
        xhigh: "xhigh";
        minimal: "minimal";
        none: "none";
    }>>;
    spec_model: z.ZodOptional<z.ZodString>;
    spec_reasoning_effort: z.ZodOptional<z.ZodString>;
    use_spec: z.ZodOptional<z.ZodBoolean>;
    settings_file: z.ZodOptional<z.ZodString>;
    list_tools: z.ZodOptional<z.ZodBoolean>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
}, z.core.$strip>;
export type DroidExecInput = z.infer<typeof DroidExecInputSchema>;
