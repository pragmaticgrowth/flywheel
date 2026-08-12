"""Needs-you answerability policy tests (goal 002-answerable-needs-you).

Every human decision the factory surfaces must name the exact command that
resolves it: ONE canonical line-shape + blocker-class table in dispatch, an
attended-only interactive-question rule, define-goal's `--amend <id>` mode, and
the narrowed "immutable contracts" invariant.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent

LINE_SHAPE = "<id or item> — <reason> → <what to run>"

INVARIANT_DOCS = ["README.md", "public/index.html", "CLAUDE.md", "AGENTS.md"]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def read_unwrapped(path: str) -> str:
    """Prose assertions match the text, not where Markdown happens to wrap it."""
    return " ".join(read(path).split())


def test_dispatch_defines_the_line_shape_exactly_once():
    # One canonical format section — the emission sites reference it by class
    # instead of each restating the shape (that duplication is the defect).
    assert read("skills/dispatch/SKILL.md").count(LINE_SHAPE) == 1


def test_dispatch_maps_every_blocker_class_to_a_resolving_command():
    text = read("skills/dispatch/SKILL.md")
    for trigger, command in (
        ("contract defect: <criterion> ambiguous", "/define-goal --amend <id>"),
        ("contract defect: <criterion> unreachable", "/define-goal --amend <id>"),
        ("contract defect: <the verified finding>", "/define-goal --amend <id>"),
        ("contract defect: <reason>", "/define-goal --amend <id>"),
        ("no runnable local gate: <evidence>", "/factory-doctor"),
        ("environment brake", "/factory-doctor"),
        ("repeated transient death", "/dispatch <id>"),
        ("budget exhausted", "config.budget.max_goals_per_session"),
        ("base:` mismatch", "git checkout"),
        ("multiple in_progress", "manual review"),
        ("CI failure", "gh run view"),
    ):
        row = [ln for ln in text.splitlines() if trigger in ln and command in ln]
        assert row, f"no needs-you table row maps {trigger!r} to {command!r}"


def test_dispatch_names_the_class_at_every_emission_site():
    # Each site names its class so a reader (and goal 003) can look the
    # resolving command up in the one table.
    text = read_unwrapped("skills/dispatch/SKILL.md") + " " + " ".join(
        " ".join(f.read_text().split())
        for f in sorted((ROOT / "skills" / "dispatch" / "references").glob("*.md"))
    )
    for marker in (
        "class `environment brake`",
        "class `conflict`",
        "class `budget exhausted`",
        "class `contract defect (unreachable)`",
        "class `CI failure`",
        "class `environment failure`",
        "class `contract defect (finding)`",
        "class `no runnable local gate`",
        "class `multiple in_progress`",
        "class `base: mismatch`",
        "class `contract defect (ambiguous)`",
        "class `needs context`",
        "class `contract defect (too large / wrong)`",
        "class `unmet dependency`",
        "class `recurring lesson`",
    ):
        assert marker in text, f"no emission site names {marker}"


def test_dispatch_attended_question_rule_requires_all_three_conditions():
    text = read_unwrapped("skills/dispatch/SKILL.md")
    assert "Attended-only interactive questions" in text
    for condition in (
        "invoked `/dispatch` conversationally in this session",
        "single-goal-scoped",
        "not `/loop`, `claude -p`, or `droid exec`",
        "ALL THREE",
    ):
        assert condition in text, f"attended rule missing: {condition}"
    # Defaults: unknown → do not ask; a batch run never asks.
    assert "unknown or unverifiable" in text and "do NOT ask" in text
    assert "A drain or multi-goal run NEVER asks" in text
    # Bounded: one round, at most 2 questions, options + recommended default.
    assert "ONE round, at most 2 questions" in text
    assert "recommended default" in text


def test_define_goal_ships_an_amend_mode():
    text = read("skills/define-goal/SKILL.md")
    assert "--amend <id>" in text
    assert "## Invocation — `/define-goal [<want>] [--amend <id>]`" in text
    # Discoverable + routable from the frontmatter.
    head = text.split("---", 2)[1]
    assert "--amend <id>" in head, "argument-hint must advertise --amend"
    description = head.lower().split("argument-hint")[0]
    # Routable: the description must name the trigger (a BLOCKED goal's broken
    # contract), not merely contain the letters "amend".
    assert "--amend" in description and "blocked goal" in description, (
        "description must route an amend of a blocked goal's contract"
    )


def test_amend_mode_specifies_its_ordered_steps():
    text = read_unwrapped("skills/define-goal/SKILL.md")
    for step in (
        "not `blocked`",                                    # refuse non-blocked
        "reports the actual status",
        "~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md",  # report read
        "missing or stale report is non-fatal",
        "ONE round either way",                             # one-round cap (v11: the
                                                            # round itself is conditional
                                                            # on a true owner fork)
        "ONLY the criteria the reason identifies as defective",
        "contract-red-team",                                # re-review
        "chore(goals): amend <id>",                         # requeue commit
        "status` back to `not_started`",
        "clearing the stale `reason`",
        "amendment note",                                   # Context note
    ):
        assert step in text, f"--amend mode missing: {step}"


def test_amend_never_writes_status_into_goal_frontmatter():
    text = read_unwrapped("skills/define-goal/SKILL.md")
    assert "status stays ONLY in `index.yaml`" in text


def test_immutable_contracts_invariant_is_narrowed_everywhere():
    hits = 0
    for path in INVARIANT_DOCS:
        for i, line in enumerate(read(path).splitlines(), 1):
            if "immutable contracts" in line:
                hits += 1
                assert "amend" in line.lower(), (
                    f"{path}:{i}: 'immutable contracts' without the --amend exception"
                )
    assert hits == 4, f"expected 4 invariant sites, found {hits}"


def test_public_docs_describe_the_amend_mode():
    for path in ["README.md", "public/index.html"]:
        assert "--amend" in read(path), f"{path}: --amend mode undocumented"
