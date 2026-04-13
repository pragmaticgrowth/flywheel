/**
 * Intelligent prompt for do_architect — architecture analysis with trade-offs.
 */
const TEMPLATE = `<task>
Analyze the architecture of the codebase or the proposed change below.
Evaluate design decisions, identify structural risks, and suggest improvements
with explicit trade-off assessments.
</task>

<output_contract>
Structure your response as:
1. **Architecture Overview** — how the system is structured (brief)
2. **Strengths** — what works well and why
3. **Risks** — structural problems, scalability concerns, coupling issues
4. **Recommendations** — specific, actionable improvements
5. **Trade-offs** — what you'd gain vs lose with each recommendation
</output_contract>

<grounding_rules>
- Base analysis on actual code structure, not assumptions
- Distinguish between "this will break" and "this might become a problem"
- Every recommendation must include a concrete trade-off assessment
- Don't recommend changes that only add complexity without solving a real problem
</grounding_rules>`;
export function buildArchitectPrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=architect.js.map