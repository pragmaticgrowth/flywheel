/**
 * Prompt template for do_pr_review — comprehensive single-pass PR review.
 * Injects git context (branch, commits, diff) into a structured review prompt.
 */
export interface PrReviewContext {
    branch: string;
    base: string;
    commitLog: string;
    diffStat: string;
    diff: string;
    diffTruncated: boolean;
    focus?: string;
}
export declare function buildPrReviewPrompt(ctx: PrReviewContext): string;
