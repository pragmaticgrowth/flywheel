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


def test_no_brace_glob_in_helper_resolution():
    # zsh aborts the WHOLE command on an unmatched glob (`no matches found`), and
    # `{cache,marketplaces}/*` is unmatched on any machine missing one of the two
    # directories — so every skill's helper-resolution must use the find-based
    # one-block form goals-status pioneered, never a brace-glob. (v8.3.1; the
    # brace form shipped broken in dispatch + factory-doctor until then.)
    for path in ACTIVE_DOCS:
        assert "{cache,marketplaces}" not in read(path), path
    for skill in ("dispatch", "factory-doctor", "goals-status"):
        text = read(f"skills/{skill}/SKILL.md")
        assert "find ~/.claude/plugins ~/.factory/plugins/cache -path" in text, skill


def test_limit_rail_is_window_timed_attended_drain():
    # Owner decision 2026-07-28: the factory runs in-subscription and in-session —
    # the limit-survival rail is a window-timed attended drain (/dispatch, a drain by
    # default since v10.0.0), never cron/launchd firing headless `claude -p` sessions.
    for path in ["skills/loop-architect/SKILL.md", "skills/factory-doctor/SKILL.md"]:
        assert "drains by default" in read(path), path
    la = read("skills/loop-architect/SKILL.md")
    assert "resets_at" in la  # the reset clock is named (doctor names it in its script's fix text)
    assert "rail is retired" in la  # the retirement of the headless rail is stated
    assert 'firing a fresh headless session per cadence' not in la
    # dispatch's batch section points the same way
    assert "window-timed drains" in read("skills/dispatch/SKILL.md")
