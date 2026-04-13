---
name: do-tools
description: Use the "do" plugin (mcp-do MCP server) to delegate work to headless AI models via droid and opencode backends. Trigger whenever the user mentions droid, opencode, research, review, explore, architect, "delegate to", "ask the researcher", "have droid look at", "run a review", "audit X", "scan for", "adversarial review", "challenge review", "review gate", or wants to offload any task to a cheap BYOK model (GLM-5-Turbo, MiniMax-M2.7, GLM-5.1). ALSO trigger for do_research, do_review, do_adversarial_review, do_explore, do_architect, do_cross_review, do_silent_scan, do_type_check, do_exec, or any do_* MCP tool name. This is the "3rd eye" for Claude Code — offloads analysis, research, and auditing to keep the main context focused.
---

# do-tools — 3rd Eye for Claude Code

Delegate research, review, architecture analysis, and bug hunting to headless AI models via the mcp-do MCP server. Supports two backends: **droid** (Factory.ai) and **opencode** (SST). Each tool includes intelligent structured prompts (task + output contract + grounding rules).

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/do:review [--cross]` | Code review against git diff. `--cross` for 3-model parallel review |
| `/do:adversarial-review [focus]` | Adversarial review — challenges design choices, not just code quality |
| `/do:research [--fast] <question>` | Web research. `--fast` for quick lookup |
| `/do:explore <question>` | Codebase navigation with file:line references |
| `/do:architect <scope>` | Architecture analysis with trade-off assessments |
| `/do:scan [scope]` | Silent failure scan (swallowed errors, empty catches) |
| `/do:types [scope]` | TypeScript type design review |
| `/do:exec <prompt>` | Power-user passthrough with all flags |
| `/do:session [continue\|list]` | Droid session management |
| `/do:status [models\|profiles]` | Show available models and profiles |
| `/do:setup [--sync-agents] [--enable-review-gate]` | Verify installations, sync agents, toggle review gate |
| `/do:pr [--base] [--focus]` | Comprehensive PR review with GPT-5.4 xHigh. Auto-gathers git context |

## Decision Matrix — which tool to use

| Task | MCP Tool | Slash Command |
|------|----------|---------------|
| Research a library / API / concept | `do_research` | `/do:research` |
| Quick factual lookup | `do_research_fast` | `/do:research --fast` |
| Code review of recent edits | `do_review` | `/do:review` |
| Adversarial review (challenge design, not just code) | `do_adversarial_review` | `/do:adversarial-review` |
| Cross-model review (3 models, security/auth code) | `do_cross_review` | `/do:review --cross` |
| "Where is X?" / "How does Y work?" | `do_explore` | `/do:explore` |
| High-level architecture analysis | `do_architect` | `/do:architect` |
| Find empty catches / silent failures | `do_silent_scan` | `/do:scan` |
| Review TypeScript type design | `do_type_check` | `/do:types` |
| Generic single-shot call | `do_exec` | `/do:exec` |
| Continue a previous session | `do_session_continue` | `/do:session continue` |
| PR review (comprehensive) | `do_pr_review` | `/do:pr` |
| List models / profiles | `do_list_models` / `do_list_profiles` | `/do:status` |
| Quick bug fix, single file | Handle in Claude Code directly — no delegation |
| Needs browser verification / live prod data | Handle in Claude Code directly |

## Provider Selection

Every execution tool accepts `provider: "droid" | "opencode"`. Default is set by:
1. Per-call `provider` parameter (highest priority)
2. `DO_DEFAULT_PROVIDER` environment variable
3. `~/.config/mcp-do/config.json` → `default_provider`
4. Built-in default: `"droid"`

## Core Operational Rules

These are **load-bearing** — violating them has caused real bugs.

### Rule 1: Only custom BYOK models, never factory built-ins

Use `custom:glm-5-turbo`, `custom:MiniMax-M2.7`, `custom:glm-5.1`, `custom:VP-GPT-5.4-Mini-48`, etc. **Never** `claude-opus-4-6`, `gpt-5.4`, `gemini-3-flash-preview` — those are factory built-ins (402 Payment Required).

The do_* presets already default to custom models. Only override `model:` with a custom or aliased id (`glm-5-turbo`, `gpt-5.4-mini`, `minimax-m2.7`).

### Rule 2: Use `do_cross_review` before committing significant changes

Different model families (Zhipu, OpenAI, MiniMax) have different blind spots and catch 3-5x more issues combined. Non-negotiable for security, auth, and payment code.

### Rule 3: Research goes through headless, never in main context

**ALL web research MUST go through do_research / do_research_fast.** Never run Research Powerpack or Context7 MCP tools directly in main context — they produce 10k-30k+ tokens per call. Use the `/do:research` command or the `do-researcher` agent instead.

### Rule 4: Session list is incomplete by default

`do_session_list` reads `~/.factory/sessions-index.json` by default — and that index skips sessions created via `droid exec` (which is how mcp-do creates them). Pass `scan_disk: true` for the complete set.

### Rule 5: Model aliases resolve per-provider

Short aliases resolve differently per provider:
| Alias | Droid | OpenCode |
|-------|-------|----------|
| `glm-5-turbo` | `custom:glm-5-turbo` | `zai-coding-plan/glm-5-turbo` |
| `glm-5.1` | `custom:glm-5.1` | `zai-coding-plan/glm-5.1` |
| `gpt-5.4-mini` | `custom:VP-GPT-5.4-Mini-48` | `openai/gpt-5.4-mini` |
| `minimax-m2.7` | `custom:MiniMax-M2.7` | `minimax-coding-plan/MiniMax-M2.7` |

You can use aliases in tool calls — the system resolves to the right provider-specific ID.

## Model Quick Reference

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `glm-5-turbo` | **Fast** | A+ | Default for research, review, exploration. Best quality + tool calling |
| `minimax-m2.7` | **Fastest** | A | Quick lookups, batch analysis (no tool calling) |
| `glm-5.1` | Slow | A+ | Deepest analysis, architecture review. Default for `do_architect` |
| `gpt-5.4-mini` | Fast | A | Cross-review default (OpenAI family for blind-spot coverage) |

## Subagents

Three thin-forwarder agents are available for proactive delegation:
- **do-researcher** — routes research questions to `do_research` / `do_research_fast`
- **do-reviewer** — gathers git diff, routes to `do_review` / `do_cross_review`
- **do-explorer** — routes codebase questions to `do_explore`

Use these when you want Claude to proactively delegate without a slash command.

## Stop Review Gate

When enabled, a `Stop` hook automatically runs a droid review before Claude stops working. If the review finds material issues, the stop is blocked and Claude must fix them first.

- **Enable**: `/do:setup --enable-review-gate`
- **Disable**: `/do:setup --disable-review-gate`
- **Default**: disabled
- **Model**: `custom:glm-5-turbo` (fast, good quality)
- **Fail-open**: if droid is unavailable or times out, the stop is allowed (never hard-blocks)

The gate only reviews code changes from the immediately previous turn. Status updates, setup output, and review results are automatically ALLOWed without inspection.

## Full Tool Catalog

See [`references/tool-catalog.md`](references/tool-catalog.md) for all 15 tools with parameter details and examples.

## Troubleshooting

See [`references/troubleshooting.md`](references/troubleshooting.md) for common issues and fixes.
