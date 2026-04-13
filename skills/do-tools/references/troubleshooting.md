# Troubleshooting — empirical findings

Each entry: symptom, cause, fix. All verified empirically.

## MCP server not responding

**Symptom:** `mcp__mcp-do__do_list_models` or any tool returns "server not found" or times out.

**Cause:** The MCP server process isn't running or crashed.

**Fix:**
1. Check if `mcp-do` binary is on PATH: `which mcp-do`
2. Try rebuilding: `cd /Users/serkan/mcp-do && npm run build`
3. Verify in Claude Code: the MCP server should auto-restart on next tool call
4. Check `~/.claude.json` for the user-scope registration

## `droid exec` returns exit code 1 with empty output

**Symptom:** A `do_*` tool with `provider: "droid"` fails silently — `ok: false` but no useful error message.

**Cause:** Usually `stream-json` output format producing error events that exit code 0 wouldn't surface. The mcp-do parser detects these.

**Fix:**
1. Check the `error_message` field in the response
2. Common causes: model not found (typo in model name), profile file missing, `FACTORY_API_KEY` expired
3. Run `do_list_models` to verify the model exists

## `opencode run` fails with "command not found"

**Symptom:** A `do_*` tool with `provider: "opencode"` returns spawn error.

**Cause:** `opencode` binary not on PATH or not installed.

**Fix:**
1. Install: `curl -fsSL https://opencode.ai/install | bash`
2. Or set `OPENCODE_BIN` env var to the full path
3. The server also checks `~/.opencode/bin/opencode` as a fallback

## Model "402 Payment Required" or similar billing error

**Symptom:** Tool call fails with a payment/billing error in the droid output.

**Cause:** You're using a factory built-in model (`claude-opus-4-6`, `gpt-5.4`, etc.) instead of a custom BYOK model.

**Fix:** Only use custom models: `custom:glm-5-turbo`, `custom:MiniMax-M2.7`, `custom:glm-5.1`, `custom:VP-GPT-5.4-Mini-48`, etc. The presets already default to custom models — only override with custom ids.

## Session list is incomplete

**Symptom:** `do_session_list` returns fewer sessions than expected. Sessions you created via MCP tools are missing.

**Cause:** `~/.factory/sessions-index.json` is incomplete — droid's indexer skips sessions created via `droid exec` (which is how mcp-do creates every session).

**Fix:** Pass `scan_disk: true` to `do_session_list` for the authoritative list. This walks `~/.factory/sessions/<dir>/*.jsonl` directly (~200-400ms for ~200 sessions).

## Cross-review has only 1-2 models responding

**Symptom:** `do_cross_review` returns results from fewer than 3 models.

**Cause:** One or more models failed (timeout, billing, model unavailable). The tool uses `Promise.allSettled` so partial results are still returned.

**Fix:** Check which model(s) failed in the response. Common causes:
- Model timeout (increase `timeout_ms`, default is 240s)
- Model not configured in the provider (run `/do:setup` to check)
- Transient API error (retry)

## Provider "opencode" returns garbled output

**Symptom:** Review or research results contain ANSI escape sequences or opencode UI chrome.

**Cause:** `NO_COLOR=1` env var not being set, or opencode version changed its output format.

**Fix:** The `cleanOpencodeOutput()` function in `src/opencode/exec.ts` strips ANSI and UI chrome. If new patterns appear, the regex may need updating.

## Timeout on large codebases

**Symptom:** `do_explore` or `do_review` times out on large repos.

**Fix:** Increase `timeout_ms` (default varies: 600s for droid, 240s for opencode). For very large codebases, scope the prompt to specific directories or files instead of the whole repo.
