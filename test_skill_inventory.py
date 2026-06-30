from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_skill_inventory_includes_html_artifacts():
    skills = sorted(
        path.parent.name
        for path in (ROOT / "skills").glob("*/SKILL.md")
    )

    assert skills == [
        "define-goal",
        "dispatch",
        "factory-doctor",
        "html-artifacts",
        "loop-architect",
    ]


def test_html_artifacts_stays_skills_only():
    skill_root = ROOT / "skills" / "html-artifacts"
    files = [path.relative_to(skill_root).as_posix() for path in skill_root.rglob("*") if path.is_file()]

    assert "SKILL.md" in files
    assert any(path.startswith("references/") for path in files)
    assert not any(path.startswith("scripts/") for path in files)
    assert not any("server" in path or "listen" in path for path in files)


def test_public_docs_advertise_five_skills_and_html_artifacts():
    for path in ["README.md", "CLAUDE.md", "public/index.html"]:
        text = read(path)
        assert "five skills" in text.lower(), path
        assert "html-artifacts" in text, path
