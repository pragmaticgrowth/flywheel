"""Plural-publish-path Ship step placement tests (goal 005-plural-publish-paths).

When the target repo's docs declare more than one publish path, Ship must run
every declared path the diff touched and report per-service. One shipped and
one not is `ship FAILED: partial`. Dispatch still never invents a deploy.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DISPATCH = "skills/dispatch/SKILL.md"
CLAUDE = "CLAUDE.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrap(text: str) -> str:
    return " ".join(text.split())


def unwrapped(path: str) -> str:
    return unwrap(read(path))


def ship_step_text() -> str:
    """The **Ship step** paragraph in dispatch, up to the next ** heading."""
    lines = read(DISPATCH).splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("**Ship step")]
    assert len(starts) == 1, (
        f"{DISPATCH}: expected 1 **Ship step heading, found {len(starts)}"
    )
    start = starts[0]
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("**")
        ),
        len(lines),
    )
    span = lines[start:end]
    assert 3 <= len(span) <= 40, f"Ship step span is {len(span)} lines"
    return unwrap("\n".join(span))


def claude_ship_restatement() -> str:
    """The SHIP STEP clause in CLAUDE.md's dispatch restatement."""
    text = unwrapped(CLAUDE)
    start = text.index("SHIP STEP")
    end = text.index("Dirty trees", start)
    return text[start:end]


def test_ship_step_runs_every_declared_path_the_diff_touched_when_docs_declare_more_than_one():
    text = ship_step_text()
    assert "more than one publish path" in text
    assert "every declared path the diff touched" in text
    assert "report per-service" in text


def test_diff_touched_means_gate_base_range_or_this_run_and_falls_back_to_every_path():
    text = ship_step_text()
    assert "gate_base..HEAD" in text
    assert "commits this run produced" in text
    assert "if the docs do not map paths to services, run every declared path" in text


def test_ship_failed_partial_is_a_legal_outcome():
    text = ship_step_text()
    assert "`ship FAILED: partial (<service> unshipped)`" in text


def test_environment_failure_names_the_partial():
    text = ship_step_text()
    assert "`ship FAILED: partial (<service> unshipped)`" in text
    assert "class `environment failure`" in text
    # The partial outcome is named as the same class, not a new channel.
    partial_at = text.index("`ship FAILED: partial (<service> unshipped)`")
    window = text[partial_at : partial_at + 180]
    assert "environment failure" in window, (
        "needs-you class `environment failure` does not name the partial"
    )


def test_never_invents_a_deploy_remains():
    assert "never invents a deploy" in ship_step_text()


def test_claude_md_restatement_matches_the_plural_ship_rule():
    text = claude_ship_restatement()
    assert "every declared path the diff touched" in text
    assert "docs declare more than one" in text
    assert "`ship FAILED: partial (<service> unshipped)`" in text
    assert "class `environment failure`" in text
    assert "never invents a deploy" in text
