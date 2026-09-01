"""Subagent-policy tests — the plugin's review roles must be spawnable on BOTH harnesses.

Two platform facts drive these tests:

1. Droid subagents CANNOT spawn subagents (docs.factory.ai custom-droids). Since
   v14.0.0 the review panel lives on the GATE side (the orchestrator is a main session
   on both harnesses), so the implementer needs no spawn capability for review at all —
   the brief must acknowledge the Droid limit for its optional recon helpers and must
   never route around it with self-review.
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


def test_dispatch_documents_the_droid_subagent_limit():
    """Droid subagents have no Task tool; since v14.0.0 the brief acknowledges the
    limit for its optional recon helpers instead of shipping a lens workaround."""
    text = dispatch_full_text()
    assert "On Droid you have no Task tool" in text, (
        "the implementer brief must state Droid's nested-spawn limit"
    )
    assert "droid exec" not in " ".join(
        (ROOT / "skills" / "dispatch" / "references" / "implementer-brief.md")
        .read_text()
        .split()
    ), "the removed Droid lens mechanism must not leak back into the brief"


def test_dispatch_forbids_self_review_by_the_implementer():
    """Self-review is the maker grading its own work — v14.0.0 bans it outright:
    the gate's independent review is the second view, sized by the diff."""
    text = dispatch_full_text()
    assert "Do NOT review your own finished diff in a subagent" in text
    assert "a self-arranged review would only duplicate it" in text


def test_gate_review_is_sized_by_the_diff_never_by_implementer_claims():
    """The old escalation keyed on the implementer's self-report; v14.0.0 keys it
    on the diff alone."""
    text = " ".join(DISPATCH.read_text().split())
    assert "sized by the DIFF" in text
    assert "never from the implementer's claims about its own work" in text
