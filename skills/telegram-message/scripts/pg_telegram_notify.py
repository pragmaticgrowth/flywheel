"""flywheel Telegram notifier — called by the plugin's hooks to DM a bot when a
run errors, waits on you, or finishes.

Contract: NEVER disrupt a session. Every path returns 0. No config / disabled /
missing token → silent no-op (this is why shipping the hooks dormant is safe).
Pure stdlib. Reads the hook event JSON from stdin; the category argv
(errors|waiting|completions) selects the config toggle and message shape.

Env:
  PG_TELEGRAM_CONFIG  override config path (default ~/.local/state/pg-telegram/config.json)
  PG_TELEGRAM_DRYRUN  =1 → print the composed message + redacted request instead of POSTing
"""
import glob, json, os, re, sys, time, urllib.request, urllib.parse

DEFAULT_TIMEOUT = 8
CATEGORIES = ("errors", "waiting", "completions", "dispatch")
# v4.14 dispatch-context gate: a fire marker / heartbeat older than this is
# treated as absent, so a crashed fire can't hold the gate open forever.
DISPATCH_CONTEXT_WINDOW = 4 * 3600


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "pg-telegram")


def config_path():
    return os.environ.get("PG_TELEGRAM_CONFIG") or os.path.join(
        state_dir(), "config.json")


def load_config(path=None):
    """Return the config dict, or None if absent/unreadable/malformed."""
    try:
        with open(path or config_path()) as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else None
    except (OSError, ValueError):
        return None


def projects_dir():
    return os.path.join(state_dir(), "projects")


