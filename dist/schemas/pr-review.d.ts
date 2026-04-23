/**
 * Input schema for do_pr_review — comprehensive single-pass PR review
 * with auto git context gathering.
 */
import { z } from "zod";
export declare const PrReviewInputShape: {
    base: z.ZodOptional<z.ZodString>;
    scope: z.ZodOptional<z.ZodEnum<{
        full: "full";
        staged: "staged";
        unstaged: "unstaged";
    }>>;
    focus: z.ZodOptional<z.ZodString>;
    cwd: z.ZodOptional<z.ZodString>;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    model: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
};
export declare const PrReviewInputSchema: z.ZodObject<{
    base: z.ZodOptional<z.ZodString>;
    scope: z.ZodOptional<z.ZodEnum<{
        full: "full";
        staged: "staged";
        unstaged: "unstaged";
    }>>;
    focus: z.ZodOptional<z.ZodString>;
    cwd: z.ZodOptional<z.ZodString>;
    provider: z.ZodOptional<z.ZodEnum<{
        droid: "droid";
        opencode: "opencode";
    }>>;
    model: z.ZodOptional<z.ZodString>;
    timeout_ms: z.ZodOptional<z.ZodNumber>;
}, z.core.$strip>;
export type PrReviewInput = z.infer<typeof PrReviewInputSchema>;
