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

def test_compose_errors_includes_error_and_repo():
    payload = {"cwd": "/repos/myapp", "error": "rate_limit",
               "error_details": "429 Too Many Requests",
               "last_assistant_message": "API Error: Rate limit reached"}
    msg = ptn.compose_message("errors", payload)
    assert "rate_limit" in msg
    assert "myapp" in msg
    assert "429" in msg
    assert "flywheel" in msg


def test_compose_waiting_includes_message_text():
    payload = {"cwd": "/repos/myapp", "message": "Claude needs your permission",
               "notification_type": "permission_prompt"}
    msg = ptn.compose_message("waiting", payload)
    assert "Claude needs your permission" in msg
    assert "myapp" in msg


def test_compose_completions_includes_reason_and_repo():
    payload = {"cwd": "/repos/myapp", "reason": "prompt_input_exit"}
    msg = ptn.compose_message("completions", payload)
    assert "myapp" in msg
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


if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")
