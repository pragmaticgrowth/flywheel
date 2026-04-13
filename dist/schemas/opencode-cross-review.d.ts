/**
 * Input schema for opencode_cross_review — runs the same review prompt through
 * multiple opencode models in parallel and returns a merged report.
 */
import { z } from "zod";
export declare const OpencodeCrossReviewInputShape: {
    prompt: z.ZodString;
    cwd: z.ZodOptional<z.ZodString>;
    models: z.ZodOptional<z.ZodArray<z.ZodString>>;
    agent: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
};
export declare const OpencodeCrossReviewInputSchema: z.ZodObject<{
    prompt: z.ZodString;
    cwd: z.ZodOptional<z.ZodString>;
    models: z.ZodOptional<z.ZodArray<z.ZodString>>;
    agent: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
}, z.core.$strip>;
export type OpencodeCrossReviewInput = z.infer<typeof OpencodeCrossReviewInputSchema>;
