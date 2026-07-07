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
import json, os, sys, time, urllib.request, urllib.parse

DEFAULT_TIMEOUT = 8
CATEGORIES = ("errors", "waiting", "completions", "dispatch")


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
       (routines / Droid automations) where no state file persists; enables all
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
        return {"enabled": True, "bot_token": tok, "chat_id": chat,
                "events": {n.strip(): True for n in names.split(",") if n.strip()},
                "only_cwd": None, "min_interval_seconds": 0}
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


def should_send(cfg, category, payload):
    """(bool, reason). Gate on enabled, credentials, category toggle, only_cwd."""
    if not cfg or not cfg.get("enabled"):
        return False, "disabled"
    if not cfg.get("bot_token") or not cfg.get("chat_id"):
        return False, "no credentials"
    if category not in CATEGORIES:
        return False, "unknown category"
    if not (cfg.get("events") or {}).get(category):
        return False, "category toggle off"
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


def _cwd(payload):
    return payload.get("cwd") or os.getcwd()


def _repo(payload):
    cwd = _cwd(payload)
    return os.path.basename(cwd.rstrip("/")) or cwd or "?"


def _clip(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _heartbeat_tail(payload):
    """Best-effort newest dispatch heartbeat line for this repo (completions)."""
    slug = _repo(payload)
    path = os.path.join(state_dir().replace("pg-telegram", "pg-dispatch"),
                        slug, "heartbeat")
    try:
        lines = [ln for ln in open(path) if ln.strip()]
        return lines[-1].strip() if lines else ""
    except OSError:
        return ""


def compose_message(category, payload):
    """Plain-text Telegram body for a category. Never raises."""
    repo = _repo(payload)
    if category == "errors":
        err = payload.get("error") or "error"
        det = payload.get("error_details") or ""
        head = f"🛑 flywheel · turn failed\nerror: {err}"
        if det:
            head += f" ({_clip(det, 120)})"
        tail = _clip(payload.get("last_assistant_message"), 300)
        return f"{head}\nrepo: {repo}" + (f"\n{tail}" if tail else "")
    if category == "waiting":
        msg = _clip(payload.get("message"), 300) or "agent is waiting for you"
        ntype = payload.get("notification_type")
        line = f"🔔 flywheel · needs you\n{msg}"
        if ntype:
            line += f"\n[{ntype}]"
        return f"{line}\nrepo: {repo}"
    if category == "completions":
        reason = payload.get("reason") or "session ended"
        body = f"✅ flywheel · run ended\nrepo: {repo}\n{reason}"
        hb = _heartbeat_tail(payload)
        return body + (f"\n{hb}" if hb else "")
    if category == "dispatch":
        report = _clip(payload.get("report"), 500) or "dispatch fired"
        return f"🏭 flywheel · dispatch\nrepo: {repo}\n{report}"
    return f"flywheel · {category}\nrepo: {repo}"


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
