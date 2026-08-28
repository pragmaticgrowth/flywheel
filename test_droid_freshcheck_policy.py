"""Policy tests for Droid fresh-check command safety and fallback honesty."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BRIEF = ROOT / "skills" / "dispatch" / "references" / "implementer-brief.md"
HARNESS_START = "**Harness note — nested spawning.**"
HARNESS_END = "\n\nWorkspace:"
TOOLS_FLAG = '--enabled-tools "Read,Grep,Glob,LS,Execute"'
EXPECTED_LENS_COMMANDS = [
    f"droid exec -f <prompt-file> {TOOLS_FLAG}",
    f'droid exec "<prompt>" {TOOLS_FLAG}',
]
VERDICT = "Fresh-check: not run (no fresh-context mechanism available)"
VERDICT_BODY = "not run (no fresh-context mechanism available)"


def harness_note() -> str:
    text = BRIEF.read_text()
    return text.split(HARNESS_START, 1)[1].split(HARNESS_END, 1)[0]


def sanctioned_droid_lens_commands() -> list[str]:
    """Enumerate every code span that sanctions a Droid exec lens command."""
    code_spans = re.findall(r"`([^`\n]+)`", harness_note())
    return [span for span in code_spans if re.search(r"\bdroid exec(?:\s|$)", span)]


def test_harness_sanctions_exactly_two_tool_enabled_droid_lens_commands():
    commands = sanctioned_droid_lens_commands()

    assert commands == EXPECTED_LENS_COMMANDS
    assert all(command.endswith(TOOLS_FLAG) for command in commands)


def test_no_fresh_context_verdict_requires_failed_droid_path_probe():
    """The fallback verdict is legal only via a failed `command -v droid` probe.

    A presence-only check is not enough: any second, unconditional
    authorization of the verdict (a legacy "If neither path is available, say
    ..." sentence, or any reworded duplicate) must fail this test.
    """
    normalized = " ".join(harness_note().split())
    required_rule = (
        "Only when `command -v droid` fails may you say "
        f"`{VERDICT}`"
    )

    assert required_rule in normalized
    # required_rule embeds the verdict string, so with this count the single
    # occurrence is provably the one inside the Only-when clause — any second
    # occurrence anywhere in the note is rejected.
    assert normalized.count(VERDICT) == 1
    # The legacy wording split the verdict across two code spans
    # ("`Fresh-check:` line — `not run (no fresh-context mechanism
    # available)`"), invisible to a full-string count; the body count rejects
    # that form and any other verdict-granting sentence alongside the rule.
    assert normalized.count(VERDICT_BODY) == 1
