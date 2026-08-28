"""Outcome-check policy tests (v12.4.0 — the standard-of-completion release).

Placement guards for the rule that a multi-goal plan is measured as a WHOLE:
ideate's 3+-phase outcome-check phase and its plan-template shape (commands, the
fail-at-base rule, the committed-test form, drivable-surface bullets), define-goal's
fast-path contracting of the outcome phase plus the type-shape sentence admitting a
verification-only goal, dispatch's plan mirror meaning, and the settle-triage
carve-out that stops a whole-outcome gap from being buried as Report-only.

Grounding: Factory's 2026-08-27 study — an agent decomposes a large task, validates
each piece in the context that produced it, and stops early having never established
a complete account of what remained. Flywheel authored the standard per goal but
never for the whole plan: `status: done` was a display stamp fired by the last phase
checking, with no plan-level check anywhere in dispatch.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_subjective_criteria_policy).
Meaning is verified by the RED-baselined dry-runs recorded in the v12.4.0 release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

IDEATE = "skills/ideate/SKILL.md"
TEMPLATE = "skills/ideate/references/plan-template.md"
DEFINE = "skills/define-goal/SKILL.md"
DISPATCH = "skills/dispatch/SKILL.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    return " ".join(read(path).split())


# ---- the template: bullets become commands ------------------------------------

def test_template_outcome_bullets_name_exact_commands():
    text = unwrapped(TEMPLATE)
    assert "Each bullet names the EXACT command that proves it" in text
    assert "<observable outcome> — `<exact command>`" in text


def test_template_keeps_the_independent_review_hatch():
    text = unwrapped(TEMPLATE)
    assert "<subjective outcome> — **needs independent review**" in text
    assert "do not invent a command for it" in text


def test_template_states_the_fail_at_base_rule():
    text = unwrapped(TEMPLATE)
    assert "must FAIL at this plan's base commit" in text
    assert "measuring a piece, not the whole" in text


def test_template_requires_the_committed_test_form():
    """The `-k committed` selector goal 020 runs resolves here."""
    text = unwrapped(TEMPLATE)
    assert "COMMITTED-TEST FORM" in text
    assert "the repo's own suite discovers" in text
    assert "Never an ad-hoc command run once at settle" in text


def test_committed_form_beats_a_stale_one_shot_check():
    """Second `-k committed` guard: WHY the committed form is required."""
    text = unwrapped(TEMPLATE)
    assert "re-run by every later goal's gate" in text
    assert "went stale the moment the next phase landed" in text


def test_template_requires_drivable_surface_bullets():
    text = unwrapped(TEMPLATE)
    assert "DRIVABLE-SURFACE CHECKS" in text
    assert "never a check that only reads or greps source" in text


def test_template_explains_why_visible_checks_stay_safe():
    text = unwrapped(TEMPLATE)
    assert "visible to them by design" in text
    assert "actually build the behavior it measures" in text


def test_template_makes_the_last_phase_the_outcome_check_at_three():
    text = unwrapped(TEMPLATE)
    assert "AT 3 OR MORE PHASES" in text
    assert "It builds nothing" in text
    assert "depends on every other phase" in text


# ---- ideate: minting the phase and self-reviewing it --------------------------

def test_ideate_mints_an_outcome_check_phase_at_three_slices():
    text = unwrapped(IDEATE)
    assert "At 3 or more slices, mint one more phase: the OUTCOME CHECK" in text
    assert "The pieces measure themselves; nothing measures the whole" in text


def test_ideate_outcome_phase_needs_no_new_dispatch_machinery():
    text = unwrapped(IDEATE)
    assert "needs no new dispatch machinery" in text
    assert "phases already map 1:1 onto goals" in text


def test_ideate_self_review_checks_outcomes_fail_at_base():
    text = unwrapped(IDEATE)
    assert "Outcomes fail at base" in text
    assert "fails at the plan's base commit" in text
    assert "reachable by `config.verify` AS WRITTEN" in text


# ---- define-goal: contracting the outcome phase -------------------------------

def test_define_goal_contracts_the_final_phase_as_an_outcome_check():
    text = unwrapped(DEFINE)
    assert "FINAL phase is its outcome check — contract it as one" in text
    assert "`depends_on` every other phase" in text


def test_define_goal_admits_a_verification_only_chore():
    text = unwrapped(DEFINE)
    assert "a VERIFICATION-ONLY goal" in text
    assert "NOT required to prove \"no behavior change\"" in text
    assert "Do not mint a `type: verify`" in text


def test_define_goal_warns_that_an_empty_k_selector_exits_five():
    text = unwrapped(DEFINE)
    assert "exits 5 when it matches nothing" in text
    assert "never left to Interfaces prose" in text


def test_define_goal_never_auto_fixes_a_whole_outcome_miss():
    text = unwrapped(DEFINE)
    assert "a whole-outcome miss is a design fault" in text


# ---- dispatch: what `status: done` means --------------------------------------

def test_plan_status_done_means_outcome_check_passed():
    """Goal 020 selects this test BY EXACT NAME; do not rename it."""
    text = unwrapped(DISPATCH)
    assert "`status: done` means the plan's outcome check PASSED" in text
    assert "not merely that its pieces got built" in text


def test_plan_mirror_stays_a_display_mirror():
    text = unwrapped(DISPATCH)
    assert "A DISPLAY mirror only" in text
    assert "`index.yaml` stays the sole status authority" in text


# ---- dispatch: the settle-triage carve-out ------------------------------------

def test_outcome_falsifying_item_is_never_report_only():
    text = unwrapped(DISPATCH)
    assert "is NEVER Report-only, however unsure you are" in text


def test_report_only_carve_out_names_its_earning_token():
    """Without the token the capture item's own rule would re-route the item."""
    text = unwrapped(DISPATCH)
    assert "carries the `live-defect` earning token by construction" in text
    assert "cannot re-route it" in text


def test_report_only_carve_out_states_the_operative_test():
    text = unwrapped(DISPATCH)
    assert "make an outcome bullet's COMMAND fail" in text
    assert "Being topically related to a bullet is not enough" in text


def test_report_only_carve_out_is_narrow_not_a_rollback():
    text = unwrapped(DISPATCH)
    assert "not a rollback of the capture bar" in text
    assert "stay Report-only exactly as they are" in text


def test_dismiss_and_report_only_have_a_stated_precedence():
    """Independent dry-run 2026-08-29: a wrong test caption matched both
    Dismiss ("purely cosmetic") and Report-only ("test-caption nits") with no
    precedence stated, so the text decided one item two ways."""
    text = unwrapped(DISPATCH)
    assert "Dismiss is for items that are NOT REAL" in text
    assert "when both seem to fit, take 4" in text


def test_report_only_default_survives_the_carve_out():
    """The v12.3.0 strings the carve-out must not overwrite."""
    text = unwrapped(DISPATCH)
    assert "Report-only is the DEFAULT" in text
    assert "(the DEFAULT — unsure lands here)" in text
    assert (
        "If you cannot honestly name one shape, the item is not over the bar → "
        "Report-only" in text
    )
