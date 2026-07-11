---
name: telegram-message
description: Use when the user runs "/telegram-message", gives a Telegram bot token + chat id, or wants Telegram alerts for flywheel dispatch/loop runs — a DM when a run hits an error/usage limit, waits on the user (permission/idle), finishes, or a dispatch fire reports. Also use to enable, disable, test, scope (per-project/global), or check the status of those alerts. Sets up notifications; never implements goals.
---

# Telegram Message — flywheel notifications

It delivers the full hook set — errors, waiting, and completions — plus
dispatch pings.

Wire a Telegram bot so an autonomous `/dispatch` or `/loop` run tells the owner
the moment it needs a human — an API/usage-limit error killed a turn, the agent
is waiting on a permission prompt, or the queue drained. One-time setup writes a
local, chmod-600 credentials file; the plugin's hooks (shipped dormant) then
call the notifier on the right events. Hook pings are **dispatch-gated by
default** (v4.14): they fire only around a live dispatch run in that repo, so
ordinary interactive sessions — idle prompts, plan questions, teammate blips —
never spam the chat (see "What fires when"). **This skill only sets up notifications —
it never claims goals or implements work.**

## Invocation

- `/telegram-message <bot_token> [chat_id]` — set up (or update) notifications
  for **this project** (the default scope — see Scopes).
- `/telegram-message <bot_token> [chat_id] --global` — machine-wide fallback
  config instead (used for any project without its own).
- `/telegram-message test` — send a test message with the resolved config.
- `/telegram-message off` / `on` — flip `enabled` on the resolved scope
  (project config if this project has one, else global) without losing the token.
- `/telegram-message status` — show which config resolves for this project and
  what's in it (token redacted).

If the user typed only `/telegram-message` with no token and none is saved,
explain the two things they need and how to get them (below), then stop.

## Scopes — personal settings, never in the repo

Telegram credentials are PERSONAL settings, so no scope ever writes a file
inside the project: there is nothing to gitignore and nothing that can be
committed or pushed, even in a public repo.

- **Project scope (default):** `~/.local/state/pg-telegram/projects/<slug>.json`
  where `<slug>` is the project root's absolute path with `/` → `-` (e.g.
  `-Users-me-myrepo.json`). The file carries a `project_root` field (the repo
  root at setup time — `git rev-parse --show-toplevel`, else the cwd); the
  notifier picks the config whose `project_root` is the longest prefix of the
  event's `cwd`. Different projects → different bots/chats/toggles; a project
  config with `"enabled": false` silences ONLY that project (explicit opt-out —
  it does not fall through to global).
- **Global scope (`--global`):** `~/.local/state/pg-telegram/config.json` — the
  fallback for any project without its own config.
- **Cloud/env scope:** `PG_TELEGRAM_BOT_TOKEN` + `PG_TELEGRAM_CHAT_ID` env vars
  beat both files — for cloud runs (routines and other environments) where no
  state file persists. See "Cloud".

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
4. **Write the config** to the scope's file (Scopes above): project scope →
   `~/.local/state/pg-telegram/projects/<slug>.json` with `project_root` set;
   `--global` → `~/.local/state/pg-telegram/config.json`. Either way `mkdir -p`
   the dir, then `chmod 600` the file. Write it with a real JSON writer (a
   `python3 - <<'PY'` heredoc), not string-concatenation, so the token is never
   echoed to the terminal:

   ```json
   { "enabled": true, "bot_token": "…", "chat_id": "…",
     "project_root": "/abs/path/to/repo",
     "events": { "errors": true, "waiting": true, "completions": true, "dispatch": true },
     "only_cwd": null, "min_interval_seconds": 0 }
   ```

   (`project_root` only in project-scope files.) Preserve an existing file's
   `events`/`only_cwd`/`min_interval_seconds`/`gate_on_dispatch` on an update;
   only overwrite token/chat_id/enabled.
5. **Send a test message** — lead with the PROJECT name (several projects may
   share one chat; the project is always the headline of every notification):
   `curl -sS "https://api.telegram.org/bot<token>/sendMessage" -d chat_id=<id> --data-urlencode "text=✅ <project-dir-name> · notifications wired to this chat"`
   Confirm the user sees it. If the send fails, surface the Telegram error.
6. **Ensure the hooks are live** for the runtime (below).
7. **Report:** which events are on, where the config lives, how to disable, and
   the security note. Do NOT print the token.

## Hook wiring

