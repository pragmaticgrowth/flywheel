"""Tier-vocabulary policy tests (v7.0.0 dual-target port).

heavy|medium|light is the native execution-tier vocabulary; the Anthropic model
names opus/sonnet/haiku may appear in active docs ONLY as read-time aliases or
inside a harness-mapping context (a line that also names the tier, says
"alias"/"maps", or is scoped to Claude Code).
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text()


ACTIVE_DOCS = [
    "CLAUDE.md",
    "README.md",
    "public/index.html",
    "skills/define-goal/SKILL.md",
    "skills/dispatch/SKILL.md",
    "skills/ideate/SKILL.md",
    "skills/goals-status/SKILL.md",
    "skills/loop-architect/SKILL.md",
    "skills/factory-doctor/SKILL.md",
]


def test_define_goal_stamps_tiers_not_model_names():
    text = read("skills/define-goal/SKILL.md").lower()
    assert "inherit | heavy | medium | light" in text
    assert "inherit | opus | sonnet | haiku" not in text


def test_active_docs_use_tier_vocabulary():
    for path in ACTIVE_DOCS:
        text = read(path).lower()
        for name, tier in (("opus", "heavy"), ("sonnet", "medium"), ("haiku", "light")):
            for i, line in enumerate(text.splitlines(), 1):
                if name in line:
                    assert (
                        tier in line or "alias" in line or "maps" in line
                        or "claude code" in line
                    ), f"{path}:{i}: bare model name '{name}' outside alias/mapping context"


def test_dispatch_carries_the_canonical_alias_table():
    text = read("skills/dispatch/SKILL.md").lower()
    assert "opus` → heavy" in text or "opus → heavy" in text
    assert "sonnet` → medium" in text or "sonnet → medium" in text
    assert "haiku` → light" in text or "haiku → light" in text


def test_scheduling_rail_names_both_harnesses():
    for path in ["skills/loop-architect/SKILL.md", "skills/factory-doctor/SKILL.md"]:
        text = read(path)
        assert 'claude -p "/dispatch"' in text, path
        assert 'droid exec "/dispatch"' in text, path
