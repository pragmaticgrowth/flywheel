"""Tests for pg_telegram_notify.py — the flywheel Telegram notifier.

Network-free: everything runs through dry-run mode (compose() returns the
message + a redacted request instead of POSTing), plus direct calls to the
pure helpers. Run: python3 test_pg_telegram_notify.py  (or pytest)."""
import importlib.util, os, io, json, tempfile, sys

_here = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location(
    "ptn", os.path.join(_here, "pg_telegram_notify.py"))
ptn = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ptn)


# ---- config loading / no-op contract ----

def _cfg(**over):
    base = {"enabled": True, "bot_token": "123:ABCDEF", "chat_id": "9",
            "events": {"errors": True, "waiting": True, "completions": True},
            "only_cwd": None, "min_interval_seconds": 0}
    base.update(over); return base


def test_load_config_missing_returns_none():
    with tempfile.TemporaryDirectory() as d:
        assert ptn.load_config(os.path.join(d, "nope.json")) is None


def test_load_config_reads_json():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.json")
        json.dump(_cfg(), open(p, "w"))
        assert ptn.load_config(p)["chat_id"] == "9"


def test_load_config_malformed_returns_none():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.json")
        open(p, "w").write("{not json")
        assert ptn.load_config(p) is None


def test_should_send_true_when_enabled_and_toggle_on():
    ok, why = ptn.should_send(_cfg(), "errors", {"cwd": "/x"})
    assert ok, why


def test_should_send_false_when_disabled():
    ok, _ = ptn.should_send(_cfg(enabled=False), "errors", {"cwd": "/x"})
    assert not ok


def test_should_send_false_when_no_token():
    ok, _ = ptn.should_send(_cfg(bot_token=""), "errors", {"cwd": "/x"})
    assert not ok


def test_should_send_false_when_no_chat_id():
    ok, _ = ptn.should_send(_cfg(chat_id=""), "errors", {"cwd": "/x"})
    assert not ok


def test_should_send_false_when_category_toggle_off():
    cfg = _cfg(events={"errors": False, "waiting": True, "completions": True})
    ok, _ = ptn.should_send(cfg, "errors", {"cwd": "/x"})
    assert not ok


def test_should_send_unknown_category_defaults_off():
    ok, _ = ptn.should_send(_cfg(), "bogus", {"cwd": "/x"})
    assert not ok


def test_only_cwd_filter_suppresses_offscope():
    cfg = _cfg(only_cwd="/repos/site")
    off, _ = ptn.should_send(cfg, "errors", {"cwd": "/repos/other"})
    on, _ = ptn.should_send(cfg, "errors", {"cwd": "/repos/site/sub"})
    assert not off and on


# ---- message composition per category ----
# Multi-project chats: the PROJECT name must lead every message (first line),
# no plugin brand on line 1, no redundant repo: line.

def _first(msg):
    return msg.splitlines()[0]


def test_compose_errors_leads_with_project():
    payload = {"cwd": "/repos/myapp", "error": "rate_limit",
               "error_details": "429 Too Many Requests",
               "last_assistant_message": "API Error: Rate limit reached"}
    msg = ptn.compose_message("errors", payload)
    assert "myapp" in _first(msg)
    assert "rate_limit" in msg and "429" in msg
    assert "repo:" not in msg  # project is the headline, not a footnote


def test_compose_waiting_leads_with_project():
    payload = {"cwd": "/repos/myapp", "message": "Claude needs your permission",
               "notification_type": "permission_prompt"}
    msg = ptn.compose_message("waiting", payload)
    assert "myapp" in _first(msg)
    assert "Claude needs your permission" in msg


def test_compose_completions_leads_with_project():
    payload = {"cwd": "/repos/myapp", "reason": "prompt_input_exit"}
    msg = ptn.compose_message("completions", payload)
    assert "myapp" in _first(msg)
    assert "prompt_input_exit" in msg


def test_compose_truncates_long_assistant_message():
    payload = {"cwd": "/x", "error": "server_error",
               "last_assistant_message": "z" * 5000}
    msg = ptn.compose_message("errors", payload)
    assert len(msg) < 1500  # bounded, not dumping 5000 chars


def test_compose_missing_fields_no_crash():
    # empty payload must still produce a string, never raise
    for cat in ("errors", "waiting", "completions"):
        assert isinstance(ptn.compose_message(cat, {}), str)


# ---- dry-run request shape + token redaction ----

def test_dryrun_redacts_token(monkeypatch=None):
    cfg = _cfg(bot_token="7777777:SECRETTOKENVALUE")
    out = ptn.build_request(cfg, "hello world")
    # url carries the bot path but the secret must be redacted in the printable form
    printable = ptn.redact(out["url"])
    assert "SECRETTOKENVALUE" not in printable
    assert out["data"]["chat_id"] == "9"
    assert out["data"]["text"] == "hello world"


def test_build_request_targets_telegram_sendmessage():
    out = ptn.build_request(_cfg(), "x")
    assert "api.telegram.org" in out["url"]
    assert out["url"].endswith("/sendMessage")


# ---- end-to-end main() in dry-run: never crashes, respects no-op ----

def _run_main(stdin_text, category, config_path, dryrun=True):
    old_in, old_out = sys.stdin, sys.stdout
    old_env = os.environ.get("PG_TELEGRAM_DRYRUN")
    os.environ["PG_TELEGRAM_CONFIG"] = config_path
    if dryrun:
        os.environ["PG_TELEGRAM_DRYRUN"] = "1"
    sys.stdin = io.StringIO(stdin_text)
    sys.stdout = io.StringIO()
    try:
        rc = ptn.main([category])
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = old_in, old_out
        if old_env is None:
            os.environ.pop("PG_TELEGRAM_DRYRUN", None)
        else:
            os.environ["PG_TELEGRAM_DRYRUN"] = old_env


