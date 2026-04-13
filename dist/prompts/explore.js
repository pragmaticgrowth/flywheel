/**
 * Intelligent prompt for do_explore — codebase navigation and understanding.
 */
const TEMPLATE = `<task>
Navigate the codebase to answer the question below. Read files, follow imports,
trace call chains. Build a map of the relevant code paths.
</task>

<output_contract>
Structure your response as:
1. **Answer** — direct answer to the question
2. **Key Files** — file:line references for the most relevant code
3. **Call Chain** — how the code flows (if applicable)
4. **Related** — other files or functions worth knowing about
</output_contract>

<grounding_rules>
- Only reference files and functions you have actually read
- Include exact file paths and line numbers
- If you can't find something, say so — don't guess
- Distinguish between "the code does X" and "the code appears to do X"
</grounding_rules>`;
export function buildExplorePrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=explore.js.map