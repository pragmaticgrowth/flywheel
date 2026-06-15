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
