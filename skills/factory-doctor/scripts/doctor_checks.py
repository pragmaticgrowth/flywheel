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


def stale_claim_problems(goals, branch_exists):
    # in_progress goals with no goal/<id> branch locally and no recorded PR are stale
    # claims / silent-death candidates the next dispatch fire must respawn or unblock.
    out = []
    for gid, entry in (goals or {}).items():
        entry = entry or {}
        if entry.get("status") != "in_progress":
            continue
        if entry.get("pr"):
            continue
        if not branch_exists.get(gid):
            out.append(f"{gid}: in_progress but no goal/{gid} branch locally and no pr — stale claim / silent-death candidate")
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


# ---- new local-gate check helpers ----

def verify_check(verify_cmds, active_goals):
    if not verify_cmds:
        if active_goals:
            return {"check": "verify", "level": "WARN",
                    "detail": "no config.verify commands — the loop has no local gate",
                    "fix": "add verify: [<build cmd>, <test cmd>] to docs/goals/index.yaml config"}
        return {"check": "verify", "level": "INFO", "detail": "no config.verify (no active goals)", "fix": ""}
    return {"check": "verify", "level": "INFO",
            "detail": f"verify: {len(verify_cmds)} command(s) configured", "fix": ""}


def working_tree_check(porcelain):
    if porcelain.strip():
        return {"check": "working-tree", "level": "WARN",
                "detail": "uncommitted changes present",
                "fix": "commit or stash before dispatch — goals commit onto the current branch"}
    return {"check": "working-tree", "level": "INFO", "detail": "working tree clean", "fix": ""}


def working_branch_check(current, base):
    if current and current == base:
        return {"check": "working-branch", "level": "WARN",
                "detail": f"on base branch '{base}' — verify this is your intended working branch",
                "fix": "checkout your working branch (e.g. staging) if base should stay clean"}
    return {"check": "working-branch", "level": "INFO", "detail": f"on '{current or 'detached'}'", "fix": ""}


def run_checks(base):
    C = []

    def add(check, level, detail, fix=""):
        C.append({"check": check, "level": level, "detail": detail, "fix": fix})

    rc, out, _ = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = out.strip() if rc == 0 else os.getcwd()

    # working-tree check (before everything else — dirty tree is important to flag early)
    _, porcelain, _ = _run(["git", "status", "--porcelain"])
    wt = working_tree_check(porcelain or "")
    C.append(wt)

    # working-branch check
    _, head_ref, _ = _run(["git", "symbolic-ref", "--short", "HEAD"])
    wb = working_branch_check((head_ref or "").strip(), base)
    C.append(wb)

    # software
    rc, out, _ = _run(["gh", "--version"])
    add("gh", "INFO", out.splitlines()[0] if rc == 0 and out.strip() else "gh not found or old")

    rc, out, _ = _run(["git", "--version"])
    add("git", "INFO" if rc == 0 and version_ge(out, "2.20") else "BLOCKER", out.strip() or "git missing")

    add("python3", "INFO", sys.version.split()[0])
    if yaml is None:
        add("pyyaml", "BLOCKER", "pyyaml not importable (dispatch + this probe parse the queue with it)",
            "FIX: python3 -m pip install --user pyyaml  (if PEP-668 externally-managed, add --break-system-packages — still user-scope)")

    # auth (INFO-only)
    rc, out, err = _run(["gh", "auth", "status"])
    add("gh-auth", "INFO",
        "authenticated" if rc == 0 else "not authenticated — gh features unavailable",
        "" if rc == 0 else "gh auth login -h github.com")

    # CI (INFO-only)
    wf = os.path.join(repo_root, ".github", "workflows")
    has_wf = os.path.isdir(wf) and any(f.endswith((".yml", ".yaml")) for f in os.listdir(wf))
    add("ci", "INFO", "CI workflow present" if has_wf else "no CI workflow found")

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

    # queue
    idx = os.path.join(repo_root, "docs", "goals", "index.yaml")
    goals_dir = os.path.join(repo_root, "docs", "goals")
    active_goals = 0
    verify_cmds = []
    if not os.path.exists(idx):
        add("queue", "WARN", "no docs/goals/index.yaml", "FIX: scaffold a default index.yaml")
    elif yaml is not None:
        try:
            index_obj = yaml.safe_load(open(idx)) or {}
            ok, probs = validate_queue(index_obj)
            add("queue", "INFO" if ok else "WARN",
                "queue valid" if ok else "; ".join(probs), "" if ok else "report drift")
            goals = index_obj.get("goals") or {}
            config = index_obj.get("config") or {}
            verify_cmds = config.get("verify") or []
            active_goals = sum(1 for e in goals.values()
                               if (e or {}).get("status") in ("not_started", "in_progress"))
            # queue liveness: in_progress claims with no local goal/<id> branch and no PR
            branch_exists = {}
            for gid, e in goals.items():
                if (e or {}).get("status") == "in_progress":
                    _, ls, _ = _run(["git", "branch", "--list", f"goal/{gid}"])
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

    # verify check (local gate) — needs active_goals + verify_cmds from queue parse above
    vc = verify_check(verify_cmds, active_goals)
    C.append(vc)

    levels = {c["level"] for c in C}
    result = "BLOCKER" if "BLOCKER" in levels else "WARN" if "WARN" in levels else "READY"
    return C, result


def main(argv=None):
    ap = argparse.ArgumentParser(prog="doctor_checks.py")
    ap.add_argument("--base", default="main")
    ap.add_argument("--self-test", action="store_true", help="run the test suite and exit")
    a = ap.parse_args(argv)
    if a.self_test:
        test_file = os.path.join(os.path.dirname(__file__), "test_doctor_checks.py")
        rc = subprocess.run([sys.executable, "-m", "pytest", test_file, "-v"]).returncode
        return rc
    checks, result = run_checks(a.base)
    print(json.dumps({"checks": checks, "result": result}, indent=2))
    return {"READY": 0, "WARN": 1, "BLOCKER": 2}[result]


if __name__ == "__main__":
    sys.exit(main())
