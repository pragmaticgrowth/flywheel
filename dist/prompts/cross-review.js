/**
 * Prompt framing for cross-model review — wraps user prompt with
 * instructions optimized for parallel multi-model execution.
 */
const TEMPLATE = `Your findings will be merged with independent reviews from other models.
Different models catch different blind spots — be thorough in your area of strength.

<output_contract>
Be specific: cite file:line for every finding.
Focus on real bugs and edge cases, not style.
Max 300 words. Severity: critical | warning | info per finding.
If no issues found, say so in one line — do not pad.
</output_contract>

<grounding_rules>
- Only report issues you can verify from the code
- Do not repeat obvious observations — focus on what others might miss
- Zero findings is valid — do not invent issues
</grounding_rules>`;
export function buildCrossReviewPrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=cross-review.js.map