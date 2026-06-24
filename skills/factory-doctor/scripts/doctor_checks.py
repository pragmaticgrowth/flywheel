"""Read-only readiness probes for the flywheel factory. Emits JSON; never
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


import argparse, glob, json, os, subprocess, sys
try:
    import yaml
except ImportError:
    yaml = None


# ---- frontend / browser-verification detection (UI goals need a real browser check) ----
def _is_ui_dep(dep):
    return (dep in {"react", "react-dom", "vue", "next", "nuxt", "vite", "preact",
                    "solid-js", "lit", "@angular/core"}
            or dep.startswith(("react-", "@angular/", "@vue/", "@sveltejs/", "@lit/")))


def _pkg_has_ui(pkg):
    deps = {}
    deps.update((pkg or {}).get("dependencies") or {})
    deps.update((pkg or {}).get("devDependencies") or {})
    return any(_is_ui_dep(d) for d in deps)


def detect_frontend(repo_root):
    # root + immediate-child package.json (monorepo apps/frontend dirs)
    candidates = [os.path.join(repo_root, "package.json")]
    try:
        for name in os.listdir(repo_root):
            p = os.path.join(repo_root, name, "package.json")
            if os.path.isfile(p):
                candidates.append(p)
    except OSError:
        pass
    for p in candidates:
        try:
            if _pkg_has_ui(json.load(open(p))):
                return True
        except (FileNotFoundError, ValueError):
            continue
    return False


def goals_reference_browser(repo_root):
    goals_dir = os.path.join(repo_root, "docs", "goals")
    if not os.path.isdir(goals_dir):
        return False
    for f in glob.glob(os.path.join(goals_dir, "*.md")):
        try:
            if "agent-browser" in open(f).read():
                return True
        except OSError:
            continue
    return False


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
    # A plugin-cache install lives at .../flywheel/<version>/skills/...; the version dir
    # changes on every update, which would break a literal allow-rule (and re-block merges
    # until re-granted). Wildcard ONLY the version segment so the rule survives updates —
    # mid-path `*` matches across `/` in Bash permission rules. Dev checkouts / the
    # marketplace clone have no version dir, so they stay literal.
    return re.sub(r"(/flywheel/)[^/]+(/skills/)", r"\1*\2", p)


def _safemerge_token():
    # Derive the wrapper from THIS script's own location — the plugin install that dispatch
    # also resolves via $CLAUDE_PLUGIN_ROOT (Claude Code) or $DROID_PLUGIN_ROOT (Droid; the
    # former is set as an alias for the latter). NEVER repo-relative: a target repo has no
    # skills/ dir, so repo_root/skills/... is a non-existent path that wouldn't match the
    # path dispatch actually invokes, leaving the allow-rule useless.
    here = os.path.dirname(os.path.realpath(__file__))
    p = os.path.realpath(os.path.join(here, "..", "..", "dispatch", "scripts", "pg_safe_merge.py"))
    return f"python3 {_durable_merge_path(p)}"


def state_branch_check(state_branch, base, exists, protected):
    if state_branch == base:
        return None  # default path: queue lives on base, covered by the base-push check
    if not exists:
        return {"name": "state-branch", "level": "WARN",
                "detail": f"state branch {state_branch!r} is missing (does not exist on origin)",
                "fix": f"FIX: git branch {state_branch} origin/{base} && git push origin {state_branch}  (or run /factory-doctor)"}
    if protected:
        return {"name": "state-branch", "level": "BLOCKER",
                "detail": f"state branch {state_branch!r} is protected — claims can't push to it",
                "fix": f"unprotect {state_branch} on GitHub, or set config.state_branch to a different unprotected branch"}
    return {"name": "state-branch", "level": "INFO",
            "detail": f"state branch {state_branch!r} exists and is pushable (not protected)"}


def _pgvalidate_path():
    # The deterministic gate dispatch runs under merge: auto — derived from THIS script's
    # install (same fallback chain as $SAFEMERGE), never repo-relative.
    here = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(here, "..", "..", "dispatch", "scripts", "pg_validate.py"))


def validation_gate_check(merge, validation, pgvalidate_present):
    # Under merge: auto, confirm the deterministic gate is actually wired: pg_validate.py
    # resolvable AND config.validation not off. Read-only; never changes the mode.
    if merge != "auto":
        return None
    if not pgvalidate_present:
        return {"check": "validation-gate", "level": "WARN",
                "detail": "pg_validate.py not resolvable from the plugin install — the deterministic gate can't run",
                "fix": "refresh the flywheel marketplace so pg_validate.py is present"}
    mode = validation or "risk_based"
    if mode == "off":
        return {"check": "validation-gate", "level": "WARN",
                "detail": "config.validation: off under merge: auto — no deterministic gate runs before merge",
                "fix": "set config.validation: risk_based (or required) in docs/goals/index.yaml"}
    return {"check": "validation-gate", "level": "INFO",
            "detail": f"deterministic gate wired (validation: {mode})"}


def stale_claim_problems(goals, branch_exists):
    # in_progress goals with no goal/<id> branch on origin and no recorded PR are stale
    # claims / silent-death candidates the next dispatch fire must respawn or unblock.
    out = []
    for gid, entry in (goals or {}).items():
        entry = entry or {}
        if entry.get("status") != "in_progress":
            continue
        if entry.get("pr"):
            continue
        if not branch_exists.get(gid):
            out.append(f"{gid}: in_progress but no goal/{gid} branch on origin and no pr — stale claim / silent-death candidate")
    return out


def _has_checkable_done(md_text):
    # True if a goal file carries a machine-checkable done-condition: a non-empty Acceptance
    # criteria section (>=1 checkbox) or a Goal contract section / a /goal line.
    text = md_text or ""
    has_accept = False
    m = re.search(r"(?im)^##\s*Acceptance criteria\s*$", text)
    if m:
        tail = text[m.end():]
        nxt = re.search(r"(?m)^##\s", tail)
        section = tail[:nxt.start()] if nxt else tail
        has_accept = bool(re.search(r"(?m)^\s*-\s*\[[ xX]\]\s*\S", section))
    has_contract = bool(re.search(r"(?im)^##\s*Goal contract\s*$", text)) or "/goal " in text
    return has_accept or has_contract


def goal_contract_problems(goals):
    # goals: list of {id, status, checkable}. Flags active goals (not_started/in_progress)
    # whose file lacks a checkable done-condition — "a loop without a goal is a slop cannon".
    return [f"{g['id']}: goal file has no checkable done-condition (acceptance criteria or goal contract)"
            for g in (goals or [])
            if g.get("status") in ("not_started", "in_progress") and not g.get("checkable")]


def run_checks(base, merge, execution, state_branch="", validation=""):
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

    # state branch (only when config sets a branch != base)
    if state_branch and state_branch != base:
        rc1, lsout, _ = _run(["git", "ls-remote", "--heads", "origin", state_branch])
        exists = bool([l for l in (lsout or "").splitlines() if state_branch in l])
        rc2, _, _ = _run(["gh", "api", f"repos/{{owner}}/{{repo}}/branches/{state_branch}/protection"])
        chk = state_branch_check(state_branch, base, exists, rc2 == 0)  # rc 0 => HTTP 200 => protected
        if chk:
            # helper returns {"name": ...} (its stable shape); normalize to the row schema
            # ("check") the rest of run_checks emits so consumers/the runner test see one shape
            C.append({"check": chk["name"], "level": chk["level"],
                      "detail": chk["detail"], "fix": chk.get("fix", "")})

    # CI
    wf = os.path.join(repo_root, ".github", "workflows")
    has_wf = os.path.isdir(wf) and any(f.endswith((".yml", ".yaml")) for f in os.listdir(wf))
    if not has_wf and merge == "auto":
        add("ci", "WARN", "no CI workflow found", "merge: auto has no automated gate; prefer merge: pr")
    else:
        add("ci", "INFO", "CI workflow present" if has_wf else "no CI (merge: pr ok)")

    # browser verification (only when frontend/UI work is present)
    if detect_frontend(repo_root) or goals_reference_browser(repo_root):
        rc, out, _ = _run(["agent-browser", "--version"])
        if rc == 0:
            add("browser-verify", "INFO",
                "frontend/UI work present; agent-browser available "
                f"({out.splitlines()[0] if out.strip() else 'ok'})")
        else:
            add("browser-verify", "WARN",
                "frontend/UI work detected but agent-browser is not installed — "
                "UI goals can't run their scripted browser check",
                "npm i -g agent-browser && agent-browser install  "
                "(then add 'agent-browser' to config.skills in docs/goals/index.yaml)")
    else:
        add("browser-verify", "INFO", "no frontend/UI work detected; browser verification not required")

    # validation gate (merge: auto only) — confirm the deterministic gate is actually wired
    vg = validation_gate_check(merge, validation, os.path.exists(_pgvalidate_path()))
    if vg:
        add(vg["check"], vg["level"], vg["detail"], vg.get("fix", ""))

    # queue
    idx = os.path.join(repo_root, "docs", "goals", "index.yaml")
    goals_dir = os.path.join(repo_root, "docs", "goals")
    if not os.path.exists(idx):
        add("queue", "WARN", "no docs/goals/index.yaml", "FIX: scaffold a default index.yaml")
    elif yaml is not None:
        try:
            index_obj = yaml.safe_load(open(idx)) or {}
            ok, probs = validate_queue(index_obj)
            add("queue", "INFO" if ok else "WARN",
                "queue valid" if ok else "; ".join(probs), "" if ok else "report drift")
            goals = index_obj.get("goals") or {}
            # queue liveness: in_progress claims with no live branch/PR = silent-death candidate
            branch_exists = {}
            for gid, e in goals.items():
                if (e or {}).get("status") == "in_progress":
                    _, ls, _ = _run(["git", "ls-remote", "--heads", "origin", f"goal/{gid}"])
                    branch_exists[gid] = bool((ls or "").strip())
            stale = stale_claim_problems(goals, branch_exists)
            add("queue-liveness", "WARN" if stale else "INFO",
                "; ".join(stale) if stale else "no stale in_progress claims",
                "dispatch will respawn or it needs unblocking" if stale else "")
            # goal contracts: active goals must carry a checkable done-condition
            gc = []
            for gid, e in goals.items():
                e = e or {}
                if e.get("status") not in ("not_started", "in_progress"):
                    continue
                try:
                    text = open(os.path.join(goals_dir, f"{gid}.md")).read()
                except OSError:
                    continue  # a missing goal file is a different concern
                gc.append({"id": gid, "status": e.get("status"), "checkable": _has_checkable_done(text)})
            cprobs = goal_contract_problems(gc)
            add("goal-contracts", "WARN" if cprobs else "INFO",
                "; ".join(cprobs) if cprobs else "active goals carry a checkable done-condition",
                "tighten via /define-goal before dispatch picks it up" if cprobs else "")
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
    ap.add_argument("--state-branch", default="")
    ap.add_argument("--validation", default="")
    a = ap.parse_args(argv)
    checks, result = run_checks(a.base, a.merge, a.execution, a.state_branch, a.validation)
    print(json.dumps({"checks": checks, "result": result}, indent=2))
    return {"READY": 0, "WARN": 1, "BLOCKER": 2}[result]


if __name__ == "__main__":
    sys.exit(main())
