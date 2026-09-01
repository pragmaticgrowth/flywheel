"""Spawning-and-waiting policy tests (v12.6.0 — the 2026-08-31 wait forensics).

Placement guards for the rules that keep a spawned helper's report reachable:
the plain-spawn / no-`name:` ban, the yield-the-turn wait discipline, the
both-harness poll ban, and the transcript-backed death test — at every site that
spawns (dispatch and its references, process-inbox, define-goal, ideate).

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_subjective_criteria_policy).
Meaning is verified by the subagent dry-runs recorded in the v12.6.0 release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
BRIEF = "skills/dispatch/references/implementer-brief.md"
PARALLEL = "skills/dispatch/references/parallel-mode.md"
ESCALATION = "skills/dispatch/references/escalation-and-repair.md"
INBOX = "skills/process-inbox/SKILL.md"
DEFINE = "skills/define-goal/SKILL.md"
IDEATE = "skills/ideate/SKILL.md"

SPAWN_SITES = [DISPATCH, BRIEF, PARALLEL, INBOX, DEFINE, IDEATE]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    return " ".join(read(path).split())


# ---- the rule is a dispatch hard rule, not a footnote --------------------------

def test_dispatch_hard_rules_carry_the_spawning_and_waiting_rule():
    text = unwrapped(DISPATCH)
    assert "Spawning and waiting — yield the turn, never build a wait" in text
    assert "the report arrives later as a completion notification" in text
    assert "Building a wait is the miss" in text


def test_the_three_self_defeating_waits_are_named():
    text = unwrapped(DISPATCH)
    for shape in ("`Monitor` sleep loop", "blocking `TaskOutput`", "repeated `ListAgents`"):
        assert shape in text
    assert "hold the turn OPEN" in text


def test_hard_rules_say_when_you_may_stop_waiting():
    # the death test must be reachable from the section that governs waiting —
    # leaving it only in Re-entrancy read as an implementer-only rule (dry-run
    # finding, 2026-08-31)
    text = unwrapped(DISPATCH)
    assert "When may you stop waiting?" in text
    assert "governs EVERY spawn this skill makes" in text
    assert "Six silent minutes is not that test" in text


# ---- no `name:` on any factory spawn ------------------------------------------

def test_name_is_banned_at_every_spawn_site():
    for path in SPAWN_SITES:
        assert "`name:`" in unwrapped(path), path


def test_the_named_agent_failure_mode_is_stated():
    text = unwrapped(DISPATCH)
    assert "persistent session teammate" in text
    assert "mailbox instead of the notification channel" in text


def test_subagent_spawns_return_inline_so_a_named_helper_is_lost():
    # v14.0.0: the brief's spawns are recon helpers (the lens panel moved to the
    # gate); the inline-return-vs-mailbox rule is unchanged.
    text = unwrapped(BRIEF)
    assert "spawn them PLAIN" in text
    assert "returns its report INLINE as its tool result" in text
    assert "a channel you, as a subagent, never read" in text


def test_warm_resume_uses_the_agent_id_not_a_name():
    # Phase 3 once mandated naming the implementer FOR warm resume — the exact
    # contradiction this release resolves; both files must agree.
    dispatch = unwrapped(DISPATCH)
    assert "Pass NO `name:`" in dispatch
    assert "the repair round resumes it by that id" in dispatch
    escalation = unwrapped(ESCALATION)
    assert "addressed by the agent id its spawn returned" in escalation
    assert "message the named implementer agent you spawned" not in escalation


# ---- death needs the transcript ------------------------------------------------

def test_death_needs_the_transcript_with_both_harness_paths():
    text = unwrapped(DISPATCH)
    assert "A silent helper is not a dead one — read its transcript" in text
    assert "subagents/agent-*.jsonl" in text
    assert "childSessionId" in text
    assert "mean a LIVE agent — keep waiting" in text


def test_killing_a_live_helper_is_named_a_double_miss():
    text = unwrapped(DISPATCH)
    assert "compliance miss twice over" in text
    assert "destroys the independence the spawn exists to buy" in text


def test_the_two_samples_rule_survives_verbatim():
    # v11.6.0's bar is the negative half of the test; the transcript rule adds to
    # it and must never replace it
    text = unwrapped(DISPATCH)
    assert "check twice with real minutes between" in text
    assert "ZERO new commits or file activity between the checks" in text


# ---- process-inbox: both halves of the test, and an exit ----------------------

def test_inbox_states_what_licenses_giving_up_on_a_verifier():
    text = unwrapped(INBOX)
    assert "TWO checks with real minutes between them" in text
    assert "zero new transcript records" in text


def test_inbox_has_a_retry_once_fallback_scoped_to_verification():
    text = unwrapped(INBOX)
    assert "retry once, never wait a second round" in text.lower()
    assert "verified inline (verifier not delivered)" in text
    assert "buys context economy and parallelism, not independence" in text
    # and the fallback must be explicitly denied to the roles that buy independence
    assert "NOT available for dispatch's gate review or red-team" in text


# ---- the poll ban is both-harness ---------------------------------------------

def test_arm_a_join_ban_is_not_droid_only():
    text = unwrapped(DISPATCH)
    assert "task-status poll loop on EITHER harness" in text
    assert "on Droid, never a repeated sleep+`ps`" not in text


def test_parallel_mode_ties_the_ban_to_delivery():
    text = unwrapped(PARALLEL)
    assert "a held-open turn is exactly what stops a finished lane's report" in text
    assert "K spawns in one message, ONE wait, K results, zero polls" in text


def test_droid_awaited_task_contract_is_untouched():
    assert "await: true" in unwrapped(DISPATCH)
    assert "await: true" in unwrapped(PARALLEL)
