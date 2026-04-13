/**
 * Input schema for do_cross_review — runs the same review prompt through
 * multiple models in parallel. Unified: works with both droid and opencode.
 */
import { z } from "zod";
export declare const CrossReviewInputShape: {
    prompt: z.ZodString;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    cwd: z.ZodOptional<z.ZodString>;
    models: z.ZodOptional<z.ZodArray<z.ZodString>>;
    agent: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
};
export declare const CrossReviewInputSchema: z.ZodObject<{
    prompt: z.ZodString;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    cwd: z.ZodOptional<z.ZodString>;
    models: z.ZodOptional<z.ZodArray<z.ZodString>>;
    agent: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
}, z.core.$strip>;
export type CrossReviewInput = z.infer<typeof CrossReviewInputSchema>;
