# Vendored: herdr-pm ops kit

`pm.py` and `resolve_ids.py` are vendored **verbatim** from
[yigitkonur/herdr-pm](https://github.com/yigitkonur/herdr-pm)
(`skills/herdr-pm-agent/scripts/`), MIT-licensed — see `LICENSE-herdr-pm`.

- Upstream commit: `b87f5048ac1f341def55eafab43028c283947334`
- Local edits: one functional change — the `STATE_ROOT` constant leaf changed
  from `herdr-pm` to `pg-dispatch` (plus its explanatory comment) so PAUSE +
  state live in this plugin's namespace (`~/.local/state/pg-dispatch/`).
  `pm.py` uses `STATE_ROOT` only for the PAUSE file and the `capabilities`
  report, so the change is functionally inert. Everything else is
  byte-identical to upstream.

**Do not hand-edit these scripts.** To pick up upstream fixes, re-vendor
(re-run the fetch from the implementation plan) and re-apply the single
`STATE_ROOT` edit.

## Subcommands the dispatch brain uses

`capabilities`, `spawn-exec`, `dispatch`, `read`, `keys`, `lanes`, `status`,
`notify` (and optionally `review`). The remaining subcommands
(`await`, `tail`, `diagnose`, `label`) ship unused — they are harmless and
kept so the file stays byte-identical to upstream.

## Confirmed flag surface (herdr client 0.6.10, protocol 13)

Live-introspected on this machine; `herdr-mode.md` references these verbatim.
All three require `--term` = the orchestrator's own pane id (`$HERDR_PANE_ID`).

```
spawn-exec  --term TERM [--session S] --slug SLUG [--branch BRANCH]
            [--base BASE] [--reuse] [--cwd CWD]
            [--backend {claude,codex,hermes,pi}] [--label LABEL]
dispatch    --term TERM [--session S] [--text TEXT] [--file FILE]
            [--marker MARKER] [--dry-run] [--clear-stray]
            [--confirm-secs N] [--force]
lanes       --term TERM [--session S] [--branch-prefix PREFIX]   # we pass goal/
```

**No `--model` flag on `spawn-exec`.** The backend is launched by name only
(`claude --dangerously-skip-permissions`), so `config.model` cannot be set at
spawn. When `config.model != inherit`, the brain sends `/model <alias>` into
the fresh pane (a `dispatch --text "/model <alias>"`) **before** the `/goal`
dispatch.

**`capabilities` server-state handling.** With the herdr server stopped,
`capabilities` returns `ok:false` + `server.running:false` (client/protocol
still reported). The brain treats `ok:false`/`server.running:false` as the
degrade-to-native trigger. A true live run (T11) needs the server up
(`herdr server`, or an interactive `herdr` session).
