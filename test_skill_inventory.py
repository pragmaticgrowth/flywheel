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


def test_public_docs_advertise_two_plugins_and_html_artifacts():
    for path in ["README.md", "CLAUDE.md", "public/index.html"]:
        text = read(path)
        assert "two plugin" in text.lower(), path
        assert "html-artifacts" in text, path
