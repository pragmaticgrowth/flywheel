---
name: telegram-message
description: Use when the user runs "/telegram-message", gives a Telegram bot token + chat id, or wants Telegram alerts for flywheel dispatch/loop runs — a DM when a run hits an error/usage limit, waits on the user (permission/idle), or finishes. Also use to enable, disable, test, or check the status of those alerts. Sets up notifications; never implements goals.
---

# Telegram Message — flywheel notifications

**CLI support**: **Claude Code only** (for now). Detect your runtime: if
Droid-specific tools (`CronCreate`, `CreateAutomation`) are available or
`$DROID_PLUGIN_ROOT` is set, you are in Droid — in that case tell the user this
skill's notifications aren't available on Droid yet and why (see "Droid: not
supported yet" below), then stop rather than writing config that can't fire.

Wire a Telegram bot so an autonomous `/dispatch` or `/loop` run tells the owner
the moment it needs a human — an API/usage-limit error killed a turn, the agent
is waiting on a permission prompt, or the queue drained. One-time setup writes a
local, chmod-600 credentials file; the plugin's hooks (shipped dormant) then
call the notifier on the right events. **This skill only sets up notifications —
it never claims goals or implements work.**

## Invocation

- `/telegram-message <bot_token> [chat_id]` — set up (or update) notifications.
- `/telegram-message test` — send a test message with the saved config.
- `/telegram-message off` / `on` — flip `enabled` without losing the token.
- `/telegram-message status` — show what's configured (token redacted).

If the user typed only `/telegram-message` with no token and none is saved,
explain the two things they need and how to get them (below), then stop.

## What the user needs first

- **Bot token** — from @BotFather in Telegram: `/newbot`, follow prompts, copy
  the `123456789:ABC...` token.
- **Chat id** — the destination. If the user doesn't have it, they message their
  new bot once, then this skill reads it from `getUpdates` (step 3).

## Setup flow

Run these yourself (the token is a secret — see Security; never print it in full,
never write it into any repo file):

1. **Parse args.** First token-looking arg → `bot_token`; a bare numeric/`-`
   arg → `chat_id`. Recognize the verbs (`test`/`off`/`on`/`status`) instead.
2. **Validate the token:**
   `curl -sS "https://api.telegram.org/bot<token>/getMe"` → expect `.ok == true`;
   show `.result.username`. On `ok:false` / 401, report an invalid token and stop.
3. **Resolve chat id.** If given, use it. If missing:
   `curl -sS "https://api.telegram.org/bot<token>/getUpdates"` and read
   `.result[].message.chat.id`. If empty, tell the user to send any message to
   the bot, then re-run. If several chats appear, show them and ask which.
4. **Write the config** to `~/.local/state/pg-telegram/config.json`
   (`mkdir -p` the dir, then `chmod 600` the file). Write it with a real JSON
   writer (a `python3 - <<'PY'` heredoc), not string-concatenation, so the token
   is never echoed to the terminal:

   ```json
   { "enabled": true, "bot_token": "…", "chat_id": "…",
     "events": { "errors": true, "waiting": true, "completions": true },
     "only_cwd": null, "min_interval_seconds": 0 }
   ```

   Preserve an existing file's `events`/`only_cwd`/`min_interval_seconds` on an
   update; only overwrite token/chat_id/enabled.
5. **Send a test message:**
   `curl -sS "https://api.telegram.org/bot<token>/sendMessage" -d chat_id=<id> --data-urlencode "text=✅ flywheel notifications are wired to this chat."`
   Confirm the user sees it. If the send fails, surface the Telegram error.
6. **Ensure the hooks are live** for the runtime (below).
7. **Report:** which events are on, where the config lives, how to disable, and
   the security note. Do NOT print the token.

## Hook wiring (Claude Code)

The hooks ship in the plugin's `hooks/hooks.json` and auto-register when flywheel
is enabled — nothing to write. Confirm they're active by noting the user can run
`/hooks` to see `StopFailure`, `Notification`, and `SessionEnd` entries pointing
at the notifier `pg_telegram_notify.py`. If the user disabled all hooks
(`disableAllHooks`), say so — notifications can't fire. (The notifier's path in
those entries resolves via `${CLAUDE_PLUGIN_ROOT}`, set automatically when the
plugin runs the hook.)

## What fires when (set expectations)

- **errors** → `StopFailure` (rate_limit, billing_error, authentication_failed,
  overloaded, server_error, …). **Verified firing in unattended `claude -p`
  runs** — the usage-limit / API-error signal that matters for `/loop /dispatch`:
  a subscription 5-hour/weekly limit killing a headless turn surfaces as the
  `rate_limit` error type. (The interactive between-turns limit *banner* fires no
  hook at all — another reason unattended drains belong on the external-scheduler
  model, where every fire is a turn that can die loudly.)
- **waiting** → `Notification` (permission prompt, idle, needs-input). The ping
  fires when the prompt APPEARS — i.e. while the agent waits on you, one per
  prompt, not on your approval action. Interactive sessions only; a headless `-p`
  run aborts rather than prompting, so don't expect waiting pings from unattended
  runs.
- **completions** → `SessionEnd` (a run/session ended; verified firing in `-p`).
  For the limit-proof external-scheduler model (`loop-architect` Step 5: fresh
  `claude -p "/dispatch"` per fire) this pings once per fire; for an in-session
  `/loop` it pings when the session itself ends. Best-effort: the message appends
  the newest dispatch heartbeat line (e.g. `8/8 · drained yes`) when present.

## Droid: not supported yet

Do NOT set up notifications on Droid — say why and stop. Two blockers, verified
2026-07-07: (1) Droid's hook system has **no error/rate-limit event** at all, and
(2) Droid hooks **do not fire under `droid exec` / `CronCreate`** (tested with
trivial `SessionStart`/`Stop`/`SessionEnd` hooks at both project and user scope —
none fired), which is exactly how the flywheel factory runs unattended on Droid.
So hook-based alerts can't serve the Droid use case. A future hook-free path
(dispatch calling the notifier directly at Phase 4) is deferred — see the design
doc `docs/superpowers/specs/2026-07-07-telegram-message-design.md`.

## Config & management

`~/.local/state/pg-telegram/config.json` (chmod 600):
- `enabled` — master switch (`/telegram-message off|on`).
- `events.{errors,waiting,completions}` — per-category toggles.
- `only_cwd` — set to a path prefix to notify only for one repo (default: all).
- `min_interval_seconds` — anti-flood throttle per category (default 0 = off).
Edit the file directly or re-run the skill. To remove entirely: delete the file.

## Security

- The token lives ONLY in the chmod-600 state file, read at runtime — never in
  `hooks.json`, a tracked file, or a message body. Never commit it; never print
  it in full (mask to the last 4 chars in any status output).
- The setup `curl`/args land in this session's LOCAL transcript. That's local
  only; if it matters, the user can rotate the token via @BotFather.
- The notifier sends the repo (cwd basename) + the hook's own message text to
  Telegram's servers — inherent to the feature; no file contents, no token.

## Relationship to the other skills

- `loop-architect` Step 5 (usage-limit proofing) recommends the external
  scheduler that makes `completions`/`errors` pings most useful.
- `dispatch` surfaces blockers under needs-you and writes the heartbeat this
  skill reads for completion messages.
- This skill never claims goals, spawns implementers, or merges — that's
  `dispatch`.
