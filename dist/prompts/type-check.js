/**
 * Intelligent prompt for do_type_check — TypeScript type design review.
 */
const TEMPLATE = `<task>
Review TypeScript type design for correctness, safety, and expressiveness.
Look for: any leaks, overly-permissive unions, missing discriminators,
unsafe casts (as), missing nullability, incorrect generics, and types
that don't reflect runtime reality.
</task>

<output_contract>
For each finding:
- **Location**: file:line
- **Issue**: what's wrong with the type
- **Risk**: what runtime error or incorrect behavior this could cause
- **Fix**: the correct type signature or approach

Categorize as: type-safety | expressiveness | consistency.
</output_contract>

<grounding_rules>
- Only flag types that could cause runtime errors or hide bugs
- Don't flag 'any' in test files unless it masks a real issue
- 'unknown' with proper narrowing is correct, not a finding
- Type assertions (as) are findings only when they could be wrong at runtime
</grounding_rules>`;
export function buildTypeCheckPrompt(userPrompt) {
    return `${TEMPLATE}\n\n${userPrompt}`;
}
//# sourceMappingURL=type-check.js.map