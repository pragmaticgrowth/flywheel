from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text()


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def test_define_goal_recon_subagents_inherit_session_model():
    recon_model_policy = section(
        read("skills/define-goal/SKILL.md"),
        "- **Model (mandatory)**:",
        "- **Angles, 2–4 per fan-out**",
    ).lower()

    assert "model: sonnet" not in recon_model_policy
    assert "never inherits the session model" not in recon_model_policy
    assert "sonnet earns its keep" not in recon_model_policy
    assert "inherit" in recon_model_policy
    assert "session model" in recon_model_policy


def test_active_docs_do_not_claim_recon_always_runs_on_sonnet():
    active_docs = [
        "CLAUDE.md",
        "README.md",
        "public/index.html",
        "skills/define-goal/SKILL.md",
        "skills/dispatch/SKILL.md",
    ]
    forbidden_phrases = [
        "recon always runs on sonnet",
        "sonnet-for-all-recon",
        "synthesis agent is also sonnet",
        "model: sonnet`, strictly read-only",
        "`model: sonnet` trades",
        "`config.model: sonnet` would",
        "finder agents on cheap models",
    ]

    for path in active_docs:
        text = read(path).lower()
        for phrase in forbidden_phrases:
            assert phrase not in text, path


def test_config_model_alias_examples_match_public_docs():
    define_goal = read("skills/define-goal/SKILL.md").lower()
    assert "sonnet, haiku, opus" not in define_goal
    assert "inherit | opus | sonnet | haiku" in define_goal
