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

const TEMPLATE = `<task>
You are reviewing a pull request. Analyze the complete diff for:
1. Bugs — logic errors, null handling, race conditions, resource leaks
2. Security — injection, auth bypass, secrets exposure, path traversal
3. Edge cases — empty input, large data, unicode, timezone issues
4. Type safety — unsafe casts, any leaks, missing null checks
5. Test gaps — untested paths, missing edge case coverage
6. Breaking changes — API surface changes, schema migrations
</task>

<output_contract>
## Summary
One paragraph: what this PR does and overall quality assessment.

## Findings
For each issue (ordered by severity):
### [critical|warning|info] Title
**File:** path:line
**Issue:** What's wrong (one sentence)
**Impact:** What breaks in production
**Fix:** Concrete suggestion (code snippet if applicable)

## Test Gaps
List specific untested paths or missing edge cases. Skip if coverage is adequate.

## Verdict
APPROVE | REQUEST_CHANGES | COMMENT
One-line justification.
</output_contract>

<grounding_rules>
- Only report issues you can verify from the diff
- Cite exact file:line for every finding
- Do not report style or formatting issues
- Do not suggest refactors unless they fix a real bug
- Zero findings is valid — do not invent issues to fill space
- If the diff is truncated, note which files you could not review
</grounding_rules>`;

export function buildPrReviewPrompt(ctx: PrReviewContext): string {
  const focusLine = ctx.focus
    ? `\nPay special attention to: ${ctx.focus}\n`
    : "";

  const truncNote = ctx.diffTruncated
    ? "\n[NOTE: Diff was truncated. Focus review on the files shown above.]\n"
    : "";

  return `${TEMPLATE}${focusLine}

<context>
Branch: ${ctx.branch} → ${ctx.base}

Commits:
${ctx.commitLog || "(no commits)"}

Files changed:
${ctx.diffStat || "(no stat available)"}
</context>

<diff>
${ctx.diff}${truncNote}
</diff>`;
}
