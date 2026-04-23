/**
 * Intelligent prompt for do_review — code review focused on real bugs.
 * Inspired by Codex adversarial-review pattern: default to skepticism,
 * cite file:line, only report material issues.
 */
const TEMPLATE = `<task>
Review the code for bugs, security vulnerabilities, edge cases, and correctness issues.
Focus on material problems only — not style, formatting, or naming conventions.
Default to skepticism: actively try to find what can go wrong.
</task>

<output_contract>
For each finding:
- **Severity**: critical | warning | info
- **Location**: file:line
- **Issue**: What's wrong (one sentence)
- **Impact**: What can go wrong in production
- **Fix**: Concrete suggestion (code snippet if applicable)

Order by severity (critical first). Max 10 findings.
If no material issues found, say "No material issues found" — do not invent findings.
</output_contract>

<grounding_rules>
- Only report issues you can verify from the actual code
- Cite exact file:line for every finding
- Do not suggest refactors unless they fix a real bug
- "Potential issue" is acceptable when evidence is circumstantial
- Do not add findings to fill space — zero findings is a valid outcome
</grounding_rules>`;
export function buildReviewPrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=review.js.map