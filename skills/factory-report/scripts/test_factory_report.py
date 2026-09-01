"""factory_report — the `stalled` signal (v14.3.0).

A stalled run is a session that claimed goals, whose whole session has been silent
STALL_MIN+ minutes, and whose claims no later terminal flip (any session, same repo)
has settled. Field case 2026-09-01 (nonresidenttax): the orchestrator lost a re-gate's
completion notification, probed liveness with a self-matching `pgrep -f`, ended its
turn believing the gate still ran, and sat 70+ minutes with two goals claimed.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import factory_report as fr  # noqa: E402

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 9, 1, 16, 0, tzinfo=UTC)


def ev(minutes, sid, **kw):
    r = dict(ts=(T0 + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             sid=sid, cwd="/root/repo-a", ev="PostToolUse", tool="Bash")
    r.update(kw)
    r["_t"] = T0 + dt.timedelta(minutes=minutes)
    return r


def test_open_claim_and_long_silence_is_stalled():
    rows = [ev(0, "S", gv="claim", gid="209"), ev(3, "S", ev="Stop")]
    out = fr.stalled_runs(rows, T0 + dt.timedelta(minutes=60))
    assert len(out) == 1
    assert out[0]["open"] == ["209"] and out[0]["repo"] == "repo-a"
    assert out[0]["silent"] >= 57


def test_settled_claim_is_not_stalled():
    rows = [ev(0, "S", gv="claim", gid="209"), ev(20, "S", gv="complete", gid="209"), ev(21, "S", ev="Stop")]
    assert fr.stalled_runs(rows, T0 + dt.timedelta(minutes=120)) == []


def test_claim_settled_by_a_later_session_is_not_stalled():
    # the next /dispatch's Phase 1 settled the orphan — that closes it here too
    rows = [ev(0, "S1", gv="claim", gid="209"), ev(2, "S1", ev="Stop"),
            ev(50, "S2", gv="block", gid="209")]
    assert fr.stalled_runs(rows, T0 + dt.timedelta(minutes=120)) == []


def test_recent_activity_anywhere_in_the_session_is_not_stalled():
    # a subagent still working carries the same sid — the RUN is alive
    rows = [ev(0, "S", gv="claim", gid="209"), ev(40, "S", aid="a1", tool="Read")]
    assert fr.stalled_runs(rows, T0 + dt.timedelta(minutes=45)) == []


def test_silence_below_threshold_is_not_stalled():
    rows = [ev(0, "S", gv="claim", gid="209"), ev(3, "S", ev="Stop")]
    assert fr.stalled_runs(rows, T0 + dt.timedelta(minutes=3 + fr.STALL_MIN - 1)) == []


def test_reclaim_after_block_only_counts_the_newest_claim():
    # blocked in S1, amended, re-claimed in S2 and left open there
    rows = [ev(0, "S1", gv="claim", gid="209"), ev(10, "S1", gv="block", gid="209"),
            ev(30, "S2", gv="claim", gid="209"), ev(31, "S2", ev="Stop")]
    out = fr.stalled_runs(rows, T0 + dt.timedelta(minutes=90))
    assert [x["sid"] for x in out] == ["S2"]


def test_lane_cwd_rolls_up_to_the_repo():
    rows = [ev(0, "S", gv="claim", gid="209"), ev(3, "S", ev="Stop")]
    rows[0]["cwd"] = "/root/.local/state/pg-dispatch/repo-a/lanes/209"
    out = fr.stalled_runs(rows, T0 + dt.timedelta(minutes=60))
    assert out and out[0]["repo"] == "repo-a"
