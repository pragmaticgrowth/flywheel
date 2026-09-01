"""Ratchet policy tests (v12.4.0 — the standard-of-completion release).

Placement guards for the rule that a standard may only get stricter: define-goal's
amend-mode classification and its amend-only reality check item 10, the red-team's
item 15 (both the amended-contract and the plan-derived shapes), the retire-evidence
rule, the drain waiver's inability to reach any of it, and ideate's plan-iteration
ratchet on `## What will be true when done` bullets.

Grounding: Factory's 2026-08-27 study — an agent that authors its own definition of
done stops early, and a standard that can soften stops measuring. Since v12.0.0
dispatch's self-heal rewrites blocked contracts in-run with nobody watching, and
nothing compared the rewrite against what it replaced. Goal 018 adds the second
half: the outcome bullets live in the PLAN, which has no immutability rule at all,
so ratcheting goal files alone leaves an unguarded upstream source.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_subjective_criteria_policy).
Meaning is verified by the RED-baselined dry-runs recorded in the v12.4.0 release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFINE = "skills/define-goal/SKILL.md"
IDEATE = "skills/ideate/SKILL.md"
RED_TEAM = "agents/contract-red-team.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    return " ".join(read(path).split())


# ---- define-goal: amend-mode classification -----------------------------------

def test_amend_classifies_every_edit_against_the_previous_commit():
    text = unwrapped(DEFINE)
    assert "THE RATCHET" in text
    assert "git show HEAD:docs/goals/<id>.md" in text
    assert "monotonically" in text


def test_weakening_shapes_are_enumerated():
    text = unwrapped(DEFINE)
    for shape in (
        "a criterion deleted and not replaced",
        "a threshold loosened",
        "an assertion a human or agent must vouch for",
        "a code-reading check",
        "loses its BEFORE",
        "`needs independent review` flag removed",
    ):
        assert shape in text, shape


def test_tightening_shapes_proceed_unattended():
    text = unwrapped(DEFINE)
    assert "Tightening or repair" in text
    assert "proceeds unattended" in text
    for shape in (
        "a criterion added",
        "pinned to the STRICTER reading",
        "moved to a `depends_on` prior",
    ):
        assert shape in text, shape


def test_weakening_stops_for_the_owner():
    text = unwrapped(DEFINE)
    assert "STOPS FOR THE OWNER, drain waiver or not" in text
    assert "stays `blocked` until they do" in text


def test_review_marker_cannot_launder_a_weakening():
    """Independent dry-run 2026-08-29 flagged this as two-readable: the skill
    sanctions `needs independent review` as an authoring shape, so a command →
    marker downgrade could be argued legitimate. Pinned to the stricter reading."""
    text = unwrapped(DEFINE)
    assert "does NOT launder a weakening" in text
    assert "never a downgrade path for a criterion that already had a command" in text


def test_implementer_failure_is_never_a_reason_to_lower_the_bar():
    assert (
        "\"The implementer could not pass it\" is never itself a reason to lower the bar"
        in unwrapped(DEFINE)
    )


def test_amendment_note_records_the_classification():
    text = unwrapped(DEFINE)
    assert "(ratchet: tightening|repair)" in text
    assert "The ratchet field is not optional" in text
    assert "owner-approved" in text


# ---- define-goal: retire is the largest weakening -----------------------------

def test_retire_is_under_the_ratchet_and_needs_hard_evidence():
    text = unwrapped(DEFINE)
    assert "Retire is under the ratchet too" in text
    assert "COMMAND OUTPUT or a quoted primary artifact" in text
    assert "own reasoning as the sole evidence stops for the owner" in text


# ---- define-goal: the waiver cannot reach the ratchet -------------------------

def test_drain_waiver_never_waives_the_ratchet():
    text = unwrapped(DEFINE)
    assert "The waiver never reaches the ratchet" in text
    assert "contract-blocking under the waiver exactly as they are interactively" in text


# ---- define-goal: reality check item 10 (amend-only) --------------------------

def test_reality_check_has_an_amend_only_ratchet_item():
    text = unwrapped(DEFINE)
    assert "10. **The ratchet" in text
    assert "AMEND MODE ONLY" in text
    assert "does not run on a fresh draft" in text


def test_reality_check_header_count_matches_its_items():
    text = unwrapped(DEFINE)
    assert "Run these ten checks" in text
    assert "eight checks" not in text


# ---- red-team item 15 ---------------------------------------------------------

def test_red_team_has_a_ratchet_item():
    # v14.0.0 narrowed the rubric to the judgment items; Ratchet is item 9.
    text = unwrapped(RED_TEAM)
    assert "9. **Ratchet**" in text
    assert "a standard may only get stricter" in text


def test_red_team_ratchet_is_contract_blocking_and_unrationalisable():
    text = unwrapped(RED_TEAM)
    assert "on both it is **contract-blocking**" in text
    assert "never fires on a fresh draft" in text
    assert "the rationale IS the defect" in text


# ---- the plan half (goal 018) -------------------------------------------------

def test_red_team_ratchet_covers_plan_derived_outcome_goals():
    text = unwrapped(RED_TEAM)
    assert "A plan-derived outcome goal" in text
    assert "git show HEAD:docs/goals/plans/<file>.md" in text
    assert "HOWEVER the plan was edited" in text


def test_red_team_names_the_plan_back_door():
    assert "This is the back door the goal-file ratchet alone leaves open" in unwrapped(
        RED_TEAM
    )


def test_ideate_ratchets_plan_outcome_bullets_on_iteration():
    text = unwrapped(IDEATE)
    assert "git show HEAD:docs/goals/plans/<file>.md" in text
    assert "weakening" in text and "tightening" in text


def test_plan_ratchet_scope_is_only_the_outcome_bullets():
    text = unwrapped(IDEATE)
    assert "ONLY the `## What will be true when done` bullets" in text
    assert "stays freely editable" in text


def test_plan_ratchet_treats_section_removal_as_weakening():
    text = unwrapped(IDEATE)
    assert "Renaming or removing the `## What will be true when done` section" in text
    assert "every bullet deleted" in text


def test_plan_ratchet_exempts_a_first_time_plan():
    text = unwrapped(IDEATE)
    assert "no previous commit" in text


def test_plan_weakening_stops_for_the_owner():
    text = unwrapped(IDEATE)
    assert "stops for the owner" in text


def test_ideate_names_itself_as_a_ratchet_site():
    assert "ideate is where the standard is authored" in unwrapped(IDEATE)


def test_plan_ratchet_records_known_residual_routes():
    text = unwrapped(IDEATE)
    assert "does not close every route" in text
    assert "what a command ASSERTS" in text
