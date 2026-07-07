# telegram-message — flywheel Telegram notifications (design)

**Date:** 2026-07-07 · **Ships as:** flywheel v4.11.0 · **Status:** approved, pre-implementation

## Problem

An autonomous `/dispatch` or `/loop` run stops for reasons a human must
notice: it hit a subscription usage limit, an API/billing/auth error killed the
turn, the agent is waiting on a permission prompt, or the queue drained. Today
nothing tells the owner — they discover a stalled factory hours later. We want a
Telegram DM the moment a run errors, waits, or finishes, set up with one command
and no per-repo wiring.

## Owner decisions (2026-07-07)

- **Home:** inside the **flywheel** plugin (not a separate marketplace plugin).
  This ends flywheel's "skills-only / no hooks" invariant — recorded here and in
  CLAUDE.md/README as a deliberate owner decision, so the docs don't contradict
  the code.
- **Notify on:** errors + agent-waiting + completions (not just hard errors).
- **Permission pings:** ping on all actionable prompts, interactive included.
- **CLIs:** both Claude Code and Droid.

## Confirmed mechanics (research 2026-07-07; CLI 2.1.202)

### Claude Code — fully confirmed, `StopFailure` live-tested
- **Plugin-shipped hooks:** `hooks/hooks.json` at plugin root auto-registers when
  the plugin is enabled (no user settings edit). Hook `command` supports
  `"${CLAUDE_PLUGIN_ROOT}"` (quote it). Do NOT persist state under the plugin
  root — it changes on every update; our state lives in `~/.local/state`.
- **`StopFailure`** fires when a turn ends on an API error — **verified firing in
  headless `claude -p`** (the unattended-dispatch case), process exit 1. Stdin
  fields: `error` (NOT `error_type`), values `rate_limit | overloaded |
  authentication_failed | oauth_org_not_allowed | billing_error | invalid_request
  | model_not_found | server_error | max_output_tokens | unknown`; plus
  `error_details`, `last_assistant_message` (the rendered API-error string here).
  Matcher is **exact-match, `|`-only** — never commas/spaces for this event.
  Output/exit ignored (pure side effect).
- **`Notification`** stdin: `message`, optional `title`, `notification_type`
  (the matcher field), values `permission_prompt | idle_prompt | auth_success |
  elicitation_dialog | elicitation_complete | elicitation_response |
  agent_needs_input | agent_completed`. `agent_needs_input`/`agent_completed`
  fire **only** with the terminal agent view open; `permission_prompt`/
  `idle_prompt` are interactive-oriented and generally do **not** fire in
  one-shot `-p` (headless aborts instead of prompting). So Notification is the
  interactive-session signal; StopFailure is the unattended signal.
- **`SessionEnd`** fires when the session ends; `reason` ∈ `clear | resume |
  logout | prompt_input_exit | bypass_permissions_disabled | other`. Used for
  "run finished." (Verify `-p` firing empirically in build — low risk.)
- **Common fields:** `session_id`, `prompt_id`, `transcript_path`, `cwd`,
  `permission_mode` (not on every event), `effort`, `hook_event_name`. **No
  project/goal field** — derive from `cwd` (basename) and, best-effort, the
  dispatch heartbeat at `~/.local/state/pg-dispatch/<cwd-basename>/heartbeat`.
- **Timeout:** command hooks default 600s — a slow curl won't hang the session.
- A native `type:"http"` hook exists but can't shape Telegram's `chat_id`/`text`
  body, so we use `type:"command"` → our script.

### Droid — partial, two unknowns to verify empirically
- Hooks live in `~/.factory/hooks.json` (user) / `.factory/hooks.json` (project),
  same JSON schema. `${CLAUDE_PLUGIN_ROOT}` is a **documented alias** for
  `${DROID_PLUGIN_ROOT}` — our dual-resolution is correct.
- 9 events incl. `Notification` (permission-needed + 60s idle → `message`),
  `Stop`, `SessionEnd` (`reason`). **No error/rate-limit event exists** — Droid
  error/limit pings are **impossible via hooks**; documented as a platform gap,
  not coded around.
- **Unknown A:** does a `.claude-plugin`-format plugin's `hooks/hooks.json`
  survive Droid's translation and fire? **Unknown B:** do hooks fire under
  `droid exec` / cron. Both cheap to test; verify in build. Fallback if A fails:
  the setup skill merges hook entries into `~/.factory/hooks.json`.

## Architecture — 4 new files under flywheel

```
hooks/hooks.json                                          # plugin hook bundle (both CLIs)
skills/telegram-message/SKILL.md                          # /telegram-message setup skill
skills/telegram-message/scripts/pg_telegram_notify.py     # stdlib notifier (never-crash)
skills/telegram-message/scripts/test_pg_telegram_notify.py# tests (dry-run, no network)
```

### 1. `hooks/hooks.json`
One bundle, three groups, each calling the notifier with a category argv. Droid
ignores the `StopFailure` group (no such event); the other two work on both CLIs
if Droid translation holds.

```json
{
  "description": "flywheel Telegram notifications — pings a bot on errors, agent-waiting, and completion. No-ops until /telegram-message is run.",
  "hooks": {
    "StopFailure": [
      { "matcher": "rate_limit|overloaded|authentication_failed|oauth_org_not_allowed|billing_error|invalid_request|model_not_found|server_error|max_output_tokens|unknown",
        "hooks": [ { "type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/telegram-message/scripts/pg_telegram_notify.py\" errors" } ] }
    ],
    "Notification": [
      { "matcher": "permission_prompt|idle_prompt|agent_needs_input|elicitation_dialog",
        "hooks": [ { "type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/telegram-message/scripts/pg_telegram_notify.py\" waiting" } ] }
    ],
    "SessionEnd": [
      { "hooks": [ { "type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/telegram-message/scripts/pg_telegram_notify.py\" completions" } ] }
    ]
  }
}
```
(Enumerate the StopFailure error values explicitly rather than an empty
match-all, so the matcher stays on the exact-match path the event requires.)

