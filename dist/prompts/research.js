/**
 * Intelligent prompt for do_research — deep web research with structured output.
 */
const TEMPLATE = `<task>
Deep research on the topic below. Search the web, documentation, forums, and code repositories.
Synthesize findings into a structured report with source citations.
</task>

<output_contract>
Structure your response as:
1. **Key Findings** — bullet points, most important first
2. **Sources** — URL + one-line summary per source
3. **Confidence** — what you're certain about vs uncertain
4. **Open Questions** — what remains unknown or needs further investigation
</output_contract>

<grounding_rules>
- Clearly separate observed facts from inferences
- Cite sources for every factual claim
- State "I could not verify" rather than guessing
- Do not fabricate URLs or documentation references
- Separate "what the docs say" from "what the community reports"
</grounding_rules>`;
export function buildResearchPrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=research.js.map