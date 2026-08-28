"""Double-death routing policy tests (goal 015).

The resume-from-increments respawn (goal 009) that itself died STATUS-less
fell through the ladder: rung 4 closed "Once per goal per session, like every
rung" and the preamble held the same law, so a SECOND consecutive STATUS-less
death had no legal re-fire and rung 5's catch-all ("Anything else → roll back
any work commits and block") swallowed it — destroying exactly the increments
the rung exists to protect; 014's child-timeout clause ("not a second free
respawn — it re-enters these stale-claim rules") was class-scoped and
collided with the spent-rung reading instead of licensing the re-fire
(verified CONFIRMED 2026-08-28 at HEAD, provenance inbox-drain). After this
goal: a second consecutive STATUS-less death re-fires the resume rung while
the transient-death budget has headroom (the re-brief is changed by the larger
`Landed so far` set), rung 5 never receives a STATUS-less death with budget
remaining, and only a spent budget blocks `repeated transient death` with the
rollback firing there. The rule is death-mode generic — 014's child-session
timeout clause is one named instance, its pinned phrases intact.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
ESCALATION = "skills/dispatch/references/escalation-and-repair.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped_text(text: str) -> str:
    return " ".join(text.split())


def ladder() -> str:
    """The escalation ladder section (to end of file)."""
    text = read(ESCALATION)
    span = text[text.index("## Escalation ladder"):]
    assert 15 <= span.count("\n") <= 70, (
        f"ladder span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


def ladder_preamble() -> str:
    """The once-per-rung law paragraph, from the ladder heading to rung 1."""
    text = read(ESCALATION)
    start = text.index("## Escalation ladder")
    end = text.index("1. **`NEEDS_CONTEXT`**", start)
    return unwrapped_text(text[start:end])


def rung4() -> str:
    """The resume-from-increments rung, up to rung 5."""
    text = read(ESCALATION)
    start = text.index("4. **No `STATUS:` block")
    end = text.index("5. **Anything else**", start)
    return unwrapped_text(text[start:end])


def rung5() -> str:
    """Rung 5 (the catch-all) to end of file."""
    text = read(ESCALATION)
    return unwrapped_text(text[text.index("5. **Anything else**"):])

def phase1_work_commits_step() -> str:
    """Phase 1 bullet 1 (work commits present) up to bullet 2 (no work commits)."""
    text = read(DISPATCH)
    start = text.index("1. **Work commits present")
    end = text.index("2. **No work commits", start)
    span = text[start:end]
    assert 5 <= span.count("\n") <= 40, (
        f"work-commits step span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


def stale_claim_step() -> str:
    """Re-entrancy rule 2 (stale claim / transient deaths) up to rule 3."""
    text = read(DISPATCH)
    start = text.index("2. **Stale claim**")
    end = text.index("3. **Finish before claiming**", start)
    span = text[start:end]
    assert 30 <= span.count("\n") <= 120, (
        f"stale-claim step span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


# ---- the once-per-rung law gains the transient carve-out ----------------------

def test_preamble_once_law_gains_the_transient_statusless_carve_out():
    span = ladder_preamble()
    assert "at most ONCE per goal per session" in span  # the law itself survives
    assert "carve-out" in span
    assert (
        "transient STATUS-less death re-fires the resume rung while the "
        "transient-death budget has headroom" in span
    )


# ---- rung 4: a second consecutive STATUS-less death re-fires the rung ---------

def test_second_consecutive_statusless_death_refires_the_resume_rung():
    span = rung4()
    assert "SECOND consecutive STATUS-less death re-fires this rung" in span
    assert "while the ~3-transient-respawn budget has headroom" in span


def test_the_rebrief_is_changed_by_the_larger_landed_so_far_set():
    span = rung4()
    assert "changed by the larger `Landed so far` set" in span


def test_the_rule_is_death_mode_generic_with_014_as_a_named_instance():
    span = rung4()
    assert "death-mode generic" in span
    assert "child-session timeout" in span
    assert "named instance" in span


# ---- rung 5: the guard ---------------------------------------------------------

def test_rung5_never_takes_a_statusless_death_while_budget_remains():
    span = rung5()
    assert (
        "never routes here while the transient-death budget has headroom" in span
    )
    assert "rung 4 re-fires" in span


def test_spent_budget_blocks_repeated_transient_death_and_rolls_back_there():
    span = rung5()
    assert "budget is spent" in span
    assert "blocks here as `repeated transient death`" in span
    assert "rollback fires at this rung" in span


# ---- SKILL.md Phase 1 bullet 1 names the repeat branch ------------------------

def test_phase1_bullet1_names_the_second_death_repeat_branch():
    span = phase1_work_commits_step()
    assert (
        "A second consecutive STATUS-less death re-fires the "
        "resume-from-increments rung while the transient-death budget has "
        "headroom" in span
    )
    assert "only a spent budget blocks `repeated transient death`" in span
    assert "rung 5's guard" in span


# ---- 014's clause survives verbatim, generalized alongside — never substituted

def test_child_timeout_pinned_phrases_survive_alongside_the_general_rule():
    span = stale_claim_step()
    # 014's sentence survives, pinned phrases verbatim
    assert "not a second free respawn" in span
    assert "re-enters these stale-claim rules" in span
    # the general clause added ALONGSIDE it, never substituted
    assert "death-mode generic" in span
    assert "ANY second STATUS-less transient death" in span


def test_stale_claim_general_rule_routes_resume_then_block():
    span = stale_claim_step()
    assert (
        "the resume-from-increments rung while the transient-respawn budget "
        "has headroom" in span
    )
    assert "`blocked: repeated transient death` only once it is spent" in span
