#!/usr/bin/env python3
"""pm.py — conductor ops kit for herdr-pm-agent (stdlib only).

Wraps the fiddly, live-verified herdr mechanics a conductor repeats every turn,
so the model spends judgment on decisions, not on JSON plumbing. Sibling script
`resolve_ids.py` is the bare resolver (terminal_id -> session_id ladder); this
one drives. Pass --session wherever you know it: every subcommand then applies
the same identity doctrine (a pane that exists is not proof it's yours).

  dispatch   -> safe mission send: composer hygiene -> pane run -> verify it
                went `working` -> eaten-Enter recovery via `send-keys Enter`
                (a second `pane run` would DOUBLE the text). --file mints a
                UNIQUE completion marker (TASK_DONE_<hex4>) and sends a short
                pointer instead of the file body; reuse `marker`/`wait_regex`
                from its output verbatim (a reused marker false-fires the next
                wait instantly — launcher pitfall #28). --dry-run previews the
                exact payload without sending. A stray composer line that is
                not your own text ABORTS (reason: stray_composer_text) — a
                human's unsent draft is never silently cleared (--clear-stray
                opts out after you judged it disposable).
  await      -> synchronous marker-wait on `herdr wait output` (for codex/pi/
                hermes conductors; claude conductors background the same
                `herdr wait output` call directly instead). Greps scrollback
                for the marker on every chunk timeout, so a marker printed
                between re-arms is never missed (assumes a unique marker).
  keys       -> identity-checked send-keys for answering another agent's
                arrow-widget/gate: resolve --term (+ --session match) at call
                time, then `pane send-keys` — never key a stale pane id.
  lanes      -> reconcile your executor-lane table against reality: worktree
                list x agent list, filtered to --branch-prefix (default pm/),
                foreign worktrees (e.g. .claude/worktrees/agent-*) counted but
                ignored. `zombie: true` = checkout exists but no open
                workspace / live agent.
  review     -> run a codex code review of a repo/worktree YOURSELF (you have a
                shell). Structured findings via the codex plugin runtime when on
                disk, native `codex review` otherwise (CLI-only hosts work too).
                Read-only. PARAPHRASE findings_markdown into your brief + scored
                fix-options; never paste raw, never auto-fix. Background it.
  capabilities -> report Herdr protocol/version and which PM helpers are usable
                on this server/client pair.
  notify     -> best-effort user notification wrapper. Disabled, busy, and
                rate-limited notifications are reported, not treated as loop
                failures.
  tail       -> deep history without sessionr: read the managed claude agent's
                transcript JSONL under ~/.claude/projects/
  read       -> identity-safe pane read: resolve (--term + session_match, or
                $HERDR_PANE_ID self) then print the PLAIN pane text. Kills the
                stale-pane-id read class (#21) in one call.
  status     -> YOUR live status line: pane custom_status via report-metadata
                (<=24 chars, TTL auto-expiry). The pane LABEL never changes;
                this is the channel that does. --clear removes it.
  diagnose   -> read-only diagnostic bundle: resolve identity, pane/agent info,
                agent explain, layout, and recent tail. Use when status or ids
                look wrong before touching a managed agent.
  label      -> rename YOUR OWN pane. Set ONCE at spawn; never rename the tab.
                Day-to-day state belongs in `status`, not here.
  spawn-exec -> spawn one parallel EXECUTOR lane. --branch uses herdr's NATIVE
                worktree (one call: git checkout + workspace + tab), --cwd uses
                a checkout you made yourself. Handles root-pane close, short
                pane label, auth-wall check. Then `dispatch --term <exec_term>`.

Own-pane commands (read/status/label) self-target via $HERDR_PANE_ID when
--term is omitted — zero id juggling for your own pane. $HERDR_PANE_ID is an
INTERNAL pane id (p_NN): every pane/wait command accepts it as a target, but
it never appears in `pane list` output — use it as a target, never compare it
to `pane_id` fields. Never override $HERDR_SOCKET_PATH (named-session routing
is automatic).
Durable artifacts (assignment, missions, handoffs) live under
~/.local/state/herdr-pm/<slug>/ — never /tmp (macOS purges it).
PAUSE brake: `touch ~/.local/state/herdr-pm/PAUSE` makes every mutating
subcommand here refuse with reason "paused" — the human's out-of-band
all-stop; `rm` it to resume.
Every command prints ONE JSON object to stdout (except `read`: plain text).
Exit 0 = ok:true.
The herdr binary is self-resolved (PATH does not persist across a conductor's
tool calls), so no `export PATH` guard is needed to run this script.
"""
import argparse
import glob
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time

HERDR = shutil.which("herdr") or os.path.expanduser("~/.local/bin/herdr")
COMPOSER_GLYPHS = ("❯", "›")  # claude / codex composer prompt markers
SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")  # ANSI SGR (color/dim) — for placeholder detection
# Conductors/executors are trusted at spawn time with full access (the claude
# argv already encodes that); a plain `codex` would stall on its own approval
# gate for every herdr/pm.py call, and workspace-write sandboxing severs the
# herdr socket (~/.config), the state root, and worktree git dirs.
BACKEND_ARGV = {
    "claude": ["claude", "--dangerously-skip-permissions"],
    "codex": ["codex", "-a", "never", "-s", "danger-full-access"],
    "pi": ["pi"],
    "hermes": ["hermes"],
}
AUTH_WALL = ("token_revoked", "sign in again", "refresh token")
# flywheel vendoring: leaf re-rooted "herdr-pm" -> "pg-dispatch" so PAUSE +
# state live in this plugin's namespace. STATE_ROOT is used only by the PAUSE
# file and the capabilities report here, so this change is functionally inert.
# See scripts/VENDORED.md. (Upstream shared this dir with discover_and_spawn.py,
# which flywheel does not vendor.)
STATE_ROOT = os.path.join(
    os.path.expanduser(os.environ.get("XDG_STATE_HOME") or "~/.local/state"), "pg-dispatch")
PAUSE_FILE = os.path.join(STATE_ROOT, "PAUSE")


def pause_guard():
    """Human all-stop: a PAUSE file blocks every mutating op (dispatch/keys/
    spawn-exec). Display-only ops (status/label/read) stay usable so a paused
    conductor can still say 'paused by human'."""
    if os.path.exists(PAUSE_FILE):
        return {"ok": False, "reason": "paused", "file": PAUSE_FILE,
                "hint": "human all-stop brake — `rm` the file to resume"}
    return None


