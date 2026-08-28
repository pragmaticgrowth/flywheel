"""Front-door policy tests (goal 013-front-door-guide).

Forensic grounding (goal Context, verified 2026-08-28): ideate's description
triggered on single-idea language only — an owner arriving with N unshaped
issues had no named entry path (define-goal's batch mode is for already-shaped
items) — and goals-status printed queue state with no next command, so the
status view never told the owner which skill to run. The fix: ideate's front
door names the N-item list arrival, and goals-status ends with one `next:`
line derived from queue state (/dispatch → /process-inbox → /ideate,
first match).

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_capture_bar_policy). The
next: derivation BEHAVIOR is proven by
skills/goals-status/scripts/test_goals_status.py; meaning is verified by the
subagent dry-runs recorded with the goal.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

IDEATE = "skills/ideate/SKILL.md"
GSTATUS = "skills/goals-status/SKILL.md"
GSTATUS_PY = "skills/goals-status/scripts/goals_status.py"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrap(text: str) -> str:
    return " ".join(text.split())


def unwrapped(path: str) -> str:
    return unwrap(read(path))


def frontmatter(path: str) -> str:
    """The text between the opening `---` and the closing `---`."""
    text = read(path)
    assert text.startswith("---\n"), f"{path}: no frontmatter"
    return text[4:text.index("\n---", 4)]


def parsed_frontmatter(path: str) -> dict:
    data = yaml.safe_load(frontmatter(path))
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data


def description_of(path: str) -> str:
    """The parsed `description:` value.

    Parsed as YAML, never unwrapped from raw text: a description wrapped
    mid-scalar onto an unindented line is invalid frontmatter and silently
    breaks the skill trigger (lens-1 Critical on this goal's first sitting) —
    validity is part of the policy, so it must fail HERE, not in the field.
    """
    data = parsed_frontmatter(path)
    d = data.get("description")
    assert isinstance(d, str) and d.strip(), f"{path}: no description string"
    return " ".join(d.split())


def test_both_front_door_frontmatters_parse_as_valid_yaml():
    for path in (IDEATE, GSTATUS):
        data = parsed_frontmatter(path)
        assert data.get("name"), f"{path}: no name field"


# ---- band 1: ideate's front door takes the N-item list ------------------------

def test_ideate_description_names_the_n_item_list_entry_path():
    d = description_of(IDEATE)
    assert "unshaped list" in d
    assert "I have N issues/items, where do I start?" in d


def test_the_list_paragraph_sits_in_the_overview_before_the_hard_gate():
    text = unwrapped(IDEATE)
    assert text.index("When a plan, when not") \
        < text.index("Arriving with a list") \
        < text.index("HARD GATE")


def ideate_list_paragraph() -> str:
    """The overview paragraph naming N-item list arrivals (wrap-tolerant)."""
    text = unwrapped(IDEATE)
    span = text[text.index("Arriving with a list"):text.index("HARD GATE")]
    assert 200 <= len(span) <= 1200, (
        f"list paragraph is {len(span)} chars — moved or swallowed?"
    )
    return span


def test_the_list_becomes_one_plan_whose_phases_map_onto_goals():
    p = ideate_list_paragraph()
    assert "ONE plan" in p
    assert "map 1:1" in p
    assert "vertical slices" in p


def test_the_list_path_is_not_a_define_goal_batch_dump():
    p = ideate_list_paragraph()
    assert "define-goal's batch mode" in p
    assert "already shaped" in p


# ---- band 2: goals-status names the next command ------------------------------

def goals_status_next_section() -> str:
    """`## The `next:` line` section, up to the next heading (wrap-tolerant)."""
    text = read(GSTATUS)
    start = text.index("## The `next:` line")
    end = text.index("\n## ", start)
    return unwrap(text[start:end])


def test_goals_status_description_names_the_next_command():
    d = description_of(GSTATUS)
    assert "next:" in d
    assert "by queue state" in d


def test_goals_status_documents_exactly_one_first_match_next_line():
    s = goals_status_next_section()
    assert "exactly one `next: <command>` line" in s
    assert "first-match" in s


def test_open_goals_including_blocked_route_to_dispatch():
    s = goals_status_next_section()
    # `blocked` is named among the open statuses on the /dispatch branch
    assert "blocked" in s.split("/dispatch")[0]


def test_the_derivation_order_is_dispatch_then_process_inbox_then_ideate():
    s = goals_status_next_section()
    assert s.index("/dispatch") < s.index("/process-inbox") < s.index("/ideate")


def test_documented_commands_exist_in_the_deriving_code():
    code = read(GSTATUS_PY)
    section = goals_status_next_section()
    for cmd in ("/dispatch", "/process-inbox", "/ideate"):
        assert cmd in code, f"{cmd} not returned by goals_status.py"
        assert cmd in section, f"{cmd} not documented in goals-status SKILL.md"
