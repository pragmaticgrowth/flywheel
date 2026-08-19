"""Contract-scope policy tests (v12.1.0).

Two defect classes that each cost a real drain, both closed here:

1. A goal that BECOMES plan-backed during implementation. The implementer brief
   mandates `writing-plans` for any change spanning >2 files, so the plan doc is
   written after the contract declared its surfaces — and the gate's blast-radius
   arm then flagged a doc the factory itself told the implementer to write.
   Measured twice (2026-08-18, 2026-08-19); the second cost a contract amendment
   mid-drain with every other arm green.

2. A criterion asserting an absolute ("cannot", "impossible", "never") whose own
   Constraints forbid the only mechanism that could deliver it. The operative half
   ships, the gate reviewer returns contract=FAIL on the consequence clause, and
   the orchestrator ends up adjudicating the criterion instead of the code.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text()


def read_unwrapped(path: str) -> str:
    """Prose assertions match the text, not where Markdown happens to wrap it."""
    return " ".join(read(path).split())


def _pgv():
    spec = importlib.util.spec_from_file_location(
        "pgv", ROOT / "skills/dispatch/scripts/pg_validate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- 1. plan docs are exempt from blast radius, and ONLY plan docs -------------


def test_plan_docs_under_both_conventions_are_recognised():
    is_plan_doc = _pgv().is_plan_doc
    # ideate's design tier, a repo's own writing-plans output, their done/ archives,
    # and a bare top-level plans/ dir.
    assert is_plan_doc("docs/goals/plans/2026-08-19-topic.md")
    assert is_plan_doc("docs/superpowers/plans/2026-08-19-topic.md")
    assert is_plan_doc("docs/goals/plans/done/2026-01-01-old.md")
    assert is_plan_doc("plans/topic.md")


def test_the_exemption_can_never_reach_code_or_ordinary_docs():
    # The whole safety argument for exempting these is that the pattern cannot
    # match anything executable. A `plans/` directory holding source, or a doc
    # merely named like a plan, must stay in scope.
    is_plan_doc = _pgv().is_plan_doc
    assert not is_plan_doc("src/plans/planner.ts")
    assert not is_plan_doc("plans/script.py")
    assert not is_plan_doc("docs/plans-overview.md")
    assert not is_plan_doc("docs/context/ai-models.md")
    assert not is_plan_doc("README.md")


def test_blast_radius_passes_a_plan_doc_outside_touches():
    # The measured failure: goal 159's real path set against the touches: it was
    # drafted with, before the plan existed.
    blast_radius = _pgv().blast_radius
    changed = [
        "docs/context/ai-models.md",
        "docs/superpowers/plans/2026-08-19-gateway-prompt-cache-answer.md",
        "scripts/prompt-cache-probe.ts",
        "test/unit/prompt-cache-probe.test.ts",
    ]
    touches = ["scripts/prompt-cache-probe.ts", "docs/context/ai-models.md"]
    assert blast_radius(changed, touches)["pass"] is True


def test_blast_radius_still_fails_a_stray_doc():
    # The exemption must not blunt the arm: a doc that is not a plan doc, outside
    # the declared surfaces, is still out-of-scope churn.
    result = _pgv().blast_radius(["src/a.ts", "docs/other/thing.md"], ["src/**"])
    assert result["pass"] is False
    assert "docs/other/thing.md" in result["evidence"]


def test_the_exemption_records_why_it_exists():
    # A bare `if is_plan_doc(p): continue` reads as a hole in the scope guard;
    # the rationale is what stops a later reader from "tightening" it back.
    body = read_unwrapped("skills/dispatch/scripts/pg_validate.py")
    assert "if is_plan_doc(p):" in body
    assert "writing-plans" in body


# --- 2. an absolute criterion must name its enforcing mechanism ---------------


ABSOLUTE_RULE_DOCS = [
    "skills/define-goal/SKILL.md",
    "agents/contract-red-team.md",
]


def test_both_the_skill_and_its_red_team_agent_carry_the_absolute_rule():
    # The check has to fire in BOTH places or it only half-exists: define-goal runs
    # it mechanically before drafting, the agent re-checks it on the draft.
    for path in ABSOLUTE_RULE_DOCS:
        body = read_unwrapped(path)
        assert '"cannot", "impossible", or "never"' in body, path
        assert "contract-blocking" in body, path


def test_the_rule_demands_the_mechanism_be_inside_touches():
    # Naming a mechanism that lives outside the goal's surfaces is exactly the
    # measured defect — the absolute is still undeliverable.
    for path in ABSOLUTE_RULE_DOCS:
        body = read_unwrapped(path)
        assert "inside `touches:`" in body, path


def test_the_rule_names_the_weaker_true_consequence_as_the_fix():
    # Without a named fix a reviewer just blocks the goal; the point is to make the
    # contract sayable.
    for path in ABSOLUTE_RULE_DOCS:
        body = read_unwrapped(path)
        assert "weaker" in body and "TRUE consequence" in body.replace(
            "true consequence", "TRUE consequence"
        ), path


def test_the_rule_is_distinguished_from_the_constraints_reality_check():
    # These two are easy to collapse into each other, and collapsing them loses the
    # case: Constraints-reality catches a bad pasted CONSTRAINT, this catches a
    # criterion whose CONSEQUENCE outruns its own Constraints.
    for path in ABSOLUTE_RULE_DOCS:
        body = read_unwrapped(path)
        assert "CONSEQUENCE" in body, path
        assert "CONSTRAINT" in body, path


def test_define_goal_hands_the_new_check_to_the_red_team():
    # The hand-off line enumerates which mechanical checks the red-team re-checks;
    # a new check that is not listed there is silently orchestrator-only.
    body = read_unwrapped("skills/define-goal/SKILL.md")
    assert "The red-team re-checks 1–3 and 6–9" in body