### 2. `pg_telegram_notify.py` — the notifier
- **Signature:** `python3 pg_telegram_notify.py <category>` where category ∈
  `errors | waiting | completions`. Reads the hook JSON from **stdin**.
- **Pure stdlib** (`json`, `urllib.request`, `os`, `sys`, `time`) — no pip deps.
- **Never disrupts a session:** every path exits 0; all logic wrapped so a
  malformed stdin, missing config, or network error is swallowed (optional debug
  line to `~/.local/state/pg-telegram/notify.log`).
- **No-op contract:** if the config file is absent, `enabled` is false, or
  `bot_token`/`chat_id` missing → exit 0 with no output and no network call. This
  is what makes shipping dormant hooks safe.
- **Steps:** load config → check `events[<category>]` toggle → optional `only_cwd`
  prefix filter on stdin `cwd` → optional `min_interval_seconds` throttle (per
  category, timestamp file in state dir) → compose message → POST to
  `https://api.telegram.org/bot<token>/sendMessage` with `chat_id` + `text`
  (plain text, **no `parse_mode`** — error strings contain markdown-breaking
  chars), `urllib` timeout 8s.
- **Messages (plain text):**
  - errors: `🛑 flywheel · turn failed` / `error: <error> (<error_details>)` /
    `repo: <cwd basename>` / `<last_assistant_message truncated ~300 chars>`
  - waiting: `🔔 flywheel · needs you` / `<message>` / `repo: <cwd basename>`
  - completions: `✅ flywheel · run ended` / `repo: <cwd basename>` /
    `<SessionEnd reason>` / best-effort newest dispatch heartbeat line if present.
- **Testability:** `PG_TELEGRAM_DRYRUN=1` prints the composed request (URL with
  token redacted + body) to stdout instead of POSTing — lets tests assert shape
  with no network.

### 3. `SKILL.md` — `/telegram-message <bot_token> <chat_id>`
Agent-driven setup (CLI-aware per flywheel convention). Verbs: bare setup,
`off`, `on`, `test`, `status`. Setup flow:
1. Parse args; if no token, explain BotFather bot creation and stop.
2. Validate token: `getMe` → show bot username; fail clearly on `ok:false`.
3. Resolve `chat_id`: use the arg, else `getUpdates` to help the user pick it
   (prompt them to message the bot first).
4. Write `~/.local/state/pg-telegram/config.json` (`mkdir -p`, **chmod 600**),
   `enabled:true`, all three event toggles true, filters off. **Never** echo the
   full token or write it into any repo file.
5. Send a test message → confirm delivery.
6. Ensure hooks live for the runtime: Claude Code — bundled with the plugin
   (verify present, mention `/hooks`); Droid — verify translation fired, else
   merge entries into `~/.factory/hooks.json` (fallback).
7. Tell the user: how to disable (`/telegram-message off` or `enabled:false`),
   where config lives, and the security note (local, chmod 600, not in repo;
   token also in the local transcript — rotate via BotFather if needed).

### 4. Tests
`test_pg_telegram_notify.py`, dry-run, no network, following the
`doctor_checks` self-contained-import pattern:
- no-op when config missing / `enabled:false` / no token.
- malformed / empty stdin → no crash, exit 0.
- message shape per category (errors/waiting/completions) contains the right
  markers and the event detail.
- `only_cwd` filter suppresses off-scope cwd.
- category toggle off → no-op.
- dry-run output **redacts the token**.

## Config schema
`~/.local/state/pg-telegram/config.json` (chmod 600, outside the repo):
```json
{ "enabled": true, "bot_token": "…", "chat_id": "…",
  "events": { "errors": true, "waiting": true, "completions": true },
  "only_cwd": null, "min_interval_seconds": 0 }
```

## Secret safety
- Token only in the chmod-600 state file, read at runtime — never in `hooks.json`,
  a tracked file, or the message body. The repo's pre-push secret hook is the
  backstop.
- The `/telegram-message <token>` args persist in the local session transcript
  (local only) — documented; rotate via BotFather if sensitive.
- The notifier sends `cwd` basename + hook message text to Telegram's servers —
  inherent to the feature; the owner opts in. No token, no file contents beyond
  the hook's own message.

## Out of scope (v1 / YAGNI)
- Per-goal pings (completions = whole-run `SessionEnd`, aligning with the
  fresh-session-per-fire limit-proof model). A future enhancement: dispatch
  Phase 4 calls the notifier directly on complete/block.
- No `Stop`-every-turn hook (spam, not "completion").
- No factory-doctor "telegram configured?" probe in v1 (candidate follow-up).
- Throttle/`only_cwd` ship present-but-off.

## Verification plan (build)
- Notifier unit tests green (dry-run).
- Empirical: register the real hooks locally, force a `StopFailure`
  (`claude -p` with a bogus model) → confirm a Telegram test send fires; confirm
  `SessionEnd` fires in `-p`. Droid: install and test unknowns A/B if the `droid`
  CLI is available; otherwise document as verify-on-Droid.
- Local gate: `python3 test_pg_telegram_notify.py`, manifest JSON valid, AGENTS.md
  symlink intact.

## Release
plugin.json 4.10.0 → **4.11.0**; CHANGELOG entry; README + site skill card +
version pill/title; CLAUDE.md (skills-only → skills+hooks owner decision, new
skill in list + structure); tag `v4.11.0`; GitHub release; `wrangler deploy`;
push; note `/plugin marketplace update pragmatic-growth`.
