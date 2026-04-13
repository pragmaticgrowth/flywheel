/**
 * Intelligent prompt for do_research_fast — quick lookup, concise answers.
 */

const TEMPLATE = `<task>
Quick research on the topic below. Provide a concise, actionable answer.
Prioritize speed over exhaustiveness.
</task>

<output_contract>
Keep response under 200 words. Structure as:
1. **Answer** — direct response
2. **Source** — primary reference (URL if available)
3. **Caveat** — anything the caller should verify
</output_contract>

<grounding_rules>
- Only state facts you can verify
- Prefer official docs over community posts
- Say "unsure" rather than guessing
</grounding_rules>`;

export function buildResearchFastPrompt(userPrompt: string): string {
  return `${TEMPLATE}\n\n${userPrompt}`;
}
