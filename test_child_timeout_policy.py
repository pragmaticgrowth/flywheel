"""Child-session timeout + Arm A one-wait policy tests (goal 014).

`Error running task subagent: Child session timed out due to inactivity` was
named by no infra-class rule: the pin-failure paragraph and Re-entrancy's
stale-claim bullet listed stream-idle, 529, connection closed, billing/auth/
overload — not the child-session timeout — so a sitting that died that way
burned respawns as a work failure instead of one same-tier transient respawn,
and Arm A's join text ("wait on that task") banned no poll loop, so joins were
implemented as repeated sleep+`ps` / task-status polls (the 2026-08-17
four-lane Droid run burned 293 poll calls — 34% of its turns — before this
class of shape got its first explicit ban; verified 2026-08-28, provenance
inbox-drain). After this goal: the timeout is a transient infrastructure death
— one same-tier respawn, pin off only if the error also names model/provider,
not a fail toward the no-progress rule, and the resume-from-increments rung
(goal 009) when `gate_base..HEAD` is non-empty — and the Arm A join is one
wait, then read the output, never a repeated poll loop on Droid.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped_text(text: str) -> str:
    return " ".join(text.split())


def stale_claim_step() -> str:
    """Re-entrancy rule 2 (stale claim / transient deaths) up to rule 3."""
    text = read(DISPATCH)
    start = text.index("2. **Stale claim**")
    end = text.index("3. **Finish before claiming**", start)
    span = text[start:end]
    assert 30 <= span.count("\n") <= 120, (
        f"stale-claim step span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


def pin_failure_paragraph() -> str:
    """The pin-failure fallback paragraph, up to the tier-application paragraph."""
    text = read(DISPATCH)
    start = text.index("**Pin-failure fallback")
    end = text.index("A non-`inherit` tier applies", start)
    span = text[start:end]
    assert 10 <= span.count("\n") <= 45, (
        f"pin-failure paragraph span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


def arm_a_join() -> str:
    """The Arm A join paragraph, up to the flake protocol."""
    text = read(DISPATCH)
    start = text.index("**Join — no verdict before BOTH arms are in hand.**")
    end = text.index("**Flake protocol", start)
    span = text[start:end]
    assert 3 <= span.count("\n") <= 15, (
        f"arm A join span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


# ---- Re-entrancy rule 2: the child-session timeout block ---------------------

def test_stale_claim_classifies_child_timeout_as_transient_not_work_failure():
    span = stale_claim_step()
    assert "Child session timed out due to inactivity" in span
    assert "NOT a work failure" in span
    assert "not a fail toward the no-progress rule" in span


def test_child_timeout_respawns_once_at_same_tier_with_pin_conditional():
    span = stale_claim_step()
    assert "respawn it ONCE at the SAME tier" in span
    assert (
        "the pin comes off only when the error text also names the model or "
        "provider" in span
    )
    assert "never for this timeout alone" in span


def test_repeat_timeout_reenters_stale_claim_rules_not_a_second_free_respawn():
    span = stale_claim_step()
    assert "not a second free respawn" in span
    assert "re-enters these stale-claim rules" in span


def test_nonempty_tree_routes_to_the_resume_from_increments_rung():
    span = stale_claim_step()
    assert "`gate_base..HEAD` non-empty" in span
    assert "resume-from-increments rung" in span
    assert "read `gate_base..HEAD`" in span
    assert "re-brief ONE fresh worker" in span
    assert "what already landed" in span
    assert "never a from-scratch respawn" in span
    assert "escalation-and-repair.md" in span


def test_error_classification_precedes_the_rung():
    span = stale_claim_step()
    assert (
        span.index("Child session timed out due to inactivity")
        < span.index("resume-from-increments rung")
    )


# ---- pin-failure fallback: the guard against unpinning a child timeout -------

def test_pin_paragraph_guards_child_timeout_against_pin_removal():
    span = pin_failure_paragraph()
    assert "names NONE of those classes" in span
    assert "Child session timed out due to inactivity" in span
    assert "is not pin failure" in span
    assert "Re-entrancy transient" in span
    assert "respawned ONCE at the SAME tier" in span
    assert (
        "the pin stays on unless the error text also names the model or "
        "provider" in span
    )
    # classification defers to Re-entrancy's transient/work-failure split
    assert "Re-entrancy rule 2" in span


# ---- Arm A join: one wait, never a poll loop ----------------------------------

def test_arm_a_join_waits_once_then_reads_output_banning_droid_poll_loops():
    span = arm_a_join()
    assert "wait on that task ONCE, then read the output" in span
    assert "on Droid, never a repeated sleep+`ps` / task-status poll loop" in span
    assert "one wait, then read the output" in span
    # the pre-existing bar survives verbatim
    assert "never grade a partial gate" in span


def test_once_precedes_the_poll_loop_ban():
    span = arm_a_join()
    assert span.index("ONCE") < span.index("never a repeated")
