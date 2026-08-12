"""Subagent-policy tests — the plugin's review roles must be spawnable on BOTH harnesses.

Two platform facts drive these tests:

1. Droid subagents CANNOT spawn subagents ("a subagent cannot spawn its own subagents
   (the Task tool is not available to it)" — docs.factory.ai custom-droids). Claude Code
   subagents CAN (Agent nests, cap depth=5). Dispatch's implementer panel therefore needs
   an explicit per-harness path, and the fallback must never be self-review.
2. Tool IDs differ per harness. Claude Code uses `Bash`; Droid uses `Execute` and validates
   `tools:` entries against a fixed table, where an unknown ID is a validation error.
   Each harness silently ignores the other's shell tool, so naming both is safe — naming
   an ID neither harness knows is not.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS = sorted((ROOT / "agents").glob("*.md"))
DISPATCH = ROOT / "skills" / "dispatch" / "SKILL.md"
DISPATCH_REFS = sorted((ROOT / "skills" / "dispatch" / "references").glob("*.md"))


def dispatch_full_text() -> str:
    """SKILL.md plus its references/ files — v10.0.0 moved the implementer brief,
    parallel mode, and escalation/repair into reference files Read on demand; the
    doctrine must exist in the combined text the orchestrator/implementer receives."""
    return " ".join(
        " ".join(f.read_text().split()) for f in [DISPATCH, *DISPATCH_REFS]
    )

# Valid on at least one harness. Droid: Read/LS/Grep/Glob/Create/Edit/ApplyPatch/Execute/
# WebSearch/FetchUrl. Claude Code: Bash + the read tools. Anything outside this set risks
# invalidating the whole definition on Droid.
PORTABLE_TOOL_IDS = {
    "Bash", "Execute", "Read", "Grep", "Glob", "LS",
    "WebSearch", "FetchUrl",
}

# Write-capable IDs on either harness — a review role must never carry one.
WRITE_TOOL_IDS = {"Edit", "Create", "Write", "ApplyPatch", "Agent", "Task", "NotebookEdit"}


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path.name}: no YAML frontmatter"
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def tool_list(path: Path) -> list:
    raw = frontmatter(path).get("tools", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def test_agents_exist():
    # v5.4.0: the three review roles; v11.1.0: the three recon roles (riptide-adapted).
    assert len(AGENTS) == 6, [p.name for p in AGENTS]


def test_every_agent_tool_id_is_valid_on_some_harness():
    """An ID neither harness knows can invalidate the definition on Droid, silently
    dropping the plugin agent to the generic fallback."""
    for path in AGENTS:
        for tool in tool_list(path):
            assert tool in PORTABLE_TOOL_IDS, (
                f"{path.name}: tool ID {tool!r} is not valid on Claude Code or Droid; "
                f"valid: {sorted(PORTABLE_TOOL_IDS)}"
            )


def test_every_agent_names_both_harness_shell_tools():
    """Each harness ignores the other's shell tool, so both must be present or the agent
    loses command access on one harness."""
    for path in AGENTS:
        tools = tool_list(path)
        assert "Bash" in tools, f"{path.name}: missing Bash (Claude Code shell tool)"
        assert "Execute" in tools, f"{path.name}: missing Execute (Droid shell tool)"


def test_review_agents_carry_no_write_capable_tool():
    """Read-only is enforced by the runtime via the allowlist, not by prompt discipline."""
    for path in AGENTS:
        for tool in tool_list(path):
            assert tool not in WRITE_TOOL_IDS, f"{path.name}: write-capable tool {tool!r}"


def test_agents_pin_no_model():
    """Review agents inherit the session model; a pin would override the orchestrator."""
    for path in AGENTS:
        assert "model" not in frontmatter(path), f"{path.name}: must not pin a model"


def test_agents_do_not_depend_on_a_message_tool_for_delivery():
    """The return channel is the subagent's final message on both harnesses."""
    for path in AGENTS:
        assert "SendMessage" not in path.read_text(), (
            f"{path.name}: SendMessage is not a valid tool ID on Droid and is not needed — "
            "the parent reads the final message"
        )


def test_dispatch_documents_the_droid_nesting_limit():
    """Droid subagents have no Task tool, so the implementer panel needs a real
    per-harness path rather than an impossible mandate."""
    text = dispatch_full_text()
    assert "cannot spawn its own subagents" in text, (
        "dispatch must state Droid's nested-spawn limit"
    )
    assert "droid exec" in text, "dispatch must name the sanctioned Droid fresh-context path"


def test_dispatch_forbids_self_review_as_the_panel_fallback():
    """Self-review is the maker grading its own work — the exact failure the panel prevents."""
    text = dispatch_full_text()
    assert "not run (no fresh-context mechanism available)" in text, (
        "dispatch must give implementers an honest 'not run' verdict instead of self-review"
    )
    assert "self-review is the maker" in text.lower(), (
        "dispatch must name self-review as the failure mode the fallback avoids"
    )


def test_honest_not_run_is_not_treated_as_a_compliance_miss():
    """A truthful 'not run' escalates the orchestrator's review; it is not a violation."""
    text = " ".join(DISPATCH.read_text().split())
    assert "is NOT a compliance miss" in text, (
        "dispatch must distinguish an honest 'not run' from a silently skipped panel"
    )