def resolve_config(cwd):
    """Personal-settings resolution, first match wins:
    1. PG_TELEGRAM_CONFIG — explicit file override (tests/debug).
    2. PG_TELEGRAM_BOT_TOKEN + PG_TELEGRAM_CHAT_ID env vars — for cloud runs
       (routines and other environments) where no state file persists; enables all
       categories (narrow with PG_TELEGRAM_EVENTS=errors,dispatch,...).
    3. Per-project config: ~/.local/state/pg-telegram/projects/*.json whose
       project_root is the longest prefix of cwd. An enabled:false project
       config is an explicit opt-out — it does NOT fall through to global.
    4. Global ~/.local/state/pg-telegram/config.json.
    Returns None when nothing is configured. All project configs live OUTSIDE
    any repo, so they can never be committed or pushed."""
    explicit = os.environ.get("PG_TELEGRAM_CONFIG")
    if explicit:
        return load_config(explicit)
    tok = os.environ.get("PG_TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("PG_TELEGRAM_CHAT_ID")
    if tok and chat:
        names = (os.environ.get("PG_TELEGRAM_EVENTS") or ",".join(CATEGORIES))
        # per-run env config states its own categories — no dispatch gate;
        # PG_TELEGRAM_EVENTS is the narrowing knob in cloud runs
        return {"enabled": True, "bot_token": tok, "chat_id": chat,
                "events": {n.strip(): True for n in names.split(",") if n.strip()},
                "only_cwd": None, "min_interval_seconds": 0,
                "gate_on_dispatch": False}
    best = None
    try:
        import glob as _glob
        for f in _glob.glob(os.path.join(projects_dir(), "*.json")):
            cfg = load_config(f)
            root = (cfg or {}).get("project_root")
            if not root:
                continue
            root = root.rstrip("/")
            if cwd == root or cwd.startswith(root + "/"):
                if best is None or len(root) > len(best["project_root"].rstrip("/")):
                    best = cfg
    except OSError:
        pass
    if best is not None:
        return best
    return load_config()


def read_stdin_payload():
    """Hook events pipe JSON; dispatch pipes its raw report line (no JSON
    quoting hazards) — non-JSON stdin becomes {'report': <text>}."""
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {"report": raw.strip()}


def _dispatch_dir(payload):
    """This repo's pg-dispatch state dir (fire marker + heartbeat live here)."""
    return os.path.join(state_dir().replace("pg-telegram", "pg-dispatch"),
                        _repo(payload))


def _fresh(path, window=DISPATCH_CONTEXT_WINDOW):
    try:
        return (time.time() - os.stat(path).st_mtime) <= window
    except OSError:
        return False


def _dispatch_context(category, payload):
    """Is this repo in dispatch context for this category? waiting needs a live
    fire (`active` marker, written at fire start / removed at fire end) — a
    loop session idling BETWEEN fires is by design, not a needs-you. errors and
    completions also accept a fresh heartbeat: a wakeup turn can die to a
    rate limit before the fire writes its marker, and SessionEnd lands after
    the last fire cleaned up."""
    d = _dispatch_dir(payload)
    marker = _fresh(os.path.join(d, "active"))
    if category == "waiting":
        return marker
    return marker or _fresh(os.path.join(d, "heartbeat"))


def should_send(cfg, category, payload):
    """(bool, reason). Gate on enabled, credentials, category toggle,
    dispatch context (default on; gate_on_dispatch:false opts out), only_cwd."""
    if not cfg or not cfg.get("enabled"):
        return False, "disabled"
    if not cfg.get("bot_token") or not cfg.get("chat_id"):
        return False, "no credentials"
    if category not in CATEGORIES:
        return False, "unknown category"
    if not (cfg.get("events") or {}).get(category):
        return False, "category toggle off"
    if (category != "dispatch" and cfg.get("gate_on_dispatch", True)
            and not _dispatch_context(category, payload)):
        return False, "no dispatch context"
    only = cfg.get("only_cwd")
    if only and not (payload.get("cwd") or "").startswith(only):
        return False, "cwd out of scope"
    return True, "ok"


def _throttled(cfg, category):
    """True if a message for this category was sent within min_interval_seconds."""
    win = cfg.get("min_interval_seconds") or 0
    if win <= 0:
        return False
    stamp = os.path.join(state_dir(), f".last-{category}")
    try:
        last = float(open(stamp).read().strip())
    except (OSError, ValueError):
        last = 0.0
    now = time.time()
    if now - last < win:
        return True
    try:
        os.makedirs(state_dir(), exist_ok=True)
        open(stamp, "w").write(str(now))
    except OSError:
        pass
    return False


def sessions_dir():
    # Claude Code's live-session registry: <pid>.json files carrying
    # {"sessionId": ..., "name": <//rename or derived name>, ...}
    return os.environ.get("PG_TELEGRAM_SESSIONS_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude", "sessions")


def _session_label(payload):
    """The session's human name (/rename or derived) when resolvable from the
    sessions registry, else the session id's first 8 chars, else ''. Several
    sessions share one project — this is how the reader tells pings apart."""
    sid = payload.get("session_id") or ""
    if not sid:
        return ""
    try:
        for f in glob.glob(os.path.join(sessions_dir(), "*.json")):
            try:
                d = json.load(open(f))
            except (OSError, ValueError):
                continue
            if d.get("sessionId") == sid and d.get("name"):
                return str(d["name"])
    except OSError:
        pass
    return sid[:8]


def _cwd(payload):
    return payload.get("cwd") or os.getcwd()


def _repo(payload):
    cwd = _cwd(payload)
    return os.path.basename(cwd.rstrip("/")) or cwd or "?"


def _clip(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _strip_hb_timestamp(line):
    """Drop the heartbeat's leading UTC timestamp — Telegram already shows
    arrival time, so it's noise in the message body."""
    parts = line.split(" · ", 1)
    if len(parts) == 2 and re.match(r"^\d{4}-\d{2}-\d{2}T", parts[0].strip()):
        return parts[1]
    return line


def _heartbeat_tail(payload):
    """Best-effort newest dispatch heartbeat line for this repo (completions)."""
    path = os.path.join(_dispatch_dir(payload), "heartbeat")
    try:
        lines = [ln for ln in open(path) if ln.strip()]
        return _strip_hb_timestamp(lines[-1].strip()) if lines else ""
    except OSError:
        return ""


def compose_message(category, payload):
    """Plain-text Telegram body. First line = <emoji> <project>[ · <session>]
    · <event> — several projects (and several sessions per project) share one
    chat, so both identities lead the message. Never raises."""
    who = _repo(payload)
    label = _session_label(payload)
    if label:
        who = f"{who} · {label}"
    if category == "errors":
        err = payload.get("error") or "error"
        det = payload.get("error_details") or ""
        line2 = f"error: {err}" + (f" ({_clip(det, 120)})" if det else "")
        tail = _clip(payload.get("last_assistant_message"), 300)
        return f"🛑 {who} · turn failed\n{line2}" + (f"\n{tail}" if tail else "")
    if category == "waiting":
        msg = _clip(payload.get("message"), 300) or "agent is waiting for you"
        ntype = payload.get("notification_type")
        return f"🔔 {who} · needs you\n{msg}" + (f"\n[{ntype}]" if ntype else "")
    if category == "completions":
        reason = payload.get("reason") or "session ended"
        hb = _heartbeat_tail(payload)
        return f"✅ {who} · run ended\n{reason}" + (f"\n{hb}" if hb else "")
    if category == "dispatch":
        report = _clip(payload.get("report"), 500) or "dispatch fired"
        return f"🏭 {who} · dispatch\n{report}"
    return f"{who} · {category}"


def build_request(cfg, text):
    """The Telegram sendMessage request (not sent here). Plain text, no parse_mode."""
    url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
    return {"url": url, "data": {"chat_id": str(cfg["chat_id"]), "text": text}}


def redact(url):
    """Hide the bot token in a printable/loggable URL."""
    import re
    return re.sub(r"/bot[^/]+/", "/bot<redacted>/", url)


def _post(req):
    body = urllib.parse.urlencode(req["data"]).encode()
    r = urllib.request.Request(req["url"], data=body,
                               headers={"Content-Type":
                                        "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(r, timeout=DEFAULT_TIMEOUT) as resp:
        resp.read()


def _log(line):
    try:
        os.makedirs(state_dir(), exist_ok=True)
        with open(os.path.join(state_dir(), "notify.log"), "a") as f:
            f.write(line.rstrip() + "\n")
    except OSError:
        pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    category = argv[0] if argv else ""
    payload = read_stdin_payload()
    try:
        cfg = resolve_config(_cwd(payload))
        ok, _why = should_send(cfg, category, payload)
        if not ok:
            return 0
        if _throttled(cfg, category):
            return 0
        text = compose_message(category, payload)
        req = build_request(cfg, text)
        if os.environ.get("PG_TELEGRAM_DRYRUN") == "1":
            sys.stdout.write(f"[dry-run] POST {redact(req['url'])}\n{text}\n")
            return 0
        _post(req)
    except Exception as e:  # never disrupt the session over a notification
        _log(f"{time.time():.0f} {category} error: {e!r}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
