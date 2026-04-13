# OpenCode Ecosystem Reference (v1.4)

Sources: [Ecosystem](https://opencode.ai/docs/ecosystem/), [Server](https://opencode.ai/docs/server), [SDK](https://opencode.ai/docs/sdk), [Plugins](https://opencode.ai/docs/plugins), [Config](https://opencode.ai/docs/config), [Modes](https://opencode.ai/docs/modes), [Commands](https://opencode.ai/docs/commands), [GitHub](https://opencode.ai/docs/github/), [IDE](https://opencode.ai/docs/ide/), [Providers](https://opencode.ai/docs/providers)

---

## Ecosystem Contents

**Everything on opencode.ai/docs/ecosystem is community-built.** The OpenCode CLI itself is by SST (github.com/anomalyco/opencode). The official surface is: the CLI, `@opencode-ai/sdk` (npm), `opencode serve` (HTTP server), and the GitHub App (github.com/apps/opencode-agent).

### Plugins (35 listed)

Distributed as npm packages or local JS/TS files. Configured in `opencode.json` under `"plugin": [...]`. Installed automatically via Bun at startup; local files go in `.opencode/plugins/` (project) or `~/.config/opencode/plugins/` (global). Plugins hook into events via a returned object of `{ "event.name": async handler }`. Available hooks include `session.idle`, `session.error`, `session.created`, `session.diff`, `session.compacted`, `tool.execute.before/after`, `permission.asked`, `message.updated`, `file.edited`, `shell.env`, `tui.prompt.append`, and 20+ others. Custom tools are defined via `tool()` helper with Zod schemas. Plugins can also inject custom context during session compaction via `experimental.session.compacting`.

Key plugins: `opencode-daytona` (isolated sandboxes), `opencode-pty` (background PTY processes), `opencode-shell-strategy` (non-interactive shell), `opencode-supermemory` (persistent memory), `opencode-firecrawl` (web scraping), `opencode-sentry-monitor` (Sentry AI Monitoring), `opencode-morph-fast-apply` / `opencode-morph-plugin` (fast editing via Morph), `opencode-devcontainers` (multi-branch isolation), `opencode-gemini-auth`, `opencode-openai-codex-auth`, `opencode-google-antigravity-auth` (use existing subscriptions), `opencode-dynamic-context-pruning` (token optimization), `opencode-vibeguard` (PII redaction), `opencode-scheduler` (launchd/systemd cron), `opencode-conductor` (protocol-driven Context→Spec→Plan→Implement), `opencode-background-agents` (async delegation), `opencode-worktree` (git worktree automation), `oh-my-opencode` (pre-built LSP/AST/MCP tools, Claude Code compatible).

### Projects

- **OpenWork** (different-ai/openwork, 13.5k stars) — open-source Claude Cowork alternative. Desktop app (Tauri, macOS), web UI, VS Code extension, Cloudflare tunneling, multi-agent with worktrees, git sidebar, PR creation, 18+ themes. Architecture: hosts `opencode serve` locally per project folder.
- **OpenChamber** (btriapitsyn/openchamber, 2.9k stars) — Desktop/web + VS Code extension. Branchable chat timeline, multi-agent runs with isolated worktrees, voice mode, terminal integration, git integration.
- **kimaki** (remorses/kimaki) — Discord bot built on the SDK.
- **portal** (hosenur/portal) — Mobile-first web UI over Tailscale/VPN.
- **ocx** (kdcokenny/ocx, 579 stars) — OpenCode config manager with portable isolated profiles, registry system, SHA-verified component installs. ShadCN-inspired model: components copied to `.opencode/`, not node_modules. CLI: `npm install -g ocx`.
- **ai-sdk-provider-opencode-sdk** (ben-vargas/ai-sdk-provider-opencode-sdk, 81 stars, npm: `ai-sdk-provider-opencode-sdk`) — Vercel AI SDK v5/v6 provider wrapping `@opencode-ai/sdk`. Enables `generateText()`, `streamText()`, structured output, tool observation, session management via OpenCode. Model format: `providerID/modelID` (e.g. `openai/gpt-5.3-codex-spark`). Supports AI SDK v6 (`latest`) and v5 (`ai-sdk-v5` tag). Auto-starts `opencode serve` if not running. Supports `providerOptions.opencode.messageID` for session-scoped calls.
- **OpenCode-Obsidian** — Obsidian plugin embedding OpenCode.
- **CodeNomad** — Desktop/Web/Mobile/Remote client.

### Agents

`Agentic` (Cluster444/agentic) — modular AI agents and commands. `opencode-agents` (darrenhinde/opencode-agents) — configs, prompts, agents, plugins.

---

## Official vs Community

**Everything in the ecosystem page is community.** Official OpenCode assets: the SST-built CLI (`opencode-ai` npm, `anomalyco/opencode` repo), `@opencode-ai/sdk` (the typed JS client), `opencode serve` (the HTTP API server), and the GitHub App for PR/issue comments (`github.com/apps/opencode-agent`). The plugin template at [zenobi-us/opencode-plugin-template](https://github.com/zenobi-us/opencode-plugin-template) is community-made (archived, deprecated in favor of `zenobi-us/bun-module`).

---

## Headless / Programmatic Use (Droid-like CLI Offload)

This is OpenCode's strongest area for replacing droid-style workflows:

**`opencode serve`** — HTTP server on configurable port (default 4096) + hostname. Exposes an OpenAPI 3.1 spec at `/doc`. This is the headless daemon. Authentication via `OPENCODE_SERVER_PASSWORD` (+ optional `OPENCODE_SERVER_USERNAME`). Optional mDNS discovery (`--mdns`).

**SDK** (`@opencode-ai/sdk`) — Type-safe client. Two modes:
- `createOpencode()` — spawns a server + client; `client.dispose()` kills the server.
- `createOpencodeClient({ baseUrl })` — connects to an already-running server.

Key SDK session methods: `session.create()`, `session.prompt()`, `session.list()`, `session.get()`, `session.delete()`, `session.abort()`, `session.share()`, `session.revert()`, `session.summarize()`, `session.prompt_async()` (fire-and-forget, returns 204). Also: `session.command()` for slash commands, `session.shell()` for inline shell execution. File APIs: `find.text()`, `find.files()`, `file.read()`. Event stream via `event.subscribe()` (SSE).

**Custom Commands** — Markdown files in `.opencode/commands/` or `~/.config/opencode/commands/`. Support `$ARGUMENTS`, positional `$1`/`$2`/`$3`, shell output injection via `!`backtick\``, `@file` references. Can specify agent, model, and `subtask: true` to force subagent isolation. Executed via `session.command()` in the SDK.

**Modes** — `build` (default, all tools), `plan` (read-only), or custom defined in `opencode.json` or `.opencode/modes/` markdown files. Control tools, model, temperature, and prompt per mode. Switch via Tab key or SDK.

**Structured Output** — `session.prompt()` accepts `format: { type: "json_schema", schema: {...}, retryCount: N }`. Falls back to prompt+parse+validate pattern recommended for strict reliability.

**Permission system** — `permission.asked` event in plugins; `session.postSessionByIdPermissionsByPermissionId()` in SDK. Configurable in `opencode.json`: `"permission": { "bash": "ask", "edit": "ask" }`.

**Vercel AI SDK provider** — `ai-sdk-provider-opencode-sdk` is the direct analog to what `mcp-droid` does for droid. It wraps `@opencode-ai/sdk` into the Vercel AI SDK interface (`generateText`, `streamText`, `Output.object`). Supports multi-turn sessions (sessionId persistence), tool observation (read-only), abort signals, image input (base64/data URLs only). **Does not support custom tool implementations** — tools are server-side only.

**OpenWork** also runs `opencode serve` as the host runtime — relevant as a reference architecture for headless multi-project orchestration.

---

## MCP Servers

OpenCode config natively supports MCP servers via `"mcp"` in `opencode.json`. Remote MCP servers (type: `"remote"`) can be organizational defaults from `.well-known/opencode`. The `/mcp` endpoint in the server API lists status; `POST /mcp` adds servers dynamically. Also supports dynamic MCP server addition at runtime via SDK.

---

## Plugin Distribution

**npm** (primary): `"plugin": ["package-name"]` in `opencode.json`. Bun auto-installs from npm at startup, cached in `~/.cache/opencode/node_modules/`. Both scoped (`@org/package`) and unscoped packages supported.

**Local files**: `.opencode/plugins/` (project) or `~/.config/opencode/plugins/` (global). Files auto-loaded at startup.

**Local dependencies**: Add `package.json` to config directory with `"dependencies"`. Bun runs `bun install` at startup. Plugins then `import` from them.

**ShadCN-style** (ocx): components copied to `.opencode/`, SHA-verified, registry-based distribution. Not npm but a separate tool.

---

## IDE Integrations

| IDE | Type | Repo/Link |
|-----|------|-----------|
| **VS Code** | Official extension (Beta) | Marketplace: `sst-dev.opencode` (v2: `sst-dev.opencode-v2`) |
| **VS Code** | Community (OpenChamber) | `openchamber/openchamber` |
| **Zed** | Official extension (ACP) | `zed.dev/extensions/opencode` (v1.4.1, 226k downloads) |
| **JetBrains** | Two community plugins | `plugins.jetbrains.com/plugin/29744-opencode-ui` + `plugins.jetbrains.com/plugin/30681-opencode` |
| **JetBrains** | Unofficial bundle | `opencode-ux+` (plugins.jetbrains.com/plugin/29089) |
| **Neovim** | Two plugins | `nickjvandyke/opencode.nvim` (3.2k stars, Lua, uses OpenCode TUI), `sudo-tee/opencode.nvim` (737 stars, terminal frontend) |
| **Cursor/Windsurf/VSCodium** | Via terminal | Run `opencode` in integrated terminal; extension auto-installs |
| **OpenWork** | Desktop app (Tauri/macOS) | `different-ai/openwork` |

---

## GitHub Actions

**Official action**: `anomalyco/opencode/github@latest` ([docs](https://opencode.ai/docs/github/)). Setup: `opencode github install` or manual — add `.github/workflows/opencode.yml`, install GitHub App, store API keys in secrets.

**Trigger events**: `issue_comment` (mention `/oc` or `/opencode`), `pull_request_review_comment` (comment on lines), `issues` (with `prompt` input), `pull_request` (auto-review), `schedule` (cron), `workflow_dispatch` (manual).

**Inputs**: `model` (required, `provider/model` format), `agent`, `prompt` (required for non-comment events), `share`, `token` (defaults to GitHub App installation token). Permissions: `id-token: write` always needed; `contents: write`, `pull-requests: write`, `issues: write` as needed.

**Key examples**: PR auto-review (trigger on `pull_request` types), scheduled triage (cron `0 9 * * 1`), issue fix workflow (`/opencode fix this` → creates branch + PR).

**Community**: `different-ai/opencode-scheduler` (systemd/launchd cron scheduling), `CloudAI-X/opencode-workflow` (universal setup with specialized agents/skills/commands/plugins), `opencode-background-agents` (async delegation pattern).

---

## Running as Service / Daemon

`opencode serve` is the primary mechanism. Defaults: port `4096`, hostname `127.0.0.1`. Flags: `--port`, `--hostname`, `--mdns` (network discovery), `--mdns-domain`, `--cors` (can repeat for multiple origins). Auth: `OPENCODE_SERVER_PASSWORD` (username: `opencode` default, configurable via `OPENCODE_SERVER_USERNAME`).

**Architecture**: The CLI itself starts both a server and a TUI client. `opencode serve` starts just the server. If a TUI is already running, `opencode serve` starts a new independent server. The SDK's `createOpencode()` manages server lifecycle automatically.

**Use for headless**: Start `opencode serve` in background, then connect via SDK (`createOpencodeClient`). The server exposes full session management, file ops, tool execution, permission approval, event streaming. `session.prompt_async()` for fire-and-forget. No TUI involvement needed once the server is up.

**Remote/project scoping**: Server binds to project directory on startup; `session.prompt()` calls include directory context. The `/session/:id/message` POST accepts `directory` parameter to scope operations.