The hooks ship in the plugin's `hooks/hooks.json` and auto-register when flywheel
is enabled — nothing to write. Confirm they're active by noting the user can run
`/hooks` to see `StopFailure`, `Notification`, and `SessionEnd` entries pointing
at the notifier `pg_telegram_notify.py`. If the user disabled all hooks
(`disableAllHooks`), say so — notifications can't fire. (The notifier's path in
those entries resolves via `${CLAUDE_PLUGIN_ROOT}`, set automatically when the
plugin runs the hook.)

## What fires when (set expectations)

Every message headline reads `<emoji> <project> · <session> · <event>` — the
session label is the session's name (a `/rename`, or Claude Code's derived
name, resolved from the live-session registry at `~/.claude/sessions/`), else
the session id's first 8 chars. That's how several sessions on one project stay
distinguishable in one chat. Dispatch pings carry no session id (plaintext
pipe), so their headline is just `<project> · dispatch`. Heartbeat lines are
shown without their timestamp — Telegram already shows arrival time.

**Dispatch-context gate (default since v4.14).** The three hook categories fire
only in dispatch context; the `dispatch` category itself is never gated. The
notifier reads two per-repo signals from `~/.local/state/pg-dispatch/<slug>/`:
- **waiting** needs a LIVE fire — the `active` marker dispatch writes at fire
  start and removes at fire end. A loop session idling between fires, an
  interactive session waiting on your answer, or an elicitation dialog in
  ordinary work never pings; a permission prompt stalling a live fire does.
- **errors** and **completions** accept the marker OR a heartbeat younger than
  4 h — so a wakeup turn dying to a usage limit *before* the fire writes its
  marker still pings, and the run-ended ping still lands after the last fire
  cleaned up. Anything older than 4 h counts as no context.
The gate is per-REPO, not per-session (skills can't see their session id): an
interactive session in a repo whose factory is mid-fire can still ping — rare,
and it concerns the repo being watched anyway. Set `"gate_on_dispatch": false`
on a scope to restore fire-always hooks (e.g. for generic non-dispatch
unattended loops); the env-var cloud scope is always ungated —
`PG_TELEGRAM_EVENTS` is its narrowing knob.

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
  runs. Gated: pings only while a dispatch fire is live in that repo (above).
- **completions** → `SessionEnd` (a run/session ended; verified firing in `-p`).
  For the limit-proof external-scheduler model (`loop-architect` Step 5: fresh
  `claude -p "/dispatch"` per fire) this pings once per fire; for an in-session
  `/loop` it pings when the session itself ends. Best-effort: the message appends
  the newest dispatch heartbeat line (e.g. `8/8 · drained yes`) when present.
- **dispatch** → not a hook: the dispatch orchestrator pipes its Phase 4 report
  line straight to the notifier every fire (`🏭` ping with the
  `<done>/<total> · needs-you` line). Works in Claude Code and in cloud runs,
  because it's a plain script call. Configs written before v4.12.0 lack the
  `dispatch` toggle — re-run setup (or add `"dispatch": true` to `events`) to
  enable it.

## Cloud

- **Cloud (routines, or any env where `~/.local/state` doesn't persist):** set
  `PG_TELEGRAM_BOT_TOKEN` and `PG_TELEGRAM_CHAT_ID` in the routine's environment
  config — the notifier prefers them over any file, no setup file needed. Narrow
  categories with `PG_TELEGRAM_EVENTS=errors,dispatch` (comma list; default all).

## Config & management

Project files `~/.local/state/pg-telegram/projects/<slug>.json` + global
`~/.local/state/pg-telegram/config.json` (all chmod 600). Resolution: env vars →
longest-`project_root`-prefix project file → global; `enabled:false` in a
project file silences that project outright. Fields:
- `enabled` — the scope's switch (`/telegram-message off|on`).
- `events.{errors,waiting,completions,dispatch}` — per-category toggles.
- `gate_on_dispatch` — default `true` (key absent = on): hook categories fire
  only in dispatch context (see "What fires when"). `false` restores
  fire-always hooks for that scope. Per-SCOPE, and a project file beats global:
  to ungate a whole machine, set it in the global config AND in every project
  file that exists.
- `project_root` — project files only; the prefix the notifier matches on.
- `only_cwd` — global-config-era repo filter (project scope supersedes it).
- `min_interval_seconds` — anti-flood throttle per category (default 0 = off).
Edit a file directly or re-run the skill. To remove a scope: delete its file.

## Security

- The token lives ONLY in chmod-600 state files (or cloud env config), read at
  runtime — never in `hooks.json`, a tracked file, or a message body. Every
  scope's file is OUTSIDE the repo, so per-project settings can never be
  committed or pushed. Never print the token in full (mask to the last 4 chars
  in any status output).
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
