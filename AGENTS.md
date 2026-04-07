# Agents

For full project context, read [`CLAUDE.md`](CLAUDE.md). Everything below applies
to every agent that touches this repo (Claude, Codex, Gemini, droid itself).

## Research Rule

**ALL web research MUST go through the `deep-researcher` droid**
(`~/.factory/droids/deep-researcher.md`). Never run Research Powerpack or
Context7 MCP tools directly in main context — they produce 10k–30k+ tokens per
call and flood the context window. The deep-researcher absorbs all that
internally and returns a clean synthesis.

```bash
droid exec --model "custom:glm-5-turbo" --auto high \
  --append-system-prompt-file ~/.factory/droids/deep-researcher.md \
  --output-format text "your research question here"
```

Run via Bash tool with `run_in_background: true` and read the output when done.

## Project-Specific

This repo is itself building an MCP server that wraps droid. Once built, use
`droid_research(...)` instead of the raw shell pattern above. Until then, the
shell pattern is the only option.

The build brief lives at [`docs/spec.md`](docs/spec.md). Read it before writing
any code.
