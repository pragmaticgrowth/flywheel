"""Subjective-criteria surfacing PLACEMENT tests (goal 003-surface-subjective-criteria).

`define-goal` promises three times that a criterion marked `needs independent
review` reaches a human under needs-you at integration. Dispatch must state that
rule where a reader — and an orchestrator walking the steps — actually meets it:
inside the PASS step of `## Working a goal`, as ONE row of the canonical
needs-you table, and in the Phase 4 needs-you contents rules.

SCOPE — read this before adding an assertion. These are PLACEMENT guards against
regression and accidental deletion, and they claim nothing more. A text-presence
test cannot verify that prose MEANS what it should; two rounds of finer string
matching tried and failed (see the "Amended 2026-07-25" note in
docs/goals/003-surface-subjective-criteria.md). Meaning is verified by the
subagent dry-run and by the orchestrator's gate reviewer — human-judgment
surfaces. Do NOT add assertions here that claim to detect a negated or
contradicted rule.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent

MARKER = "needs independent review"

DISPATCH = "skills/dispatch/SKILL.md"

TABLE_HEADER = "| class | trigger | what to run |"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrap(text: str) -> str:
    """Prose assertions match the text, not where Markdown happens to wrap it."""
    return " ".join(text.split())


def section_lines(heading: str) -> list[str]:
    """The lines of the `## ` section opened by `heading`, up to the next `## `."""
    lines = read(DISPATCH).splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    assert len(starts) == 1, f"{DISPATCH}: expected 1 {heading!r} heading, found {len(starts)}"
    start = starts[0]
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return lines[start:end]


def pass_step_span() -> list[str]:
    """Step 4 of `## Working a goal`: `4. PASS →` up to the next column-0 line.

    An indented line is a continuation of the step; the first non-blank line
    starting at column 0 ends it (today: the `anchor`/`gate_base` paragraph).
    """
    section = section_lines("## Working a goal")
    starts = [i for i, line in enumerate(section) if line.startswith("4. PASS →")]
    assert len(starts) == 1, f"{DISPATCH}: expected 1 `4. PASS →` step, found {len(starts)}"
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(section))
            if section[i].strip() and section[i] == section[i].lstrip()
        ),
        len(section),
    )
    return section[start:end]


def table_span() -> list[str]:
    """The canonical blocker-class table's rows, header line to the next blank line."""
    section = section_lines("## needs-you — the canonical format")
    starts = [i for i, line in enumerate(section) if line.startswith(TABLE_HEADER)]
    assert len(starts) == 1, f"{DISPATCH}: expected 1 blocker-class table, found {len(starts)}"
    start = starts[0]
    end = next(
        (i for i in range(start + 1, len(section)) if not section[i].strip()),
        len(section),
    )
    return section[start:end]


def contents_rules() -> str:
    """The Phase 4 paragraph enumerating what needs-you carries."""
    text = unwrap(read(DISPATCH))
    start = text.index("needs-you lists what is genuinely waiting on the human")
    return text[start:text.index("**Stalled factory", start)]


def test_the_pass_step_span_stays_narrow():
    # A width bound with headroom: if a future restructuring lets this span
    # swallow the rest of the section, the placement assertions below stop
    # meaning anything — so fail loudly here instead.
    span = pass_step_span()
    assert len(span) <= 45, f"the `4. PASS →` span widened to {len(span)} lines"


def test_the_pass_step_states_the_surfacing_rule():
    # Placement only: the marker belongs in the PASS step, where the
    # orchestrator is told what to do on a PASS — not merely somewhere in
    # the file.
    assert MARKER in unwrap("\n".join(pass_step_span())), (
        f"the `4. PASS →` step never names {MARKER!r}"
    )


def test_the_review_class_is_one_row_of_the_canonical_table():
    # One new row in goal 002's table — never a second needs-you format, and
    # never a row pasted somewhere outside the table.
    rows = [
        line for line in table_span()
        if line.startswith(f"| `{MARKER}`") and line.count("|") == 4
    ]
    assert len(rows) == 1, (
        f"expected exactly 1 `{MARKER}` row in the blocker-class table, found {len(rows)}"
    )


def test_the_needs_you_contents_rules_enumerate_the_class():
    assert MARKER in contents_rules(), (
        "the Phase 4 needs-you contents rules do not enumerate the class"
    )
