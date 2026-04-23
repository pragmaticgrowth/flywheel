/**
 * Intelligent prompt for do_review — code review focused on real bugs.
 * Inspired by Codex adversarial-review pattern: default to skepticism,
 * cite file:line, only report material issues.
 */
export declare function buildReviewPrompt(userPrompt: string): string;
