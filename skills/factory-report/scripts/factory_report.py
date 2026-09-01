#!/usr/bin/env python3
"""Factory performance report — goal timing, agent cost, and the three failure modes.

Reads three sources and prefers the most trustworthy one for each number:

  1. git `chore(goals):` commits   — authoritative goal timing. Works retroactively,
                                     and cannot be fabricated by an agent.
  2. the hook event log            — agent lifecycles, tool-call counts, session cost.
                                     Absent before the log was enabled; that is normal.
  3. index.yaml / archive.yaml     — status, current queue depth, stamped durations
                                     (cross-checked against git, never trusted over it).

Exit codes: 0 ok, 2 nothing to report.
"""
import argparse, collections, datetime as dt, glob, json, os, re, statistics as st, subprocess, sys

UTC = dt.timezone.utc
FLIP = re.compile(r"chore\(goals\): (claim|complete|block|retire|amend) (\S+)")
DEFAULT_LOG = os.path.expanduser("~/.local/state/pg-factory/events.ndjson")

# Failure-mode thresholds. Deliberately reporting-only — nothing here stops an agent.
RUNAWAY_TOOLS = 300      # p90 of a healthy worker is ~105; 300 is 3x headroom
HUNG_GAP_MIN = 15.0      # a working agent's largest normal gap is ~1 min
LONG_GOAL_MIN = 90.0


