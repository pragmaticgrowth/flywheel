/**
 * Intelligent prompt for do_silent_scan — find swallowed errors and silent failures.
 */

const TEMPLATE = `<task>
Scan the codebase for silent failures: swallowed errors, empty catch blocks,
ignored promise rejections, .catch(() => {}), missing error handling on I/O,
and any pattern where errors are consumed without logging or re-throwing.
</task>

<output_contract>
For each finding:
- **Location**: file:line
- **Pattern**: type of silent failure (swallowed error, ignored promise, etc.)
- **Risk**: what would happen if this error occurs silently in production
- **Fix**: how to properly handle or propagate the error

Order by risk: data loss / security > degraded UX > cosmetic.
</output_contract>

<grounding_rules>
- Only report patterns you find in the actual code
- Intentional error suppression with a comment explaining why is NOT a finding
- Focus on I/O boundaries, network calls, file operations, database queries
- An empty catch with a TODO comment is a finding; an empty catch with a
  "deliberately swallowed" comment is not
</grounding_rules>`;

export function buildSilentScanPrompt(userPrompt: string): string {
  return `${TEMPLATE}\n\n${userPrompt}`;
}
