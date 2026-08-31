"""Marketplace shape tests.

As of v8.0.0 `pragmatic-growth` ships exactly ONE plugin: flywheel. The
html-artifacts, autoresearch, and human-writing plugins were removed from the
marketplace (owner decision 2026-07-25); git history keeps them recoverable.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

REMOVED_PLUGINS = ("html-artifacts", "autoresearch", "human-writing")


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_flywheel_root_skill_inventory():
    skills = sorted(
        path.parent.name
        for path in (ROOT / "skills").glob("*/SKILL.md")
    )

    assert skills == [
        "define-goal",
        "dispatch",
        "factory-doctor",
        "factory-report",
        "goals-status",
        "ideate",
        "loop-architect",
        "process-inbox",
        "show-me",
    ]


def test_marketplace_ships_flywheel_only():
    marketplace = json.loads(read(".claude-plugin/marketplace.json"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}

    assert list(entries) == ["flywheel"]
    assert entries["flywheel"]["source"] == "./"


def test_removed_plugin_trees_are_gone():
    assert not (ROOT / "plugins").exists(), "plugins/ should be gone in v8.0.0"


def test_active_docs_do_not_advertise_removed_plugins():
    # History files (CHANGELOG, docs/superpowers/**) keep their references; the
    # active docs must not offer a plugin nobody can install.
    for path in ["README.md", "CLAUDE.md"]:
        text = read(path).lower()
        for name in REMOVED_PLUGINS:
            for i, line in enumerate(text.splitlines(), 1):
                if name in line:
                    assert "removed" in line or "v8.0.0" in line, (
                        f"{path}:{i}: stale reference to removed plugin '{name}'"
                    )


def test_public_docs_advertise_a_single_plugin_marketplace():
    marketplace = json.loads(read(".claude-plugin/marketplace.json"))
    assert len(marketplace["plugins"]) == 1
    for path in ["README.md", "CLAUDE.md"]:
        text = read(path).lower()
        assert "one plugin" in text, f"{path}: expected 'one plugin'"
