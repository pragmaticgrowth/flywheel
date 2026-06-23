"""Verify a goal PR, then merge it. Shipped inside pg-plugin (MIT).
Dispatch calls this instead of raw `gh pr merge` so the harness allow-rule
can be narrow (Bash(python3 <abs>/pg_safe_merge.py:*)) instead of broad."""

GREEN_CHECK = {"SUCCESS", "NEUTRAL", "SKIPPED"}
UNMERGEABLE = {"BLOCKED", "DIRTY", "BEHIND", "DRAFT"}


def verify_pr(pr, *, goal, base, expected_head, expected_base, current_base_sha):
    reasons = []
    if pr.get("headRefName") != f"goal/{goal}":
        reasons.append(f"head branch {pr.get('headRefName')!r} is not goal/{goal}")
    if f"Goal: {goal}" not in (pr.get("body") or ""):
        reasons.append(f"PR body is missing the 'Goal: {goal}' marker")
    if pr.get("baseRefName") != base:
        reasons.append(f"PR base {pr.get('baseRefName')!r} != configured base {base!r}")
    for c in pr.get("statusCheckRollup") or []:
        concl = (c.get("conclusion") or c.get("state") or "").upper()
        if concl not in GREEN_CHECK:
            name = c.get("name") or c.get("context") or "check"
            reasons.append(f"check {name!r} is not green ({concl or 'PENDING'})")
    if pr.get("mergeStateStatus") in UNMERGEABLE:
        reasons.append(f"merge state is {pr.get('mergeStateStatus')} (not mergeable)")
    for f in pr.get("files") or []:
        if f.get("path", "").startswith("docs/goals/"):
            reasons.append(f"PR edits queue file {f['path']!r}; implementers must never touch docs/goals/")
    if expected_head and pr.get("headRefOid") != expected_head:
        reasons.append(f"head SHA drifted ({pr.get('headRefOid')} != verified {expected_head})")
    if expected_base and current_base_sha != expected_base:
        reasons.append(f"base moved since verification ({current_base_sha} != {expected_base})")
    return (len(reasons) == 0, reasons)


import argparse, json, subprocess, sys


class GhError(Exception):
    pass


def _gh_json(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise GhError(out.stderr.strip() or "gh failed")
    return json.loads(out.stdout or "null")


def _current_base_sha(base):
    out = subprocess.run(["git", "rev-parse", f"origin/{base}"], capture_output=True, text=True)
    if out.returncode != 0:
        raise GhError(out.stderr.strip() or "git rev-parse failed")
    return out.stdout.strip()


def _allowed_methods():
    repo = _gh_json(["repo", "view", "--json",
                     "squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed"])
    order = [("squashMergeAllowed", "squash"), ("mergeCommitAllowed", "merge"),
             ("rebaseMergeAllowed", "rebase")]
    return [m for k, m in order if repo.get(k)]


def _self_test():
    import test_pg_safe_merge as t  # sibling module; ships alongside this script
    fns = [g for n, g in sorted(vars(t).items())
           if n.startswith("test_") and n != "test_self_test_mode_exits_zero"]
    for fn in fns:
        fn()
    print(f"self-test: {len(fns)} verify_pr cases passed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pg_safe_merge.py")
    ap.add_argument("--pr"); ap.add_argument("--goal"); ap.add_argument("--base")
    ap.add_argument("--expected-head", default=""); ap.add_argument("--expected-base", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not (a.pr and a.goal and a.base):
        ap.error("--pr, --goal and --base are required")
    try:
        pr = _gh_json(["pr", "view", a.pr, "--json",
                       "headRefName,baseRefName,body,mergeStateStatus,statusCheckRollup,files,headRefOid"])
        base_sha = _current_base_sha(a.base)
        methods = _allowed_methods()
    except GhError as e:
        print(f"[pg-safe-merge] environment error: {e}", file=sys.stderr); return 4
    ok, reasons = verify_pr(pr, goal=a.goal, base=a.base, expected_head=a.expected_head,
                            expected_base=a.expected_base, current_base_sha=base_sha)
    if not ok:
        print("[pg-safe-merge] REFUSED to merge:", file=sys.stderr)
        for r in reasons:
            print(f"  - {r}", file=sys.stderr)
        return 3
    if not methods:
        print("[pg-safe-merge] no merge method enabled on this repo", file=sys.stderr); return 3
    method = methods[0]  # prefer squash > merge > rebase
    if a.dry_run:
        print(f"[pg-safe-merge] OK — would merge PR #{a.pr} via --{method} --delete-branch")
        return 0
    out = subprocess.run(["gh", "pr", "merge", a.pr, f"--{method}", "--delete-branch"],
                         capture_output=True, text=True)
    sys.stdout.write(out.stdout); sys.stderr.write(out.stderr)
    return 0 if out.returncode == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
