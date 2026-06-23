"""Read-only readiness probes for the pg-plugin factory. Emits JSON; never
mutates. The factory-doctor skill interprets the output and applies fixes."""
import re


def version_ge(have, want):
    def parse(s):
        m = re.search(r"(\d+(?:\.\d+)+|\d+)", s or "")
        return [int(x) for x in m.group(1).split(".")] if m else [0]
    a, b = parse(have), parse(want)
    n = max(len(a), len(b)); a += [0] * (n - len(a)); b += [0] * (n - len(b))
    return a >= b


def _rule_matches(rule, token):
    return rule in (f"Bash({token}:*)", f"Bash({token})") or rule.startswith(f"Bash({token}")


def find_merge_permission(settings, token):
    allowed_in = denied_in = None
    for name, s in settings:
        perms = (s or {}).get("permissions", {}) or {}
        for d in perms.get("deny", []) or []:
            if _rule_matches(d, token):
                denied_in = name
        for a in perms.get("allow", []) or []:
            if _rule_matches(a, token):
                allowed_in = name
    return allowed_in, denied_in


def parse_gh_scopes(auth_status_text):
    m = re.search(r"Token scopes:\s*(.+)", auth_status_text or "")
    if not m:
        return []
    return [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()]


def validate_queue(index_obj):
    problems = []
    goals = (index_obj or {}).get("goals") or {}
    ids = set(goals)
    for gid, entry in goals.items():
        entry = entry or {}
        if "status" not in entry:
            problems.append(f"{gid}: index entry has no status")
        for dep in entry.get("depends_on", []) or []:
            if dep not in ids:
                problems.append(f"{gid}: depends_on points at missing entry {dep}")
    # simple cycle detection
    WHITE, GREY, BLACK = 0, 1, 2
    color = {g: WHITE for g in goals}

    def visit(g):
        color[g] = GREY
        for dep in (goals.get(g) or {}).get("depends_on", []) or []:
            if dep not in color:
                continue
            if color[dep] == GREY:
                problems.append(f"circular depends_on at {g}->{dep}"); return
            if color[dep] == WHITE:
                visit(dep)
        color[g] = BLACK

    for g in goals:
        if color[g] == WHITE:
            visit(g)
    return (len(problems) == 0, problems)