def test_main_noop_when_config_missing():
    with tempfile.TemporaryDirectory() as d:
        rc, out = _run_main('{"cwd":"/x","error":"rate_limit"}', "errors",
                            os.path.join(d, "none.json"))
        assert rc == 0 and out.strip() == ""


def test_main_malformed_stdin_no_crash():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.json"); json.dump(_cfg(), open(p, "w"))
        rc, _ = _run_main("{broken", "errors", p)
        assert rc == 0


def test_main_dryrun_emits_send_when_configured():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.json"); json.dump(_cfg(), open(p, "w"))
        rc, out = _run_main('{"cwd":"/repos/myapp","error":"billing_error"}',
                            "errors", p)
        assert rc == 0
        assert "billing_error" in out and "myapp" in out


def test_main_dryrun_noop_when_toggle_off():
    with tempfile.TemporaryDirectory() as d:
        cfg = _cfg(events={"errors": False, "waiting": True, "completions": True})
        p = os.path.join(d, "config.json"); json.dump(cfg, open(p, "w"))
        rc, out = _run_main('{"cwd":"/x","error":"rate_limit"}', "errors", p)
        assert rc == 0 and out.strip() == ""


# ---- v4.12.0: config resolution chain (env > project > global) ----

def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"))


def _state(d):
    # point the notifier's state dir at a temp dir for resolution tests
    os.environ["XDG_STATE_HOME"] = d
    os.environ.pop("PG_TELEGRAM_CONFIG", None)
    os.environ.pop("PG_TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("PG_TELEGRAM_CHAT_ID", None)


def test_resolve_env_creds_win_without_any_file():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        os.environ["PG_TELEGRAM_BOT_TOKEN"] = "1:ENVTOK"
        os.environ["PG_TELEGRAM_CHAT_ID"] = "77"
        try:
            cfg = ptn.resolve_config("/repos/anything")
            assert cfg and cfg["bot_token"] == "1:ENVTOK" and cfg["chat_id"] == "77"
            assert cfg["events"].get("dispatch")  # env path enables all categories
        finally:
            _state(d)


def test_resolve_project_longest_prefix_wins():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        pdir = os.path.join(d, "pg-telegram", "projects")
        _write(os.path.join(pdir, "a.json"),
               _cfg(chat_id="short", project_root="/repos"))
        _write(os.path.join(pdir, "b.json"),
               _cfg(chat_id="long", project_root="/repos/site"))
        cfg = ptn.resolve_config("/repos/site/src")
        assert cfg["chat_id"] == "long"


def test_resolve_project_optout_beats_global():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        _write(os.path.join(d, "pg-telegram", "config.json"), _cfg())
        _write(os.path.join(d, "pg-telegram", "projects", "x.json"),
               _cfg(enabled=False, project_root="/repos/quiet"))
        cfg = ptn.resolve_config("/repos/quiet")
        assert cfg["enabled"] is False  # explicit opt-out, no fallthrough to global


def test_resolve_falls_back_to_global():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        _write(os.path.join(d, "pg-telegram", "config.json"), _cfg(chat_id="glob"))
        cfg = ptn.resolve_config("/repos/other")
        assert cfg["chat_id"] == "glob"


def test_resolve_none_when_nothing_configured():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        assert ptn.resolve_config("/repos/x") is None


def test_explicit_config_env_still_wins_over_everything():
    with tempfile.TemporaryDirectory() as d:
        _state(d)
        p = os.path.join(d, "explicit.json"); _write(p, _cfg(chat_id="explicit"))
        os.environ["PG_TELEGRAM_CONFIG"] = p
        os.environ["PG_TELEGRAM_BOT_TOKEN"] = "1:ENVTOK"
        os.environ["PG_TELEGRAM_CHAT_ID"] = "77"
        try:
            cfg = ptn.resolve_config("/repos/x")
            assert cfg["chat_id"] == "explicit"
        finally:
            _state(d)


# ---- v4.12.0: dispatch category (hook-free direct notify) ----

def test_should_send_dispatch_toggle():
    cfg = _cfg(events={"errors": True, "waiting": True,
                       "completions": True, "dispatch": True})
    ok, _ = ptn.should_send(cfg, "dispatch", {"cwd": "/x"})
    assert ok
    cfg["events"]["dispatch"] = False
    ok, _ = ptn.should_send(cfg, "dispatch", {"cwd": "/x"})
    assert not ok


def test_compose_dispatch_leads_with_project():
    msg = ptn.compose_message("dispatch",
                              {"cwd": "/repos/myapp",
                               "report": "[dispatch] 6/8 done · blocked: 1 · needs-you: goal 004"})
    assert "myapp" in _first(msg)
    assert "6/8 done" in msg


def test_main_dispatch_accepts_plaintext_stdin():
    # dispatch pipes the raw report line — no JSON quoting hazards
    with tempfile.TemporaryDirectory() as d:
        cfg = _cfg(events={"errors": True, "waiting": True,
                           "completions": True, "dispatch": True})
        p = os.path.join(d, "config.json"); json.dump(cfg, open(p, "w"))
        rc, out = _run_main("[dispatch] 3/5 done · ready: 1 · blocked: 1",
                            "dispatch", p)
        assert rc == 0 and "3/5 done" in out


if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")