def sh(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def find_repos(roots):
    seen, out = set(), []
    for root in roots:
        for pat in ("*/docs/goals/index.yaml", "*/*/docs/goals/index.yaml"):
            for p in glob.glob(os.path.join(os.path.expanduser(root), pat)):
                repo = os.path.dirname(os.path.dirname(os.path.dirname(p)))
                if repo not in seen and os.path.isdir(os.path.join(repo, ".git")):
                    seen.add(repo)
                    out.append(repo)
    return sorted(out)


def inbox_open_count(repo):
    """Unchecked `- [ ]` lines in <repo>/docs/goals/inbox.md — the same pile-up
    goals-status and factory-doctor surface per-repo, rolled up machine-wide here.
    0 when the file is absent, empty, or unreadable."""
    path = os.path.join(repo, "docs", "goals", "inbox.md")
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return 0
    return sum(1 for ln in text.splitlines() if ln.strip().startswith("- [ ]"))


def goal_events(repo, since):
    """Every queue flip in this repo, from git. The honest clock."""
    out = sh(["git", "-C", repo, "log", "--format=%aI\t%s", f"--since={since}",
              "--", "docs/goals/index.yaml"])
    evs = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        ts, subj = line.split("\t", 1)
        m = FLIP.match(subj.strip())
        if not m:
            continue
        try:
            evs.append((dt.datetime.fromisoformat(ts).astimezone(UTC), m.group(1), m.group(2)))
        except ValueError:
            continue
    return sorted(evs)


def settled(evs):
    """Pair each terminal flip with the latest claim before it."""
    out = []
    for t, verb, gid in evs:
        if verb in ("claim", "amend"):
            continue
        claims = [a for a, v, g in evs if g == gid and v == "claim" and a < t]
        if claims:
            out.append((gid, max(claims), t, verb, (t - max(claims)).total_seconds() / 60))
    return out


# Idle-inflation: wall-clock claim->settle time includes idle gaps (a dead session, an
# account usage-limit pause) that have nothing to do with the goal's own size — measured
# ~90% of 4h+ cycles are idle-inflated. Only worth a `git log` for the genuinely slow
# ones (IDLE_GAP_CHECK_MIN), and only relabeled when the largest gap explains most of
# the wall clock (IDLE_GAP_WARN_MIN).
IDLE_GAP_CHECK_MIN = 240.0
IDLE_GAP_WARN_MIN = 180.0


def idle_gap_minutes(repo, claimed, settled_at):
    """Largest gap (minutes) in commit activity across a goal's claim->settle window,
    including the lead-in (claim -> first commit) and lead-out (last commit -> settle).
    Read-only `git log`; called only for the handful of slow cycles above
    IDLE_GAP_CHECK_MIN, so a full-history scan per goal stays cheap in practice.
    0.0 when git has nothing to say (no commits in range, or the command fails) —
    never raises.
    """
    out = sh(["git", "-C", repo, "log", "--all", "--pretty=%ad", "--date=iso-strict",
              f"--since={claimed.isoformat()}", f"--until={settled_at.isoformat()}"])
    times = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            times.append(dt.datetime.fromisoformat(line).astimezone(UTC))
        except ValueError:
            continue
    if not times:
        return 0.0
    times.sort()
    bounds = [claimed] + times + [settled_at]
    gaps = [(bounds[i + 1] - bounds[i]).total_seconds() / 60 for i in range(len(bounds) - 1)]
    return max(gaps) if gaps else 0.0


def read_log(path, cutoff):
    rows = []
    if not os.path.exists(path):
        return rows
    # Cheap pre-filter: pg-log.sh always writes `"ts":"YYYY-MM-DDTHH:MM:SSZ"`, a fixed-
    # width ISO stamp — the 19 chars right after the marker sort lexicographically the
    # same as they sort chronologically, so a plain string compare against the same
    # fixed-width cutoff can reject an old line without ever calling json.loads on it.
    # This is a fast-skip only: a line that isn't clearly older (or doesn't match the
    # marker at all) still goes through the real parse below, unchanged from before.
    marker = '"ts":"'
    cutoff_s = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    with open(path, errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            i = line.find(marker)
            if i != -1:
                ts_s = line[i + len(marker): i + len(marker) + 19]
                if len(ts_s) == 19 and ts_s < cutoff_s:
                    continue
            try:
                r = json.loads(line)
                r["_t"] = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
            except Exception:
                continue
            if r["_t"] >= cutoff:
                rows.append(r)
    return rows


LANE = re.compile(r"/pg-dispatch/([^/]+)/lanes/")


def repo_of(cwd):
    """Repo name from a working directory. A dispatch lane worktree lives at
    ~/.local/state/pg-dispatch/<slug>/lanes/<goal>, so its basename is the GOAL id —
    roll those up under the repo they belong to, or every lane looks like its own repo."""
    m = LANE.search(cwd or "")
    if m:
        return m.group(1)
    return os.path.basename((cwd or "").rstrip("/")) or "?"


def agents(rows):
    """Group log events per agent (or per session for main-loop work)."""
    by = collections.defaultdict(list)
    for r in rows:
        by[(r.get("sid"), r.get("aid") or "main")].append(r)
    out = []
    for (sid, aid), evs in by.items():
        evs.sort(key=lambda r: r["_t"])
        tools = [e for e in evs if e.get("ev") == "PostToolUse"]
        gaps = [(evs[i]["_t"] - evs[i - 1]["_t"]).total_seconds() / 60 for i in range(1, len(evs))]
        # A subagent's clock starts at SubagentStart when we have it. Falling back to its
        # first logged event undercounts every subagent by whatever it spent thinking
        # before its first tool call — measured at 3s of a real 7s — and makes a subagent
        # that never calls a tool (a lens returning a verdict) look like it never ran.
        st = next((e["_t"] for e in evs if e.get("ev") == "SubagentStart"), None)
        exact = st is not None
        start = st or evs[0]["_t"]
        out.append(dict(
            sid=sid, aid=aid, at=evs[-1].get("at") or evs[0].get("at"),
            repo=repo_of(evs[0].get("cwd") or ""),
            start=start, end=evs[-1]["_t"], exact=exact,
            mins=(evs[-1]["_t"] - start).total_seconds() / 60,
            ntool=len(tools), maxgap=max(gaps) if gaps else 0.0,
            task=next((e.get("task") for e in reversed(evs) if e.get("task")), None),
            nmsg=next((e.get("nmsg") for e in reversed(evs) if e.get("nmsg")), 0) or 0,
            harness=evs[0].get("h", "?"),
        ))
    return sorted(out, key=lambda a: a["start"])


def bar(frac, width=20):
    filled = max(0, min(width, round(frac * width)))
    return "█" * filled + "·" * (width - filled)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--roots", nargs="*", default=["~", "~/*"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    cutoff = dt.datetime.now(UTC) - dt.timedelta(days=a.days)
    since = cutoff.strftime("%Y-%m-%d")
    repos = find_repos(a.roots)
    if not repos:
        print("no repos with a docs/goals queue found", file=sys.stderr)
        return 2

    per_repo, all_goals, repo_path_by_name, inbox_debt = {}, [], {}, {}
    for repo in repos:
        name = os.path.basename(repo)
        repo_path_by_name[name] = repo
        s = [g for g in settled(goal_events(repo, since)) if g[2] >= cutoff]
        if s:
            per_repo[name] = s
            all_goals += [(name,) + g for g in s]
        n_inbox = inbox_open_count(repo)
        if n_inbox:
            inbox_debt[name] = n_inbox

    rows = read_log(a.log, cutoff)
    ags = agents(rows) if rows else []

    if a.json:
        print(json.dumps(dict(
            window_days=a.days, repos=list(per_repo),
            goals=[dict(repo=r, id=g, claimed=c.isoformat(), settled=t.isoformat(),
                        verb=v, minutes=round(m, 1)) for r, g, c, t, v, m in all_goals],
            agents=[dict(a2, start=a2["start"].isoformat(), end=a2["end"].isoformat())
                    for a2 in ags],
            inbox_debt=inbox_debt,
        ), indent=2, default=str))
        return 0

    W = 72
    print("=" * W)
    print(f"FACTORY REPORT — last {a.days} days — {dt.datetime.now(UTC):%Y-%m-%d %H:%M} UTC")
    print("=" * W)

    if not all_goals:
        print("\nNo goals settled in the window.")
    else:
        mins = [g[5] for g in all_goals]
        inbox_tail = (f"   inbox {sum(inbox_debt.values())} open across {len(inbox_debt)} repos"
                     if inbox_debt else "")
        print(f"\nGOALS  {len(all_goals)} settled across {len(per_repo)} repos"
              f"   median {st.median(mins):.0f}m   mean {st.mean(mins):.0f}m{inbox_tail}")
        by_day = collections.defaultdict(list)
        for r, g, c, t, v, m in all_goals:
            by_day[t.strftime("%m-%d")].append(m)
        worst = max((st.median(v) for v in by_day.values()), default=1) or 1
        print("\n  day      n   median")
        for d in sorted(by_day):
            v = by_day[d]
            med = st.median(v)
            print(f"  {d}  {len(v):>4}   {bar(med / worst)} {med:>6.0f}m")
        print("\n  repo                 n   median     max   inbox")
        for name, s in sorted(per_repo.items(), key=lambda kv: -len(kv[1])):
            v = [x[4] for x in s]
            print(f"  {name[:18]:18} {len(v):>3}   {st.median(v):>6.0f}m  {max(v):>6.0f}m   "
                  f"{inbox_debt.get(name, 0):>5}")
        blocked = [g for g in all_goals if g[4] == "block"]
        if blocked:
            print(f"\n  blocked: {len(blocked)} of {len(all_goals)} "
                  f"({100 * len(blocked) / len(all_goals):.0f}%)")

    # inbox debt across every repo carrying a docs/goals queue, not just the ones with
    # goals settled this window — a heavy inbox with zero recent dispatch activity is
    # exactly the pile-up this exists to surface, and the table above only shows repos
    # that already appear there.
    silent_debt = {k: v for k, v in inbox_debt.items() if k not in per_repo}
    if silent_debt:
        print(f"\nINBOX  {sum(silent_debt.values())} open, no goals settled this window "
              f"— /process-inbox")
        for name, n in sorted(silent_debt.items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {name[:18]:18} {n:>5}")

    print("\n" + "-" * W)
    if not rows:
        if os.path.isdir(os.path.dirname(a.log)):
            print("AGENTS  logging is on, but no events in this window yet — "
                  "agent numbers appear after the next run")
        else:
            print("AGENTS  event logging is off — enable with: "
                  f"mkdir -p {os.path.dirname(a.log).replace(os.path.expanduser('~'), '~')}")
    else:
        # Work is: any tool call, OR a subagent we watched start (Claude), OR a session
        # that exchanged messages (Droid, where a subagent IS a session — a lens that
        # reasons and returns a verdict calls no tools but is not an empty session).
        # Only sessions with none of the three are dropped as noise.
        work = [x for x in ags if x["ntool"] >= 1 or x["exact"] or x["nmsg"] >= 1]
        print(f"AGENTS  {len(work)} with real work, {len(rows)} events logged")
        by_type = collections.defaultdict(list)
        for x in work:
            by_type[x["at"] or "main session"].append(x)
        print("\n  role                        n   median    total   tools  timing")
        for k, v in sorted(by_type.items(), key=lambda kv: -sum(x["mins"] for x in kv[1])):
            m = [x["mins"] for x in v]
            ex = sum(1 for x in v if x["exact"])
            mark = "exact" if ex == len(v) else ("from 1st tool" if ex == 0 else f"{ex}/{len(v)} exact")
            print(f"  {k[:24]:24} {len(v):>4}  {st.median(m):>6.1f}m "
                  f"{sum(m) / 60:>6.1f}h  {st.median([x['ntool'] for x in v]):>5.0f}  {mark}")

        print("\n" + "-" * W)
        print("FAILURE SIGNALS  (reporting only — nothing here stops an agent)")
        runaway = [x for x in work if x["ntool"] >= RUNAWAY_TOOLS]
        hung = [x for x in work if x["maxgap"] >= HUNG_GAP_MIN]
        print(f"\n  runaway  {len(runaway):>3}  agents past {RUNAWAY_TOOLS} tool calls")
        for x in runaway[:5]:
            print(f"           {x['start']:%m-%d %H:%M} {x['repo'][:12]:12} "
                  f"{x['ntool']:>5} calls / {x['mins']:.0f}m  {(x['task'] or x['at'] or '')[:28]}")
        print(f"  hung     {len(hung):>3}  agents silent {HUNG_GAP_MIN:.0f}m+ mid-run")
        for x in hung[:5]:
            print(f"           {x['start']:%m-%d %H:%M} {x['repo'][:12]:12} "
                  f"{x['maxgap']:>5.0f}m gap / {x['mins']:.0f}m  {(x['task'] or x['at'] or '')[:28]}")

    long_goals = sorted([g for g in all_goals if g[5] >= LONG_GOAL_MIN], key=lambda g: -g[5])
    # Idle-inflation check: only for the genuinely slow ones (>4h), and only a `git log`
    # per goal — cheap because there are always a handful, never the whole window.
    idle_gap = {}
    for r, g, c, t, v, m in long_goals:
        if m > IDLE_GAP_CHECK_MIN:
            repo_path = repo_path_by_name.get(r)
            if repo_path:
                gap = idle_gap_minutes(repo_path, c, t)
                if gap > IDLE_GAP_WARN_MIN:
                    idle_gap[(r, g, c, t)] = gap
    oversized_n = len(long_goals) - len(idle_gap)
    idle_tail = f"  ({len(idle_gap)} idle-inflated, excluded)" if idle_gap else ""
    print(f"  oversized{oversized_n:>3}  goals over {LONG_GOAL_MIN:.0f} minutes{idle_tail}")
    for r, g, c, t, v, m in long_goals[:5]:
        gap = idle_gap.get((r, g, c, t))
        tag = f"  [idle-inflated (~{gap / 60:.0f}h gap)]" if gap else ""
        print(f"           {t:%m-%d %H:%M} {r[:12]:12} {m:>5.0f}m  {g[:34]}{tag}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