def find_codex_companion():
    """The codex plugin's runtime script — present on disk whenever the CC codex
    plugin is INSTALLED (independent of whether it's enabled in settings). Gives
    structured review output; native `codex review` is the plugin-free fallback."""
    cands = glob.glob(os.path.expanduser(
        "~/.claude/plugins/cache/*/codex/*/scripts/codex-companion.mjs"))
    cands += glob.glob(os.path.expanduser(
        "~/.claude/plugins/marketplaces/*/plugins/codex/scripts/codex-companion.mjs"))
    cands += glob.glob(os.path.expanduser(
        "~/.factory/plugins/cache/*/codex/*/scripts/codex-companion.mjs"))
    cands += glob.glob(os.path.expanduser(
        "~/.factory/plugins/marketplaces/*/plugins/codex/scripts/codex-companion.mjs"))
    cands = [c for c in cands if os.path.isfile(c)]
    return max(cands, key=os.path.getmtime) if cands else None


def codex_plugin_enabled():
    """True if the Claude Code codex plugin (codex@<marketplace>) is enabled —
    its /codex:* review commands then work in any managed claude pane."""
    try:
        s = json.load(open(os.path.expanduser("~/.claude/settings.json")))
    except (OSError, json.JSONDecodeError):
        try:
            s = json.load(open(os.path.expanduser("~/.factory/settings.json")))
        except (OSError, json.JSONDecodeError):
            return None
    ep = s.get("enabledPlugins")
    # dict form maps plugin->bool; a DISABLED plugin stays as a key with value
    # false, so honor the value (codex review caught this false-positive).
    if isinstance(ep, dict):
        keys = [k for k, v in ep.items() if v]
    elif isinstance(ep, list):
        keys = ep
    else:
        return None
    return any(str(k).split("@", 1)[0] == "codex" for k in keys)


def run_process(*args, timeout=None):
    """Run a herdr command and return the CompletedProcess (rc + stdout + stderr)."""
    return subprocess.run([HERDR, *args], capture_output=True, text=True, timeout=timeout)


def run(*args, timeout=None):
    """Run a herdr command; return (returncode, stdout_text)."""
    p = run_process(*args, timeout=timeout)
    return p.returncode, p.stdout


def help_text(*args):
    p = run_process(*args, "--help")
    return p.returncode, p.stdout + p.stderr


def parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def command_error(args, p, parsed=None):
    return {
        "_ok": False,
        "_cmd": "herdr " + " ".join(args),
        "_returncode": p.returncode,
        "_stderr": p.stderr.strip(),
        "_stdout": p.stdout.strip(),
        **({"_error": parsed.get("error")} if isinstance(parsed, dict) and parsed.get("error") else {}),
    }


def jresult(*args):
    """Run + parse the JSON envelope; return result dict or an _ok:false error."""
    p = run_process(*args)
    parsed = parse_json(p.stdout)
    if p.returncode != 0:
        return command_error(args, p, parsed)
    if not isinstance(parsed, dict):
        return command_error(args, p, parsed)
    if parsed.get("error"):
        return command_error(args, p, parsed)
    result = parsed.get("result", {})
    if isinstance(result, dict):
        result.setdefault("_ok", True)
        return result
    return {"_ok": True, "value": result}


def raw_json(*args):
    """Run a herdr JSON-ish command and return either parsed JSON or a command error."""
    p = run_process(*args)
    parsed = parse_json(p.stdout)
    if p.returncode != 0 or parsed is None:
        return command_error(args, p, parsed)
    if isinstance(parsed, dict):
        parsed.setdefault("_ok", True)
    return parsed


def command_available(*args, must_contain=None):
    rc, text = help_text(*args)
    if rc != 0:
        return False
    return must_contain in text if must_contain else True


def panes():
    result = jresult("pane", "list")
    return result.get("panes", []) if result.get("_ok", True) else []


def pane_by_term(term):
    return next((p for p in panes() if p.get("terminal_id") == term), None)


def emit(obj, code=None):
    print(json.dumps(obj, indent=2))
    return (0 if obj.get("ok") else 1) if code is None else code


def need_pane(term, session=None):
    """Resolve a pane by terminal_id; if --session was given, enforce identity
    (session mismatch = NOT your pane — same doctrine as resolve_ids.py).
    NOTE: a plain /clear does NOT change herdr's reported session id (it stays
    stale), so session_match stays TRUE after /clear; a mismatch means a
    different or restarted agent, not a /clear."""
    row = pane_by_term(term)
    if not row:
        return None, {"ok": False, "error": f"no pane with terminal_id {term}",
                      "hint": "process restart? run resolve_ids.py --session to re-find it"}
    if session:
        sid = (row.get("agent_session") or {}).get("value")
        if sid != session:
            return None, {"ok": False, "error": "session_mismatch", "expected": session,
                          "found": sid,
                          "hint": "not your agent, or its process RESTARTED (new id). NOTE: a "
                                  "plain /clear does NOT cause this — herdr keeps reporting the "
                                  "old id after /clear, so a mismatch means a different/restarted "
                                  "agent; re-resolve via terminal_id and update your stored ids"}
    return row, None


def status_of(term):
    row = pane_by_term(term)
    return (row or {}).get("agent_status"), row


def resolve_self(a):
    """Own-pane ops: --term wins (resolve + optional session check); else the
    stable $HERDR_PANE_ID this process inherited from its own pane."""
    if getattr(a, "term", None):
        row, err = need_pane(a.term, a.session)
        if err:
            return None, err
        return row["pane_id"], None
    env = os.environ.get("HERDR_PANE_ID")
    if env:
        return env, None
    return None, {"ok": False, "error": "no --term given and no $HERDR_PANE_ID in env"}


def pane_field(pane_id, field):
    return (jresult("pane", "get", pane_id).get("pane") or {}).get(field)


def screen(pane_id, lines=60):
    _, out = run("pane", "read", pane_id, "--source", "recent-unwrapped", "--lines", str(lines))
    return out


def _sgr_faint(codes, faint):
    """Update faint(2) state from one SGR escape's parameters. CRUCIAL: skip the
    sub-params of 38/48 extended-color (`38;2;r;g;b`, `48;2;r;g;b`, `38;5;n`) so a
    truecolor `2` is never misread as faint — otherwise a REAL draft rendered on a
    truecolor composer background would be wrongly treated as a ghost and clobbered."""
    i = 0
    while i < len(codes):
        c = codes[i]
        if c in ("38", "48"):
            nxt = codes[i + 1] if i + 1 < len(codes) else ""
            i += 5 if nxt == "2" else 3 if nxt == "5" else 1
            continue
        if c == "2":
            faint = True
        elif c in ("0", "22", ""):
            faint = False
        i += 1
    return faint


