import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_flywheel_root_skill_inventory_excludes_html_artifacts_plugin():
    skills = sorted(
        path.parent.name
        for path in (ROOT / "skills").glob("*/SKILL.md")
    )

    assert skills == [
        "define-goal",
        "dispatch",
        "factory-doctor",
        "goals-status",
        "loop-architect",
    ]


def test_marketplace_lists_html_artifacts_as_separate_plugin():
    marketplace = json.loads(read(".claude-plugin/marketplace.json"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}

    assert entries["flywheel"]["source"] == "./"
    assert entries["html-artifacts"]["source"] == "./plugins/html-artifacts"

    html_plugin = json.loads(read("plugins/html-artifacts/.claude-plugin/plugin.json"))
    assert html_plugin["name"] == "html-artifacts"


def test_html_artifacts_plugin_stays_skills_only():
    skill_root = ROOT / "plugins" / "html-artifacts" / "skills" / "html-artifacts"
    files = [path.relative_to(skill_root).as_posix() for path in skill_root.rglob("*") if path.is_file()]

    assert "SKILL.md" in files
    assert any(path.startswith("references/") for path in files)
    assert not any(path.startswith("scripts/") for path in files)
    assert not any("server" in path or "listen" in path for path in files)


_COUNT_WORD = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def test_public_docs_advertise_current_plugin_count_and_html_artifacts():
    # Derive the expected count from the marketplace manifest so this self-updates when a
    # plugin is added — and catches the NEXT addition if the docs' prose word isn't bumped.
    marketplace = json.loads(read(".claude-plugin/marketplace.json"))
    n = len(marketplace["plugins"])
    word = _COUNT_WORD[n]
    for path in ["README.md", "CLAUDE.md", "public/index.html"]:
        text = read(path).lower()
        assert f"{word} plugin" in text, f"{path}: expected '{word} plugin' (marketplace lists {n})"
        assert "html-artifacts" in read(path), path
