"""Report-line honesty policy tests (goal 011-report-line-honesty).

Two measured defects in one envelope (fold of two inbox lines, provenance
inbox-drain, verified 2026-08-28):

1. PLAN-TOOL CLOSER LEAK — the OUTPUT ENVELOPE (skills/dispatch/SKILL.md
   :1011-1034) said the closing turn is "the report line, the summary line, one
   bullet per needs-you item, one bullet per fyi item. Nothing else" but never
   SEQUENCED the harness's own plan/artifact status acknowledgement, so Droid
   drains let plan-tool acknowledgement prose ("Plan is up-to-date.") land
   AFTER the report line — a second closing message wearing a tool label.
2. COUNTER DRIFT — Phase 4 said "the counts come from the index after this
   iteration's mutations" without saying HOW, and mid-drain report lines
   derived done/ready/blocked/total by incrementing a remembered count, which
   drifts the first time a Phase 1 settle, a Self-heal retire, or a blocked
   requeue changes the index between fires without the counting session
   seeing it.

After this goal: the envelope names the plan-tool update (any harness
plan/artifact status acknowledgement, including "Plan is up-to-date.") as a
PRE-CLOSING action — allowed, never banned, but it lands before the closing
turn so the closer stays the run's last message — and Phase 4 requires
deriving every counter from ONE `index.yaml` read at settle time, never an
incremented remembered count.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_self_heal_policy for the
same concession). Meaning is verified by the orchestrator's gate reviewer.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
CLAUDE = "CLAUDE.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    """Prose assertions match the text, not where Markdown happens to wrap it."""
    return " ".join(read(path).split())


def output_envelope() -> str:
    """The OUTPUT ENVELOPE section, from its heading to Phase 4's counters prose."""
    return (
        unwrapped(DISPATCH)
        .partition("**The output envelope")[2]
        .partition("Lead with **progress**")[0]
    )


def phase4_counters() -> str:
    """Phase 4's counter prose, from the progress lead to the bar spec."""
    return (
        unwrapped(DISPATCH)
        .partition("Lead with **progress**")[2]
        .partition("The bar is 20 cells")[0]
    )


def claude_md_envelope_restatement() -> str:
    """CLAUDE.md's dispatch-bullet restatement of the envelope."""
    return (
        unwrapped(CLAUDE)
        .partition("OUTPUT ENVELOPE")[2]
        .partition("DECLARATIVE STALLS")[0]
    )


# ---- the plan-tool update is sequenced pre-closing ---------------------------


def test_envelope_names_the_plan_tool_update_as_a_pre_closing_action():
    env = output_envelope()
    assert "PRE-CLOSING" in env
    # The acknowledgement named from the field: Droid's literal closer-leak line.
    assert "Plan is up-to-date." in env


def test_the_plan_tool_update_is_allowed_not_banned():
    # The rule sequences an allowed action; it must not read as a prohibition —
    # the harness emits the acknowledgement either way, so the defect was WHERE
    # it landed, not THAT it happened.
    assert "ALLOWED" in output_envelope()


def test_the_closer_stays_the_runs_last_message():
    env = output_envelope()
    assert "BEFORE the closing turn" in env
    assert "last message" in env


# ---- counters derive from ONE index read at settle ---------------------------


def test_phase4_counters_derive_from_one_index_read_at_settle():
    counters = phase4_counters()
    assert "ONE fresh read of `index.yaml` at settle time" in counters
    assert "single read" in counters


def test_phase4_forbids_the_incremented_remembered_count():
    # The drift shape named, not just the good shape: a remembered `done += 1`
    # is what actually drifted on Droid drains.
    counters = phase4_counters()
    assert "never an incremented remembered count" in counters
    for counter in ("done", "ready", "blocked", "total"):
        assert counter in counters, counter


# ---- the CLAUDE.md restatement carries both rules -----------------------------


def test_claude_md_restatement_carries_the_pre_closing_rule():
    w = claude_md_envelope_restatement()
    for phrase in ("PRE-CLOSING", "Plan is up-to-date.", "lands BEFORE", "allowed"):
        assert phrase in w, phrase


def test_claude_md_restatement_carries_the_one_read_counter_rule():
    w = claude_md_envelope_restatement()
    assert "ONE `index.yaml` read at settle" in w
    assert "incremented remembered count" in w
