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
