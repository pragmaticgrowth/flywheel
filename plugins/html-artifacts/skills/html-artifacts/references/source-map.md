# Source Map

Use this when maintaining or auditing the skill, not for every artifact generation.

## Primary Sources

- Anthropic, "Using Claude Code: The unreasonable effectiveness of HTML":
  `https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html`
- Thariq Shihipar's companion gallery:
  `https://thariqs.github.io/html-effectiveness/`
- Gallery source repo:
  `https://github.com/thariqs/html-effectiveness`
- f-labs-io `agent-html-skills` plugin:
  `https://github.com/f-labs-io/agent-html-skills`
- Standalone one-skill prior art:
  `https://github.com/dogum/html-artifacts`

## Coverage Map

| Source/gallery category | This skill reference |
|---|---|
| Exploration and planning | `planning-and-comparison.md` |
| Code review and code understanding | `code-review-and-understanding.md` |
| Design systems and component variants | `design-and-prototypes.md` |
| Prototyping animations/interactions | `design-and-prototypes.md`, `custom-editors.md` |
| SVG illustrations and flowcharts | `diagrams-and-data.md` |
| Decks | `decks.md` |
| Research and concept explainers | `reports-and-research.md` |
| Status and incident reports | `reports-and-research.md`, `diagrams-and-data.md` |
| Custom editors | `custom-editors.md` |
| Architecture, ERD, timelines, data explorers from f-labs | `diagrams-and-data.md` |

## Design Decisions

- Single skill, many references. This keeps triggering simple while preserving progressive
  disclosure.
- No listener/server submit pipeline. The html-artifacts plugin remains skills-only: no MCP,
  hooks, commands, daemons, or background processes.
- Clipboard/export is the universal round trip. It works in Claude Code, Droid, local
  browsers, and other agent shells.
- Foundation rules are centralized in one reference instead of repeated in every topic file.
- Topic files give recipes, not rigid templates. The agent should compose the artifact to the
  task instead of filling a slot grammar.

## Maintenance Checklist

When changing this skill:

1. Keep `SKILL.md` under control; move topic depth to references.
2. Update this coverage map if adding/removing a reference.
3. Verify at least one pressure scenario:
   - stakeholder-ready implementation plan becomes an HTML file;
   - custom editor includes export;
   - diagram uses inline SVG and handles labels.
4. Keep README and `public/index.html` aligned with the plugin boundary and description.
5. Do not add servers, commands, hooks, or MCP surfaces without an explicit user request.
