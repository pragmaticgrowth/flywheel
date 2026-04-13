# mcp-do

**Status: v0.2.0** — 15 MCP tools, 183 passing unit tests, droid + opencode dual-backend support. Distributed as the `do` Claude Code plugin via the `pragmatic-growth` marketplace.

A local **stdio MCP server** and Claude Code **plugin** that wraps Factory AI [`droid`](https://docs.factory.ai/cli/getting-started/overview) CLI and [`opencode`](https://opencode.ai) CLI as a unified typed tool surface. The "3rd eye" for Claude Code — offloads research, review, architecture analysis, and bug hunting to cheap headless AI models.

## Install

### Via Claude Code Plugin (recommended)

```bash
# Add the marketplace
claude plugin marketplace add pragmaticgrowth/mcp-do

# Install the plugin
claude plugin install do@pragmatic-growth

# Sync agent profiles to droid + opencode
/do:setup --sync-agents
```

### Manual

```bash
git clone git@github.com:pragmaticgrowth/mcp-do.git
cd mcp-do
npm install && npm run build
npm link
claude mcp add mcp-do -- mcp-do
```

## Tools (15)

| Group | Tools |
|---|---|
| Generic | `do_exec` |
| Presets | `do_research`, `do_research_fast`, `do_review`, `do_explore`, `do_architect`, `do_silent_scan`, `do_type_check`, `do_pr_review`, `do_adversarial_review` |
| Cross-model | `do_cross_review` (3 models in parallel) |
| Sessions | `do_session_continue`, `do_session_list` |
| Meta | `do_list_models`, `do_list_profiles` |

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/do:review [--cross]` | Code review. `--cross` for 3-model parallel |
| `/do:pr [--base] [--focus]` | Comprehensive PR review with GPT-5.4 xHigh |
| `/do:adversarial-review` | Adversarial review — challenges design choices |
| `/do:research [--fast]` | Web research via headless model |
| `/do:explore` | Codebase navigation with file:line references |
| `/do:architect` | Architecture analysis |
| `/do:scan` | Silent failure scan |
| `/do:types` | TypeScript type design review |
| `/do:exec` | Power-user passthrough |
| `/do:setup [--sync-agents]` | Verify installations, sync agent profiles |

## Models

All GPT models route through YK (your own OpenAI key). Default models:

| Role | Model |
|------|-------|
| Default (research, review, explore) | GLM-5-Turbo (BYOK) |
| Deep (architect) | GLM-5.1 (BYOK) |
| Fast (research_fast) | MiniMax M2.7 (BYOK) |
| PR review | GPT-5.4 xHigh (YK) |
| Cross-review GPT slot | GPT-5.4 High (YK) |

## Development

```bash
npm run build         # tsc -> dist/
npm test              # vitest — 183 tests
npm start             # node dist/index.js
```

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — full project context
- [`docs/spec.md`](docs/spec.md) — architecture spec
- [`skills/do-tools/SKILL.md`](skills/do-tools/SKILL.md) — plugin skill with decision matrix

## License

Personal project. No license declared.
