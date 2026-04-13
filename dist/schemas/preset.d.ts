/**
 * Shared input schema for all specialized preset tools (do_research,
 * do_review, do_explore, ...). Each preset overrides defaults at
 * registration time but accepts the same user-facing input shape.
 */
import { z } from "zod";
export declare const ProviderSchema: z.ZodOptional<z.ZodEnum<{
    droid: "droid";
    opencode: "opencode";
}>>;
export declare const PresetInputShape: {
    prompt: z.ZodString;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    cwd: z.ZodOptional<z.ZodString>;
    model: z.ZodOptional<z.ZodString>;
    auto: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
    }>>;
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
    session_id: z.ZodOptional<z.ZodString>;
    tags: z.ZodOptional<z.ZodArray<z.ZodUnion<readonly [z.ZodString, z.ZodObject<{
        name: z.ZodString;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, z.core.$strip>]>>>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
};
export declare const PresetInputSchema: z.ZodObject<{
    prompt: z.ZodString;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    cwd: z.ZodOptional<z.ZodString>;
    model: z.ZodOptional<z.ZodString>;
    auto: z.ZodOptional<z.ZodEnum<{
        low: "low";
        medium: "medium";
        high: "high";
    }>>;
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
    session_id: z.ZodOptional<z.ZodString>;
    tags: z.ZodOptional<z.ZodArray<z.ZodUnion<readonly [z.ZodString, z.ZodObject<{
        name: z.ZodString;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, z.core.$strip>]>>>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
}, z.core.$strip>;
export type PresetInput = z.infer<typeof PresetInputSchema>;
