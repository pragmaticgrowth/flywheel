"""Self-healing-drain policy tests (v12.0.0 — the 2026-08-19 forensics release).

Placement guards for the rules that turn needs-you items into completions:
dispatch's Self-heal section (in-run amend + retire, blocked-backlog pass), the
two-channel needs-you/fyi split, the output envelope, the ship step, the
declarative-stall ban, define-goal's drain waiver + retire + Drainability/Premise
checks, process-inbox's OWNER bar, and the red-team's lockstep items.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_subjective_criteria_policy).
Meaning is verified by the subagent dry-runs recorded in the v12.0.0 release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
ESCALATION = "skills/dispatch/references/escalation-and-repair.md"
DEFINE = "skills/define-goal/SKILL.md"
INBOX = "skills/process-inbox/SKILL.md"
RED_TEAM = "agents/contract-red-team.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    return " ".join(read(path).split())


# ---- dispatch: self-heal ------------------------------------------------------

def test_dispatch_has_a_self_heal_section():
    text = read(DISPATCH)
    assert "## Self-heal" in text
    assert "drain waiver" in unwrapped(DISPATCH)


def test_self_heal_bounds_one_amend_per_goal_per_run():
    assert "ONE amend-and-re-claim per goal per RUN" in unwrapped(DISPATCH)


def test_self_heal_keeps_the_owner_fork_stop():
    text = unwrapped(DISPATCH)
    assert "true owner fork" in text
    assert "never resolved under the waiver" in text


def test_self_heal_walks_the_blocked_backlog():
    assert "blocked backlog heals too" in unwrapped(DISPATCH)


def test_retire_is_the_fifth_claim_verb():
    text = read(DISPATCH)
    assert "chore(goals): claim|complete|block|archive|retire <id>" in text
    assert "chore(goals): retire <id>" in text
    assert "status: retired" in unwrapped(DISPATCH)


def test_escalation_reference_routes_defects_through_self_heal():
    text = unwrapped(ESCALATION)
    assert "Self-heal owns the block" in text
    assert "retire" in text.lower()


def test_warm_resume_replay_detection():
    text = unwrapped(ESCALATION)
    assert "Replay detection" in text
    assert "disable warm resume" in text


# ---- dispatch: channels + envelope --------------------------------------------

def test_needs_you_and_fyi_are_two_channels():
    text = unwrapped(DISPATCH)
    assert "`needs-you:` is decisions, `fyi:` is observations" in text


def test_reason_half_is_capped():
    assert "~120 characters" in unwrapped(DISPATCH)


def test_output_envelope_binds_the_message_not_the_line():
    text = unwrapped(DISPATCH)
    assert "A per-goal settle turn is the report line and NOTHING else." in text
    assert "never a second closing message" in text


def test_the_fires_report_means_the_file():
    assert "always means that FILE, never the chat turn" in unwrapped(DISPATCH)


def test_closing_state_word():
    text = unwrapped(DISPATCH)
    assert "all complete" in text
    assert "outstanding: <n> for you" in text


# ---- dispatch: stalls, ship, dirt, chain, infra -------------------------------

def test_declarative_stalls_are_banned():
    text = unwrapped(DISPATCH)
    assert "Declarative stalls are the same miss" in text
    assert "a run never ends on an offer" in text


def test_ship_step_exists_and_keys_off_repo_docs():
    text = unwrapped(DISPATCH)
    assert "Ship step" in text
    assert "unshipped is not done" in text
    assert "standing authorization" in text


def test_dirty_tree_is_handled_not_refused():
    text = unwrapped(DISPATCH)
    assert "A dirty tree is handled, not a refusal" in text
    assert "chore(wip): foreign tree state at drain start" in text


def test_drained_flagless_run_chains_to_process_inbox():
    text = unwrapped(DISPATCH)
    assert "INVOKE it, flagless, once" in text
    assert "the chain never loops" in text


def test_infra_error_class_is_widened_and_settles_cleanly():
    text = unwrapped(DISPATCH)
    assert "insufficient balance" in text
    assert "auth_unavailable" in text
    assert "settle CLEANLY" in text


def test_droid_parallel_is_refused_and_polling_banned():
    text = unwrapped(DISPATCH)
    assert "parallel unavailable on this harness" in text
    assert "compliance miss on any harness" in text


def test_droid_spawns_are_awaited():
    assert "await: true" in unwrapped(DISPATCH)


# ---- define-goal --------------------------------------------------------------

def test_define_goal_reality_check_has_ten_checks():
    text = unwrapped(DEFINE)
    assert "ten checks" in text
    assert "Drainability" in text
    assert "Premise" in text


def test_define_goal_splits_irreversible_actions():
    text = unwrapped(DEFINE)
    assert "SPLIT, never gate" in text


def test_define_goal_amend_has_drain_waiver_and_retire():
    text = unwrapped(DEFINE)
    assert "Drain waiver" in text
    assert "Retire instead of amend when there is nothing to amend" in text
    assert "provenance: dispatch-self-heal" in text


def test_blanket_never_auto_amend_is_retired_but_interactive_confirms():
    text = unwrapped(DEFINE)
    assert "Never auto-amend" not in read(DEFINE)
    assert "Interactive amends keep the confirmation" in text


def test_inbox_intake_refuses_unconfirmed_premises():
    text = unwrapped(DEFINE)
    assert "premise unconfirmed" in text
    assert "verified live" in text


# ---- red-team lockstep --------------------------------------------------------

def test_red_team_carries_drainability_and_premise():
    text = unwrapped(RED_TEAM)
    assert "Drainability" in text
    assert "Premise" in text
    assert "blocks by construction" in text


def test_red_team_no_longer_endorses_criteria_path_gates():
    assert "ONLY for actions the criteria do not require" in unwrapped(RED_TEAM)


# ---- process-inbox ------------------------------------------------------------

def test_owner_bar_requires_a_proven_consequence():
    text = unwrapped(INBOX)
    assert "a proven consequence, not a matching topic" in text
    assert "blast radius" in text


def test_owner_lines_are_readjudicated_not_relisted():
    assert "RE-ADJUDICATED against the v12.0.0 OWNER bar" in unwrapped(INBOX)


def test_inbox_report_is_a_hard_envelope():
    text = unwrapped(INBOX)
    assert "That is the ENTIRE message" in text
    assert "EQUAL the number of OWNER lines" in text


def test_convert_verifies_named_mechanisms():
    assert "Mechanism check" in unwrapped(INBOX)