def _faint_at(raw, snippet):
    """Walk a raw ANSI line tracking SGR faint(2) state; return whether the run that
    contains `snippet` is rendered DIM. A composer GHOST PLACEHOLDER is always faint;
    real typed input never is — so faint == placeholder. Processes leading SGR even when
    the snippet starts at column 0, and treats 38/48 truecolor `2` as colour, not faint."""
    plain = SGR_RE.sub("", raw)
    idx = plain.find(snippet)
    if idx < 0:
        return False
    faint = False
    pi = i = 0
    n = len(raw)
    while i < n:
        m = SGR_RE.match(raw, i)
        if m:
            faint = _sgr_faint(m.group(1).split(";") if m.group(1) else ["0"], faint)
            i = m.end()
            continue
        if pi >= idx:
            return faint
        pi += 1
        i += 1
    return faint


def composer_line(pane_id):
    """Read the composer input (LAST glyph-prefixed line). Returns the typed draft, or
    None when the composer is EMPTY. 'Empty' covers two model-specific GHOST renders that
    are not real input — without this, dispatch falsely aborts a fresh agent's first send
    as stray_composer_text:
      - ellipsis/whitespace placeholder (Fable 5 idle `❯ …` vs Opus bare `❯`);
      - a DIM (\\e[2m faint) hint string (codex idle `› Write tests for @filename`).
    Real typed input is never faint, so faint text == placeholder == empty; a real
    truncated draft (`actualtext…`) is non-empty after the ellipsis strip and not faint,
    so it is kept. ADVISORY ONLY: render can lag send-keys; agent_status is the truth."""
    _, ansi = run("pane", "read", pane_id, "--source", "recent-unwrapped", "--ansi", "--lines", "60")
    for raw in reversed(ansi.splitlines()):
        plain = SGR_RE.sub("", raw).strip()
        if plain[:1] in COMPOSER_GLYPHS:
            text = plain[1:].strip()
            if not text.strip("….·• "):
                return None                       # empty / ellipsis placeholder
            if _faint_at(raw, text[:24]):
                return None                       # dim ghost hint -> empty
            return text
    return None


def looks_like_ours(stray, text):
    """Is the composer text a render of OUR pending text? Used only to recover an
    eaten Enter (re-submit) vs. abort on a foreign draft. STRICT on purpose: every
    `--file` mission pointer shares the long `Read .../herdr-pm/` state-root prefix,
    and the pane render can truncate a DIFFERENT mission's stale pointer down to
    that shared prefix — a bare prefix match would then submit the wrong mission
    (codex review caught this). A non-truncated render that matches is ours; a
    TRUNCATED one must reach past the shared `/herdr-pm/` boundary into the unique
    per-mission slug to count — otherwise it's ambiguous and we abort."""
    raw = (stray or "").strip()
    truncated = raw.endswith(("…", "...", ".."))
    s = raw.rstrip("….").strip()
    if len(s) < 8 or not (text.startswith(s) or s in text):
        return False
    if not truncated:
        return True
    after = s.split("/herdr-pm/", 1)          # visible part must include a slug segment
    return len(after) == 2 and bool(after[1].strip(" /"))


# ----------------------------------------------------------------- commands

def cmd_capabilities(_):
    status = raw_json("status", "--json")
    client = status.get("client") if isinstance(status, dict) else None
    server = status.get("server") if isinstance(status, dict) else None
    caps = {
        "pane_report_metadata": command_available("pane", must_contain="report-metadata"),
        "notification_show": command_available("notification", must_contain="notification show"),
        "worktree": command_available("worktree", must_contain="worktree create"),
        "agent_explain": command_available("agent", must_contain="agent explain"),
        "agent_read": command_available("agent", must_contain="agent read"),
        "pane_layout": command_available("pane", must_contain="pane layout"),
        "agent_wait_terminal_target": command_available("agent", must_contain="targets accept terminal ids"),
    }
    # boot doctor: "am I wired?" in one call — any red flag here is a
    # first-turn report item, not something to silently work around.
    pane_env = os.environ.get("HERDR_PANE_ID")
    codex_home = os.path.isdir(os.path.expanduser("~/.codex"))
    codex_cli = shutil.which("codex")
    codex_plugin = codex_plugin_enabled()
    env = {
        "herdr_env": os.environ.get("HERDR_ENV"),
        "herdr_pane_id": pane_env,
        "self_pane_ok": bool(jresult("pane", "get", pane_env).get("pane")) if pane_env else None,
        "socket_path": os.environ.get("HERDR_SOCKET_PATH"),
        "sessionr": shutil.which("sessionr"),
        # PM-as-human toolkit (references/managed-agent-controls.md):
        "agent_browser": shutil.which("agent-browser"),   # verify frontend like a human
        "codex_home": codex_home,                          # ~/.codex present
        "codex_cli": codex_cli,                            # native `codex review`
        "codex_plugin_enabled": codex_plugin,              # /codex:review in a claude pane
    }
    return emit({
        "ok": bool(server and server.get("running") and server.get("compatible")),
        "client": client,
        "server": server,
        "protocol": (server or {}).get("protocol") or (client or {}).get("protocol"),
        "server_capabilities": (server or {}).get("capabilities"),
        "capabilities": caps,
        "env": env,
        # can offer a codex second-opinion review at all (still ask the human once before using):
        "can_offer_codex_review": bool(codex_home and (codex_cli or codex_plugin)),
        "state_root": STATE_ROOT,
        "paused": os.path.exists(PAUSE_FILE),
        **({} if isinstance(status, dict) and status.get("_ok", True) else {"raw_status": status}),
    })


def cmd_notify(a):
    title = (a.title or "").strip()
    if not title:
        return emit({"ok": False, "error": "title must contain visible text"})
    if not command_available("notification", must_contain="notification show"):
        return emit({
            "ok": True,
            "shown": False,
            "reason": "unsupported",
            "type": "notification_show",
            "note": "this Herdr client has no notification show wrapper",
        })
    args = ["notification", "show", title, "--sound", a.sound]
    if a.body:
        args.extend(["--body", a.body])
    if a.position:
        args.extend(["--position", a.position])
    result = jresult(*args)
    if not result.get("_ok", True):
        return emit({"ok": False, "error": "notification_failed", "raw": result})
    return emit({
        "ok": True,
        "shown": result.get("shown"),
        "reason": result.get("reason"),
        "type": result.get("type"),
    })

