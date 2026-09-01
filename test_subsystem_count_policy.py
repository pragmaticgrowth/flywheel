"""Subsystem-count Size policy tests (v12.3.0).

The one shape that reliably exceeds one implementer sitting — a `touches:` list
spanning three PRODUCT bands — sailed through every Size check: Size blocked
only on a qualitative "spans multiple subsystems" signal that an atomicity
Context note could downgrade to advisory, and Slice actively endorses thin
vertical goals that cross layers. Measured (2026-08-28, ajww field repo): goal
249 carried 16 globs across supabase/migrations + apps/api + apps/web + docs
(4 bands) and 4 acceptance runners, passed Size, Slice, and the reality
checks, and the lane run then needed touches-closure amends — exactly the
oversized-contract cycle-time tail the one-sitting rule exists to kill
(2026-07-28 forensics: 158 cycles, median ~57 min, every 13–18h outlier an
oversized contract).

The rule closed here, in the settled drain-waiver reading: a `touches:` list
hitting ≥3 of the three product bands {migration/schema, API/server, web/UI}
is contract-blocking Size EVEN WITH an atomicity note (the note still
downgrades the qualitative two-band span, never the count); `docs/goals/**`
never counts; the split of a 3-product-band goal is a `depends_on` chain of
thinner vertical slices; Slice's vertical-cut test is untouched.

SCOPE — text-presence guards against regression and accidental deletion only;
presence is not meaning (see test_subjective_criteria_policy and
test_self_heal_policy for the same concession). Meaning is verified by the
subagent dry-run at release time.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SKILL = "skills/define-goal/SKILL.md"
RED_TEAM = "agents/contract-red-team.md"
CLAUDE = "CLAUDE.md"

# The three surfaces that carry the Size vocabulary: the rule must be stated in
# all of them, or authoring (define-goal's two copies) and review (the red-team
# agent) disagree, with CLAUDE.md drifting from both.
RULE_SURFACES = [SKILL, RED_TEAM, CLAUDE]

BAND_GLOBS = {
    "migration/schema": ["**/migrations/**", "**/supabase/**"],
    "API/server": ["**/apps/api/**", "**/server/**"],
    "web/UI": ["**/apps/web/**", "**/frontend/**"],
}


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    """Prose assertions match the text, not where Markdown happens to wrap it."""
    return " ".join(read(path).split())


# ---- the trigger, stated on every surface ------------------------------------


def test_every_surface_names_all_three_product_bands():
    for path in RULE_SURFACES:
        body = unwrapped(path)
        for band, globs in BAND_GLOBS.items():
            for glob in globs:
                assert glob in body, f"{path}: {band} band missing {glob}"


def test_every_surface_states_the_at_least_three_of_three_trigger():
    for path in RULE_SURFACES:
        body = unwrapped(path)
        assert "≥3 of the three product bands" in body, path
        assert "contract-blocking" in body, path


def test_docs_goals_never_counts_toward_the_band_count():
    # Plans, index, inbox, and goal files are factory state, not product
    # surfaces — counting them is how a thin vertical goal (apps/api +
    # apps/web + its linked plan) would trip a trigger it exists to permit.
    for path in RULE_SURFACES:
        assert "`docs/goals/**` never counts" in unwrapped(path), path


def test_the_count_trigger_is_blocking_even_with_an_atomicity_note():
    for path in RULE_SURFACES:
        assert "even with an atomicity note" in unwrapped(path), path


def test_the_qualitative_two_band_span_keeps_its_atomicity_downgrade():
    # The settled reading narrows ONLY the count: the long-standing downgrade
    # for the qualitative span must survive it, or one rule swallowed the other.
    for path in RULE_SURFACES:
        assert "two-band span" in unwrapped(path), path


def test_the_named_fix_is_a_depends_on_chain_of_thinner_vertical_slices():
    for path in RULE_SURFACES:
        body = unwrapped(path)
        assert "thinner vertical slices" in body, path
        assert "depends_on" in body, path


# ---- both define-goal copies + the red-team agent's item 7 --------------------


def test_both_define_goal_size_copies_carry_the_count_trigger():
    # define-goal states Size twice — the one-sitting authoring rule in the
    # goal-file template and the Size item in its contract-review rubric. The
    # count trigger must live in BOTH or drafting and review disagree.
    body = unwrapped(SKILL)
    authoring = body.partition("**The one-sitting rule.**")[2].partition(
        "Populate the frontmatter"
    )[0]
    review = body.partition("**Size (one-sitting test)**")[2].partition(
        "**Slice (vertical-cut test"
    )[0]
    for name, section in [
        ("one-sitting authoring rule", authoring),
        ("red-team Size check", review),
    ]:
        assert "≥3 of the three product bands" in section, name
        assert "`docs/goals/**` never counts" in section, name
        assert "even with an atomicity note" in section, name


def test_the_red_team_agent_item_7_carries_the_full_trigger():
    # v14.0.0 renumbered the narrowed rubric: Size is item 5, Slice item 6.
    item7 = (
        unwrapped(RED_TEAM)
        .partition("5. **Size (one-sitting test)**")[2]
        .partition("6. **Slice")[0]
    )
    for phrase in [
        "≥3 of the three product bands",
        "`docs/goals/**` never counts",
        "even with an atomicity note",
        "two-band span",
        "thinner vertical slices",
    ]:
        assert phrase in item7, phrase


def test_claude_md_restatement_carries_the_full_trigger():
    # CLAUDE.md restates every Size rule in the define-goal bullet's history;
    # a restatement that omits the count trigger tells a reader of the overview
    # alone that atomicity notes still downgrade everything.
    window = unwrapped(CLAUDE).partition("ONE-SITTING rule")[2][:2500]
    for phrase in [
        "≥3 of the three product bands",
        "`docs/goals/**` never counts",
        "even with an atomicity note",
        "thinner vertical slices",
    ]:
        assert phrase in window, phrase


def test_product_docs_are_a_fourth_band_not_a_renamed_trigger():
    # docs/** minus docs/goals/** may count as a FOURTH band; the trigger stays
    # ≥3 of the three PRODUCT bands. Pinning this stops a later edit from
    # silently widening the trigger to "any three of four bands", which would
    # re-legalize the measured migration+api+web+docs goal.
    for path in [SKILL, RED_TEAM]:
        assert "fourth band" in unwrapped(path), path


def test_the_rule_carries_its_field_grounding():
    # The one-sitting rule's forensic style: the measured case that motivated
    # the count trigger stays attached to the rule text.
    assert "16-glob" in unwrapped(SKILL)


# ---- Slice's vertical-cut test stays untouched --------------------------------


def test_slice_still_endorses_the_thin_end_to_end_path():
    # The count trigger narrows Size only; Slice's vertical-cut endorsement is
    # what keeps thin apps/api + apps/web vertical goals LEGAL, and the new
    # count text must not leak into it.
    slice_bullet = (
        unwrapped(SKILL)
        .partition("**Slice (vertical-cut test")[2]
        .partition("- **Cross-goal**")[0]
    )
    assert "thinnest end-to-end path first" in slice_bullet
    assert "three product bands" not in slice_bullet
    item8 = (
        unwrapped(RED_TEAM)
        .partition("8. **Slice (vertical-cut test)**")[2]
        .partition("9. **Cross-goal**")[0]
    )
    assert "three product bands" not in item8
