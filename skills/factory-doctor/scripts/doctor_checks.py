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


import argparse, json, os, subprocess, sys
try:
    import yaml
except ImportError:
    yaml = None


def _run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "not found"


def _settings_sources(repo_root):
    home = os.path.expanduser("~")
    paths = [("project", os.path.join(repo_root, ".claude", "settings.json")),
             ("project-droid", os.path.join(repo_root, ".factory", "settings.json")),
             ("local", os.path.join(repo_root, ".claude", "settings.local.json")),
             ("local-droid", os.path.join(repo_root, ".factory", "settings.local.json")),
             ("user", os.path.join(home, ".claude", "settings.json")),
             ("user-droid", os.path.join(home, ".factory", "settings.json"))]
    out = []
    for name, p in paths:
        try:
            out.append((name, json.load(open(p))))
        except (FileNotFoundError, ValueError):
            out.append((name, {}))
    return out


def _durable_merge_path(p):
    # A plugin-cache install lives at .../pg-plugin/<version>/skills/...; the version dir
    # changes on every update, which would break a literal allow-rule (and re-block merges
    # until re-granted). Wildcard ONLY the version segment so the rule survives updates —
    # mid-path `*` matches across `/` in Bash permission rules. Dev checkouts / the
    # marketplace clone have no version dir, so they stay literal.
    return re.sub(r"(/pg-plugin/)[^/]+(/skills/)", r"\1*\2", p)


def _safemerge_token():
    # Derive the wrapper from THIS script's own location — the plugin install that dispatch
    # also resolves via $CLAUDE_PLUGIN_ROOT (Claude Code) or $DROID_PLUGIN_ROOT (Droid; the
    # former is set as an alias for the latter). NEVER repo-relative: a target repo has no
    # skills/ dir, so repo_root/skills/... is a non-existent path that wouldn't match the
    # path dispatch actually invokes, leaving the allow-rule useless.
    here = os.path.dirname(os.path.realpath(__file__))
    p = os.path.realpath(os.path.join(here, "..", "..", "dispatch", "scripts", "pg_safe_merge.py"))
    return f"python3 {_durable_merge_path(p)}"


def run_checks(base, merge, execution):
    C = []

    def add(check, level, detail, fix=""):
        C.append({"check": check, "level": level, "detail": detail, "fix": fix})

    rc, out, _ = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = out.strip() if rc == 0 else os.getcwd()

    # software
    rc, out, _ = _run(["gh", "--version"])
    if rc != 0:
        add("gh", "BLOCKER", "gh CLI not found", "install GitHub CLI (https://cli.github.com)")
    elif not version_ge(out, "2.40"):
        add("gh", "WARN", f"gh too old: {out.splitlines()[0]}", "upgrade gh >= 2.40")
    else:
        add("gh", "INFO", out.splitlines()[0])
    rc, out, _ = _run(["git", "--version"])
    add("git", "INFO" if rc == 0 and version_ge(out, "2.20") else "BLOCKER", out.strip() or "git missing")
    add("python3", "INFO", sys.version.split()[0])
    if yaml is None:
        add("pyyaml", "BLOCKER", "pyyaml not importable (dispatch + this probe parse the queue with it)",
            "FIX: python3 -m pip install --user pyyaml  (if PEP-668 externally-managed, add --break-system-packages — still user-scope)")

    # auth
    rc, out, err = _run(["gh", "auth", "status"])
    if rc != 0:
        add("gh-auth", "BLOCKER", "not authenticated", "gh auth login -h github.com")
    else:
        scopes = parse_gh_scopes(out + err)
        miss = [s for s in ["repo"] if s not in scopes]
        add("gh-auth", "BLOCKER" if miss else "INFO",
            f"scopes: {', '.join(scopes) or 'unknown'}",
            (f"gh auth refresh -h github.com -s repo" if miss else ""))

    # permissions (only relevant for merge: auto)
    if merge == "auto":
        token = _safemerge_token()
        allowed_in, denied_in = find_merge_permission(_settings_sources(repo_root), token)
        if denied_in:
            add("merge-permission", "BLOCKER", f"a deny rule in {denied_in} blocks the merge wrapper",
                f"remove the Bash({token}:*) deny in .claude/settings*.json or .factory/settings*.json")
        elif allowed_in:
            add("merge-permission", "INFO", f"allow-rule present in {allowed_in}")
        else:
            add("merge-permission", "BLOCKER", "no allow-rule for the merge wrapper",
                f"FIX: add Bash({token}:*) to .claude/settings.local.json (Claude Code) or .factory/settings.local.json (Droid)")
    else:
        add("merge-permission", "INFO", "merge: pr — orchestrator never merges; no rule needed")

    # branch protection
    rc, out, _ = _run(["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{base}/protection"])
    if rc == 0:
        try:
            prot = json.loads(out or "{}")
        except ValueError:
            prot = {}
        if prot.get("required_pull_request_reviews"):
            add("branch-protection", "BLOCKER" if merge == "auto" else "WARN",
                f"{base} requires PR reviews",
                "merge: auto can't merge; set merge: pr or relax the rule")
        add("base-push", "BLOCKER",
            f"{base} is protected — the claim protocol can't push to it",
            "set config.base to a state branch, or run a single dispatcher")
    else:
        add("base-push", "INFO", f"{base} not protected/unreadable (claim protocol can push)")

    # CI
    wf = os.path.join(repo_root, ".github", "workflows")
    has_wf = os.path.isdir(wf) and any(f.endswith((".yml", ".yaml")) for f in os.listdir(wf))
    if not has_wf and merge == "auto":
        add("ci", "WARN", "no CI workflow found", "merge: auto has no automated gate; prefer merge: pr")
    else:
        add("ci", "INFO", "CI workflow present" if has_wf else "no CI (merge: pr ok)")

    # queue
    idx = os.path.join(repo_root, "docs", "goals", "index.yaml")
    if not os.path.exists(idx):
        add("queue", "WARN", "no docs/goals/index.yaml", "FIX: scaffold a default index.yaml")
    elif yaml is not None:
        try:
            ok, probs = validate_queue(yaml.safe_load(open(idx)))
            add("queue", "INFO" if ok else "WARN",
                "queue valid" if ok else "; ".join(probs), "" if ok else "report drift")
        except yaml.YAMLError as e:
            add("queue", "BLOCKER", f"index.yaml parse error: {e}")

    # herdr
    if execution == "herdr":
        rc, out, _ = _run(["herdr", "--version"])
        add("herdr", "INFO" if rc == 0 else "WARN",
            out.strip() if rc == 0 else "herdr not found — dispatch degrades to native")

    levels = {c["level"] for c in C}
    result = "BLOCKER" if "BLOCKER" in levels else "WARN" if "WARN" in levels else "READY"
    return C, result


def main(argv=None):
    ap = argparse.ArgumentParser(prog="doctor_checks.py")
    ap.add_argument("--base", default="main"); ap.add_argument("--merge", default="pr")
    ap.add_argument("--execution", default="native")
    a = ap.parse_args(argv)
    checks, result = run_checks(a.base, a.merge, a.execution)
    print(json.dumps({"checks": checks, "result": result}, indent=2))
    return {"READY": 0, "WARN": 1, "BLOCKER": 2}[result]


if __name__ == "__main__":
    sys.exit(main())