def cmd_dispatch(a):
    guard = pause_guard()
    if guard:
        return emit(guard)
    if bool(a.file) == bool(a.text):
        return emit({"ok": False, "error": "exactly one of --text or --file"})

    text, extra = a.text, {}
    if a.file:
        path = os.path.abspath(os.path.expanduser(a.file))
        if not os.path.isfile(path):
            return emit({"ok": False, "error": f"mission file not found: {path}"})
        try:
            body = open(path, encoding="utf-8").read()
        except OSError as e:
            return emit({"ok": False, "error": f"mission file unreadable: {e}"})
        bare = [ln.strip() for ln in body.splitlines()
                if re.match(r"^\s*TASK_DONE\w*\s*$", ln)]
        # the marker lives in the POINTER below, never in the file: a bare
        # marker line inside the file false-fires the wait when echoed
        marker = a.marker or "TASK_DONE_" + secrets.token_hex(2).upper()
        extra = {"marker": marker, "file": path,
                 "wait_regex": r"^\s*" + re.escape(marker) + r"\s*$",
                 **({"lint": [f"file contains bare marker line(s) {bare[:3]!r} — "
                              "remove them or they will false-fire the wait"]} if bare else {})}
        text = (f"Read {path} and execute it fully. When fully done and all criteria "
                f"verified, print {marker} on its own line.")

    row, err = need_pane(a.term, a.session)
    if err:
        return emit(err)
    pane, actions = row["pane_id"], []
    st = row.get("agent_status")

    if a.dry_run:
        return emit({"ok": True, "dry_run": True, "target_pane": pane, "status": st,
                     "composer": composer_line(pane), "would_send": text, **extra})

    if st == "working" and not a.force:
        return emit({"ok": False, "reason": "agent_working",
                     "hint": "it is mid-task; wait, or --force to queue the text", **extra})
    if st == "blocked":
        return emit({"ok": False, "reason": "agent_blocked",
                     "hint": "it is paused on a prompt/gate — answer that first "
                             "(esc here could cancel its own question widget)", **extra})

    # composer hygiene (only when not working — esc INTERRUPTS a working claude).
    # Our own earlier eaten send -> submit it. ANYTHING else is not ours to
    # destroy (often a human's unsent draft): abort and surface, unless the
    # caller already judged it disposable (--clear-stray).
    submitted_pending = False
    stray = composer_line(pane)
    if stray and st in ("idle", "done"):
        if looks_like_ours(stray, text):
            run("pane", "send-keys", pane, "Enter")
            actions.append("enter_submitted_pending_text")
            submitted_pending = True
            time.sleep(0.5)
        elif a.clear_stray:
            run("pane", "send-keys", pane, "Esc")  # herdr key name is `Esc`, not `Escape`
            actions.append(f"esc_cleared_stray:{stray[:40]!r}")
            time.sleep(0.5)
        else:
            return emit({"ok": False, "reason": "stray_composer_text", "composer": stray,
                         "hint": "unsubmitted composer text is not yours to clear — "
                                 "surface it to the human, or re-run with --clear-stray "
                                 "after judging it disposable", **extra})

    if not submitted_pending:
        run("pane", "run", pane, text)
        actions.append("pane_run")

    def poll(seconds):
        for _ in range(seconds):
            time.sleep(1)
            _row, poll_err = need_pane(a.term, a.session)
            if poll_err:
                return None, poll_err
            s = _row.get("agent_status")
            if s == "working":
                return s, None
        _row, poll_err = need_pane(a.term, a.session)
        return ((_row or {}).get("agent_status"), poll_err)

    st, poll_err = poll(a.confirm_secs)
    if poll_err:
        return emit(poll_err)
    if st != "working":
        # eaten Enter: if OUR text sits in the composer, submit it — NEVER a
        # second `pane run` (that doubles the text into one garbled line).
        row, rerr = need_pane(a.term, a.session)  # session-safe re-resolve: ids renumber, and a
        if rerr:                                   # restart could reassign this id to a DIFFERENT agent
            return emit(rerr)
        pane = row["pane_id"]
        comp = composer_line(pane) or ""
        if comp and looks_like_ours(comp, text):
            run("pane", "send-keys", pane, "Enter")
            actions.append("enter_submitted_pending_text")
            st, poll_err = poll(max(3, a.confirm_secs // 2))
            if poll_err:
                return emit(poll_err)
    if st == "blocked":
        # the send WAS accepted, but the agent landed on a gate/prompt (common with codex's
        # per-command approvals) — surface that, don't call it a failed submit or resend.
        return emit({"ok": False, "reason": "agent_blocked", "status": st,
                     "hint": "send landed on a gate — answer it (pm.py keys / pane run), then "
                             "re-wait; do NOT resend the mission", **extra})
    ok = st == "working"
    return emit({"ok": ok, "status": st, "actions": actions, **extra,
                 **({} if ok else {"reason": "submit_not_accepted",
                                   "composer": composer_line(pane)})})


def cmd_await(a):
    deadline = time.time() + a.timeout_ms / 1000.0
    pattern = a.pattern or rf"^\s*{re.escape(a.marker)}\s*$"
    line_re = re.compile(pattern)
    idle_streak = 0

    def marker_on_screen(pane):
        """The wait only sees the window from its own arm time (pitfall #28), so a
        marker printed BETWEEN re-arms would be missed — this grep closes that gap.
        Only safe with a per-mission unique marker (dispatch --file mints one)."""
        return next((ln for ln in screen(pane, 120).splitlines() if line_re.match(ln)), None)

    while True:
        row, err = need_pane(a.term, a.session)
        if err:
            return emit(err)
        pane = row["pane_id"]  # re-resolve every chunk: ids renumber mid-wait
        remaining_ms = int((deadline - time.time()) * 1000)
        if remaining_ms <= 0:
            return emit({"ok": False, "result": "timeout",
                         "status": row.get("agent_status")})
        chunk = str(min(a.chunk_ms, remaining_ms))
        rc, out = run("wait", "output", pane, "--match", pattern, "--regex",
                      "--source", "recent-unwrapped", "--timeout", chunk)
        if rc == 0:
            try:
                matched = json.loads(out)["result"].get("matched_line")
            except (json.JSONDecodeError, KeyError):
                matched = None
            return emit({"ok": True, "result": "marker", "matched_line": matched,
                         "status": status_of(a.term)[0]})
        hit = marker_on_screen(pane)
        if hit is not None:
            return emit({"ok": True, "result": "marker", "via": "scrollback",
                         "matched_line": hit, "status": status_of(a.term)[0]})
        st, _ = status_of(a.term)
        if st == "blocked":
            return emit({"ok": False, "result": "blocked",
                         "tail": screen(pane, 40).splitlines()[-15:]})
        if st in ("idle", "done"):
            idle_streak += 1
            # idle WITHOUT the marker for a while = it asked a question, or it
            # yielded on backgrounded work. Hand back for classification.
            if idle_streak >= a.idle_grace:
                return emit({"ok": False, "result": "idle_no_marker", "status": st,
                             "tail": screen(pane, 40).splitlines()[-15:]})
        else:
            idle_streak = 0


def cmd_tail(a):
    row, err = need_pane(a.term, a.session)
    if err:
        return emit(err)
    sid = (row.get("agent_session") or {}).get("value")
    cwd = row.get("cwd") or ""
    if row.get("agent") != "claude" or not cwd:
        return emit({"ok": False, "hint": "transcript tail is claude-only (Droid stores transcripts differently — use `herdr pane read` or sessionr)"})
    proj = os.path.expanduser("~/.claude/projects/" + re.sub(r"[/.]", "-", cwd))
    path = os.path.join(proj, f"{sid}.jsonl") if sid else ""
    fallback = False
    if not os.path.isfile(path):
        cands = sorted((os.path.join(proj, f) for f in os.listdir(proj)
                        if f.endswith(".jsonl")) if os.path.isdir(proj) else [],
                       key=os.path.getmtime, reverse=True)
        if not cands:
            return emit({"ok": False, "hint": f"no transcript under {proj} — "
                                              "session may predate this cwd"})
        path, fallback = cands[0], True  # stored id's file is gone (process restart) → newest jsonl.
        # (After a plain /clear the OLD id's file still exists, so this fallback does NOT trigger and
        # tail would read the CLEARED session — herdr's reported id stays stale on /clear, live-verified.)
    turns = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            role, ts = d.get("type"), d.get("timestamp", "")
            if role not in ("assistant", "user"):
                continue
            content = (d.get("message") or {}).get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(c.get("text", "") for c in content
                                 if c.get("type") == "text")
            else:
                text = ""
            if text.strip():
                turns.append({"role": role, "ts": ts, "text": text[:a.chars]})
    return emit({"ok": True, "path": path, "fallback_newest_jsonl": fallback,
                 "turns": turns[-a.n:]})


def cmd_read(a):
    if getattr(a, "term", None):
        row, err = need_pane(a.term, a.session)
        if err:
            return emit(err)
        if a.source != "detection":
            # stable-id read — no resolve->read window at all (pitfall #21);
            # `agent read` does not serve the detection snapshot, so that
            # source (and any older client) falls through to pane read.
            # NOTE: unlike `pane read` (plain text), `agent read` returns a
            # JSON envelope — the text lives at result.read.text.
            rc, out = run("agent", "read", a.term,
                          "--source", a.source, "--lines", str(a.lines))
            if rc == 0:
                try:
                    text = json.loads(out)["result"]["read"]["text"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    text = None  # unexpected shape — fall through to pane read
                if text is not None:
                    sys.stdout.write(text if text.endswith("\n") else text + "\n")
                    return 0
        rc, out = run("pane", "read", row["pane_id"],
                      "--source", a.source, "--lines", str(a.lines))
        if rc != 0:
            return emit({"ok": False, "error": "pane_read_failed",
                         "pane_id": row["pane_id"]})
        sys.stdout.write(out)
        return 0
    pane, err = resolve_self(a)
    if err:
        return emit(err)
    rc, out = run("pane", "read", pane, "--source", a.source, "--lines", str(a.lines))
    if rc != 0:
        return emit({"ok": False, "error": "pane_read_failed", "pane_id": pane})
    sys.stdout.write(out)
    return 0


def cmd_status(a):
    pane, err = resolve_self(a)
    if err:
        return emit(err)
    src = "user:herdr-pm"
    if not command_available("pane", must_contain="report-metadata"):
        return emit({
            "ok": True,
            "pane_id": pane,
            "custom_status": None,
            "reason": "unsupported",
            "note": "this Herdr client has no pane report-metadata wrapper; keep the fixed pane label and mention status in your message body",
        })
    if a.clear:
        rc, _ = run("pane", "report-metadata", pane, "--source", src, "--clear-custom-status")
        if rc != 0:
            return emit({"ok": False, "error": "report_metadata_failed", "pane_id": pane})
        got = pane_field(pane, "custom_status")
        return emit({"ok": True, "pane_id": pane, "custom_status": got,
                     "note": "clear accepted; effective custom_status may remain if another source supplies it"})
    text = (a.text or "").strip()
    if not text or len(text) > 24:
        return emit({"ok": False,
                     "error": f"status must be 1-24 chars (compact), got {len(text)}: {text!r}"})
    args = ["pane", "report-metadata", pane, "--source", src, "--custom-status", text]
    if a.ttl_ms:  # --ttl-ms 0 = sticky (no expiry) — for 'awaiting you'/'blocked: …';
        args += ["--ttl-ms", str(a.ttl_ms)]  # ALWAYS clear/replace sticky on next wake
    rc, _ = run(*args)
    if rc != 0:
        return emit({"ok": False, "error": "report_metadata_failed", "pane_id": pane})
    got = pane_field(pane, "custom_status")
    return emit({"ok": got == text, "pane_id": pane, "custom_status": got,
                 "ttl_ms": a.ttl_ms or "sticky"})


def cmd_review(a):
    """Run a codex code review of a repo/worktree YOURSELF (the conductor has a
    shell) and return the dense findings for the PM to PARAPHRASE into its brief
    — never dump the raw block at the human. Read-only: no PAUSE guard, no edits.
    Companion path (structured `rendered` markdown) when the plugin is on disk;
    native `codex review` otherwise. codex reviews take minutes — background it."""
    repo = os.path.abspath(os.path.expanduser(a.repo))
    if not os.path.isdir(repo):
        return emit({"ok": False, "error": f"repo not a directory: {repo}"})
    if not shutil.which("codex"):
        return emit({"ok": False, "error": "codex CLI not found — no codex review path",
                     "hint": "install @openai/codex, or skip the codex second opinion"})
    focus = (a.focus or "").strip()
    steerable = bool(a.adversarial or focus)
    comp = find_codex_companion()

    if comp:
        verb = "adversarial-review" if steerable else "review"
        cargs = []
        if a.base:
            cargs += ["--base", a.base]
        else:
            cargs += ["--scope", "working-tree"]   # no base ⇒ the dirty tree, matching native --uncommitted
        if focus and verb == "adversarial-review":
            cargs += [focus]                       # focus text after flags
        root = os.path.dirname(os.path.dirname(comp))   # …/codex/<ver>
        env = {**os.environ, "CLAUDE_PLUGIN_ROOT": root, "DROID_PLUGIN_ROOT": root}

        def comp_json(*va):
            r = subprocess.run(["node", comp, *va], cwd=repo, env=env,
                               capture_output=True, text=True)
            try:
                return json.loads(r.stdout)
            except (json.JSONDecodeError, TypeError):
                return None

        try:                                       # foreground: blocks until codex finishes
            launch = subprocess.run(["node", comp, verb, *cargs], cwd=repo, env=env,
                                    capture_output=True, text=True, timeout=a.timeout_secs)
        except subprocess.TimeoutExpired:
            return emit({"ok": False, "result": "timeout", "repo": repo,
                         "hint": f"codex review exceeded {a.timeout_secs}s — raise --timeout-secs or re-run"})
        if launch.returncode != 0:                 # a failed launch records no job — never trust 'latest'
            return emit({"ok": False, "error": "codex review failed to run", "repo": repo,
                         "stderr": (launch.stderr or "")[-600:],
                         "stdout_tail": (launch.stdout or "")[-300:]})
        # correlate THIS run's job by its thread id, NOT the most-recent stored job
        # (concurrent/failed reviews would otherwise hand back stale findings — codex
        # review of this very helper flagged exactly that). The companion prints
        # `Thread ready (<id>)` on STDERR (live-verified — its progress reporter), not
        # stdout (which carries the final rendered review).
        m = re.search(r"Thread ready \(([0-9a-f-]+)\)",
                      (launch.stderr or "") + "\n" + (launch.stdout or ""))
        thread, job_id, how = (m.group(1) if m else None), None, "latest"
        st = comp_json("status", "--json") or {}
        pool = ([st["latestFinished"]] if st.get("latestFinished") else []) + (st.get("recent") or [])
        if thread:
            job_id = next((j.get("id") for j in pool if j.get("threadId") == thread), None)
            if job_id:
                how = "thread"
        if not job_id and pool:
            job_id = pool[0].get("id")             # newest finished, as a fallback
        res = comp_json("result", *([job_id] if job_id else []), "--json") or {}
        sj = res.get("storedJob") or {}
        if sj.get("rendered") or sj.get("summary"):
            return emit({"ok": sj.get("status") == "completed", "source": "companion",
                         "repo": repo, "base": a.base, "verb": verb, "job_id": sj.get("id"),
                         "correlated_by": how, "summary": sj.get("summary"),
                         "findings_markdown": sj.get("rendered"),
                         "note": "PARAPHRASE this into your brief + scored fix-options; do not paste raw, do not auto-fix"})
        # companion produced nothing parseable → fall through to native

    # native fallback (no plugin): `codex review [--base|--uncommitted] [<focus prompt>]`.
    # With no --base the conductor wants the DIRTY WORKING TREE — pass --uncommitted so
    # codex reviews staged/unstaged/untracked changes, not the inferred default branch.
    nargs = ["review"]
    if a.base:
        nargs += ["--base", a.base]
    else:
        nargs += ["--uncommitted"]
    prompt = focus
    if steerable and not prompt:   # --adversarial with no focus must still steer codex, not no-op
        prompt = ("Adversarially challenge the implementation approach, design choices, "
                  "tradeoffs, and hidden assumptions — not just surface defects.")
    if prompt:
        nargs += [prompt]
    try:
        p = subprocess.run(["codex", *nargs], cwd=repo, capture_output=True,
                           text=True, timeout=a.timeout_secs)
    except subprocess.TimeoutExpired:
        return emit({"ok": False, "result": "timeout", "repo": repo,
                     "hint": f"codex review exceeded {a.timeout_secs}s — raise --timeout-secs or re-run"})
    out = p.stdout or ""
    idx = out.rfind("Full review comments:")          # findings live at the tail
    findings = out[idx:].strip() if idx >= 0 else "\n".join(out.splitlines()[-40:])
    return emit({"ok": p.returncode == 0, "source": "native", "repo": repo,
                 "base": a.base, "findings_markdown": findings, "raw_chars": len(out),
                 "note": "PARAPHRASE this into your brief + scored fix-options; do not paste raw, do not auto-fix"})


def cmd_diagnose(a):
    row, err = need_pane(a.term, a.session)
    if err:
        return emit({"ok": False, "stage": "resolve", **err})
    pane = row["pane_id"]
    tail = screen(pane, a.lines).splitlines()
    out = {
        "ok": True,
        "resolved": row,
        "pane": jresult("pane", "get", pane),
        "agent": jresult("agent", "get", a.term),
        "explain": raw_json("agent", "explain", a.term, "--json"),
        "layout": jresult("pane", "layout", "--pane", pane),
        "tail": tail[-a.lines:],
    }
    if a.repo:
        # "what does herdr think" + "what does the repo say" in one wake-time call
        def g(*ga):
            p = subprocess.run(["git", "-C", a.repo, *ga], capture_output=True, text=True)
            return (p.stdout.strip() if p.returncode == 0
                    else f"<git {' '.join(ga)} failed: {(p.stderr.strip() or '?')[:120]}>")
        out["git"] = {
            "head": g("rev-parse", "--abbrev-ref", "HEAD"),
            "log_oneline_5": g("log", "--oneline", "-5").splitlines(),
            "status_sb": g("status", "-sb").splitlines(),
            "ahead_behind_upstream": g("rev-list", "--left-right", "--count", "@{u}...HEAD"),
        }
    return emit(out)


# herdr's send-keys vocabulary (live-verified): Esc Up Down Left Right Tab Enter.
# `Escape`/`Return`/`Space`/`Shift+Tab` are NOT accepted — normalize the common aliases
# so a conductor that types the obvious name doesn't silently no-op a gate answer.
KEY_ALIASES = {"escape": "Esc", "esc": "Esc", "return": "Enter", "enter": "Enter",
               "up": "Up", "down": "Down", "left": "Left", "right": "Right", "tab": "Tab"}


def cmd_keys(a):
    guard = pause_guard()
    if guard:
        return emit(guard)
    if not a.keys:
        return emit({"ok": False, "error": "no keys given — pass them after --, "
                                           "e.g. keys --term <t> -- Down Down Enter"})
    keys = [KEY_ALIASES.get(k.lower(), k) for k in a.keys]
    row, err = need_pane(a.term, a.session)  # resolve AT CALL TIME — raw send-keys
    if err:                                  # to a saved pane id keys a stranger (#21)
        return emit(err)
    p = run_process("pane", "send-keys", row["pane_id"], *keys)  # rc=1 + stderr on a bad key
    ok = p.returncode == 0
    return emit({"ok": ok, "pane_id": row["pane_id"], "keys": keys,
                 **({} if ok else {"error": (p.stderr or "").strip() or "send-keys failed",
                                   "hint": "valid keys: Esc Up Down Left Right Tab Enter"})})


def cmd_lanes(a):
    row, err = need_pane(a.term, a.session)
    if err:
        return emit(err)
    ws = row["workspace_id"]
    wt = jresult("worktree", "list", "--workspace", ws, "--json")
    if not wt.get("_ok", True):
        return emit({"ok": False, "error": "worktree list failed (older herdr?)", "raw": wt})
    label_by_term = {p.get("terminal_id"): p.get("label") for p in panes()}
    by_cwd = {}
    for ag in jresult("agent", "list").get("agents", []):
        c = ag.get("foreground_cwd") or ag.get("cwd")
        if c:
            by_cwd.setdefault(os.path.realpath(c), ag)
    lanes, foreign = [], 0
    for w in wt.get("worktrees", []):
        if not w.get("is_linked_worktree"):
            continue  # the source checkout itself
        branch = w.get("branch") or ""
        if not branch.startswith(a.branch_prefix):
            foreign += 1  # other tools' worktrees (e.g. .claude/worktrees/agent-*, .factory/worktrees/agent-*) — not yours
            continue
        path = w.get("path")
        ag = by_cwd.get(os.path.realpath(path)) if path else None
        open_ws = w.get("open_workspace_id")
        lanes.append({
            "branch": branch, "path": path,
            "lane_workspace_id": open_ws, "open": bool(open_ws),
            "exec_term": (ag or {}).get("terminal_id"),
            "agent_status": (ag or {}).get("agent_status"),
            "label": label_by_term.get((ag or {}).get("terminal_id")),
            "zombie": not (open_ws and ag),
        })
    return emit({"ok": True, "workspace_id": ws,
                 "repo_root": (wt.get("source") or {}).get("repo_root"),
                 "lanes": lanes, "foreign": foreign})


def cleanup_lane(lane_ws=None, tab=None):
    if lane_ws:
        run("worktree", "remove", "--workspace", lane_ws, "--force", "--json")
    elif tab:
        run("tab", "close", tab)


def cmd_spawn_exec(a):
    guard = pause_guard()
    if guard:
        return emit(guard)
    if bool(a.branch) == bool(a.cwd):
        return emit({"ok": False, "error": "exactly one of --branch (native worktree) "
                                           "or --cwd (pre-made checkout)"})
    label = a.label or f"⚒ EX {a.slug.upper()}"
    if len(label.split()) > 5:
        return emit({"ok": False, "error": f"pane label must be ≤5 words, got {label!r}"})
    row, err = need_pane(a.term, a.session)
    if err:
        return emit(err)
    ws, name = row["workspace_id"], f"ex-{a.slug}"
    lane = {}

    if a.branch:
        # 1a. NATIVE worktree lane: one server-side call = git checkout + workspace +
        #     tab + root pane, with worktree provenance. Trust the returned path;
        #     `worktree remove` later cleans checkout AND workspace (never the branch).
        verb = "open" if a.reuse else "create"
        args = ["worktree", verb, "--workspace", ws, "--branch", a.branch,
                "--label", name, "--no-focus", "--json"]
        if a.base and not a.reuse:
            args[6:6] = ["--base", a.base]
        wt = jresult(*args)
        if not wt.get("_ok", True):
            return emit({"ok": False, "error": f"worktree {verb} failed",
                         "hint": "older herdr, existing branch/path, or invalid base; use --reuse or fall back to --cwd mode",
                         "raw": wt})
        lane_ws = (wt.get("workspace") or {}).get("workspace_id")
        tab = (wt.get("tab") or {}).get("tab_id")
        root = (wt.get("root_pane") or {}).get("pane_id")
        cwd = (wt.get("worktree") or {}).get("path")
        if not (lane_ws and tab and cwd):
            return emit({"ok": False, "error": f"worktree {verb} failed (older herdr? "
                                               "branch exists? fall back to --cwd mode)",
                         "raw": wt})
        start_ws = lane_ws
        lane = {"lane_workspace_id": lane_ws, "worktree_path": cwd, "branch": a.branch}
    else:
        # 1b. pre-made checkout: own tab in YOUR workspace; label fixed at create
        if not os.path.isdir(a.cwd):
            return emit({"ok": False, "error": f"cwd {a.cwd!r} does not exist — "
                                               "create the git worktree first"})
        t = jresult("tab", "create", "--workspace", ws, "--label", name, "--no-focus")
        tab, root = (t.get("tab") or {}).get("tab_id"), (t.get("root_pane") or {}).get("pane_id")
        if not tab:
            return emit({"ok": False, "error": "tab create failed", "raw": t})
        cwd, start_ws = a.cwd, ws

    # 2. start the executor in the worktree (argv tokens after --)
    r = jresult("agent", "start", name, "--workspace", start_ws, "--tab", tab,
                "--no-focus", "--cwd", cwd, "--", *BACKEND_ARGV[a.backend])
    ag = r.get("agent") or {}
    if not ag.get("terminal_id"):
        cleanup_lane(lane.get("lane_workspace_id"), tab)
        return emit({"ok": False, "error": "agent start failed (name taken? backend missing?)",
                     "raw": r})
    exec_term = ag["terminal_id"]

    # 3. registration wait by TERMINAL id (pitfall #13; pane ids are legacy), then close
    #    the empty root pane (pitfall #15) — closing RENUMBERS ids, so everything below
    #    re-resolves from exec_term
    run("agent", "wait", exec_term, "--status", "idle", "--timeout", "15000")
    if root:
        run("pane", "close", root)
    me = pane_by_term(exec_term)
    if not me:
        return emit({"ok": False, "error": "executor pane vanished after spawn"})

    # 4. short pane label + read-back
    run("pane", "rename", me["pane_id"], label)
    got = (pane_by_term(exec_term) or {}).get("label")

    # 5. alive-check: no auth wall (pitfall #14)
    time.sleep(2)
    me = pane_by_term(exec_term)
    scr = screen(me["pane_id"], 30).lower()
    # a fresh agent in a NEW worktree dir hits "do you trust this folder?" (claude shows it even
    # with --dangerously-skip-permissions; live-verified). The conductor created this worktree, so
    # accept it — otherwise the first dispatch refuses it as a stray composer. Default = trust.
    trust_accepted = False
    if "trust this folder" in scr or "do you trust" in scr:
        run("pane", "send-keys", me["pane_id"], "Enter")
        trust_accepted = True
        time.sleep(1.5)
        me = pane_by_term(exec_term) or me
        scr = screen(me["pane_id"], 30).lower()
    auth_ok = not any(s in scr for s in AUTH_WALL)
    ok = bool(got == label and auth_ok)
    if not ok:
        cleanup_lane(lane.get("lane_workspace_id"), me.get("tab_id"))
    return emit({"ok": ok,
                 "exec_term": exec_term, "exec_pane": me["pane_id"],
                 "tab_id": me["tab_id"], "label": got, "auth_ok": auth_ok,
                 "trust_accepted": trust_accepted, **lane,
                 **({} if ok else {"cleanup": "lane workspace removed" if lane.get("lane_workspace_id") else "tab closed"}),
                 "next": f"pm.py dispatch --term {exec_term} --text 'Read <mission file> and execute it fully.'"})


def cmd_label(a):
    if len(a.text.split()) > 5:
        return emit({"ok": False, "error": f"pane label must be ≤5 words, got {a.text!r}"})
    pane, err = resolve_self(a)  # resolved at call time — never a saved pane id
    if err:
        return emit(err)
    run("pane", "rename", pane, a.text)
    got = pane_field(pane, "label")
    return emit({"ok": got == a.text, "pane_id": pane, "label": got})


def main():
    if not os.path.exists(HERDR):
        return emit({"ok": False, "error": "herdr binary not found (PATH or ~/.local/bin)"}, 2)
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def term_arg(p, required=True):
        p.add_argument("--term", required=required,
                       help="stable terminal_id of the pane"
                            + ("" if required else " (omit = own pane via $HERDR_PANE_ID)"))
        p.add_argument("--session", help="expected session id — enforces it's YOUR agent")

    dp = sub.add_parser("dispatch", help="safe mission send + submit verify")
    term_arg(dp)
    dp.add_argument("--text", help="short order/nudge (no marker)")
    dp.add_argument("--file", help="mission file: sends a pointer + a MINTED unique "
                                   "marker; copy `marker`/`wait_regex` from the output")
    dp.add_argument("--marker", help="override the minted TASK_DONE_<hex4> (with --file)")
    dp.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="preview target/status/composer/payload without sending")
    dp.add_argument("--clear-stray", dest="clear_stray", action="store_true",
                    help="ESC a foreign composer draft you already judged disposable "
                         "(default: abort and surface it)")
    dp.add_argument("--confirm-secs", dest="confirm_secs", type=int, default=12)
    dp.add_argument("--force", action="store_true", help="send even if status=working (queues)")

    aw = sub.add_parser("await", help="synchronous marker-wait (non-claude conductors); "
                                      "stateless — on a host-kill just re-run it")
    term_arg(aw)
    aw.add_argument("--marker", default="TASK_DONE",
                    help="the minted marker from dispatch --file; the scrollback "
                         "fallback assumes it is unique to this mission")
    aw.add_argument("--pattern", help="override the anchored regex built from --marker")
    aw.add_argument("--timeout-ms", dest="timeout_ms", type=int, default=1800000,
                    help="keep below your host's tool-call ceiling")
    aw.add_argument("--chunk-ms", dest="chunk_ms", type=int, default=30000)
    aw.add_argument("--idle-grace", dest="idle_grace", type=int, default=4,
                    help="consecutive idle chunks before handing back idle_no_marker")

    kp = sub.add_parser("keys", help="identity-checked send-keys (widgets/gates); "
                                     "keys go after --, e.g. -- Down Down Enter")
    term_arg(kp)
    kp.add_argument("keys", nargs="*", help="keys (herdr vocab): Esc Up Down Left Right Tab Enter "
                                            "(Escape/Return aliased)")

    ln = sub.add_parser("lanes", help="reconcile executor lanes: worktree x agent reality")
    term_arg(ln)  # --term = YOUR term (locates the project workspace)
    ln.add_argument("--branch-prefix", dest="branch_prefix", default="pm/",
                    help="lane branches to claim (default pm/); others count as foreign")

    sub.add_parser("capabilities", help="report Herdr protocol/version and supported PM primitives")

    nf = sub.add_parser("notify", help="best-effort Herdr notification wrapper")
    nf.add_argument("--title", required=True)
    nf.add_argument("--body")
    nf.add_argument("--position", choices=["top-left", "top-right", "bottom-left", "bottom-right"])
    nf.add_argument("--sound", default="none", choices=["none", "done", "request"])

    tl = sub.add_parser("tail", help="claude transcript tail (deep history, no sessionr)")
    term_arg(tl)
    tl.add_argument("--n", type=int, default=12)
    tl.add_argument("--chars", type=int, default=800, help="truncate each turn's text")

    rd = sub.add_parser("read", help="identity-safe read -> plain text (stable-id "
                                     "`agent read` when --term given)")
    term_arg(rd, required=False)
    rd.add_argument("--lines", type=int, default=120)
    rd.add_argument("--source", default="recent-unwrapped",
                    choices=["visible", "recent", "recent-unwrapped", "detection"])

    st = sub.add_parser("status", help="set YOUR live custom status (label stays put)")
    term_arg(st, required=False)
    st.add_argument("--text", help="≤24 chars, e.g. 'driving: clamp tests'")
    st.add_argument("--clear", action="store_true", help="remove the custom status")
    st.add_argument("--ttl-ms", dest="ttl_ms", type=int, default=2700000,
                    help="auto-expiry (default 45 min — stale states self-clear); "
                         "0 = sticky, for 'awaiting you'/'blocked: …' — always "
                         "clear/replace sticky on your next wake")

    dg = sub.add_parser("diagnose", help="read-only identity/status/layout/detection bundle")
    term_arg(dg)
    dg.add_argument("--lines", type=int, default=80)
    dg.add_argument("--repo", help="also include git head/log/status/ahead-behind for this path")

    rv = sub.add_parser("review", help="run a codex review of a repo/worktree YOURSELF "
                                       "(structured findings to paraphrase); background it")
    rv.add_argument("--repo", required=True, help="repo or worktree path to review")
    rv.add_argument("--base", help="review the branch diff against this ref (e.g. main); "
                                   "omit to review the working tree")
    rv.add_argument("--adversarial", action="store_true",
                    help="challenge the approach/design, not just defects")
    rv.add_argument("--focus", help="steer the review (implies adversarial): "
                                    "'challenge the caching + retry design'")
    rv.add_argument("--timeout-secs", dest="timeout_secs", type=int, default=600,
                    help="codex reviews take minutes; background this call")

    lb = sub.add_parser("label", help="rename YOUR pane (≤5 words; set once at spawn)")
    term_arg(lb, required=False)
    lb.add_argument("--text", required=True)

    se = sub.add_parser("spawn-exec", help="spawn a parallel executor lane in a worktree")
    term_arg(se)  # --term = YOUR term (locates the project workspace)
    se.add_argument("--slug", required=True, help="lane name -> agent ex-<slug>")
    se.add_argument("--branch", help="NATIVE lane: herdr creates worktree+workspace for this branch")
    se.add_argument("--base", help="base ref for --branch (default: current HEAD)")
    se.add_argument("--reuse", action="store_true",
                    help="open an existing worktree branch/path instead of creating a fresh one")
    se.add_argument("--cwd", help="pre-made checkout path (fallback mode)")
    se.add_argument("--backend", default="claude", choices=sorted(BACKEND_ARGV))
    se.add_argument("--label", help="pane label, ≤5 words (default: ⚒ EX <SLUG>)")

    a = ap.parse_args()
    return {"dispatch": cmd_dispatch, "await": cmd_await, "keys": cmd_keys,
            "lanes": cmd_lanes, "capabilities": cmd_capabilities, "notify": cmd_notify,
            "tail": cmd_tail, "read": cmd_read, "status": cmd_status,
            "diagnose": cmd_diagnose, "review": cmd_review, "label": cmd_label,
            "spawn-exec": cmd_spawn_exec}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
