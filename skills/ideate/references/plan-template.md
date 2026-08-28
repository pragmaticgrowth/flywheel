# The plan template (canonical — ideate step 4)

Write plans to `docs/goals/plans/YYYY-MM-DD-<topic>.md` (create the directory if
needed). Fill every section; sections marked *(code-shaped)* apply when the work
touches existing code and stay prose-light for greenfield. Keep the whole plan
under ~2 pages — a plan that needs more is usually two plans.

Two writing rules govern the entire document:

1. **Headers state the takeaway, not the topic and not the question.** A reader
   skimming only the headings must get the design's actual claims — that is what
   makes a wrong assumption catchable in seconds.
   - BAD (topic): `### Session storage`
   - BAD (question): `### How are sessions persisted?`
   - GOOD (takeaway): `### Sessions persist to Postgres before the daemon acks`
2. **Altitude: signatures and shapes, never function bodies.** If the plan starts
   containing implementations, it has dropped a level — that detail belongs to the
   implementer. Show a signature with its body elided (`{ ... }`), a file-tree
   diff, a call-flow sketch; never working code.

```markdown
---
topic: <kebab-case-topic>
created: YYYY-MM-DD
status: open          # open (draft) | approved (ideate stamps it at the owner's
                      #   approval touch; OPEN questions may remain) | done
                      #   (dispatch stamps it when the last phase checks)
repo: <repo name>
branch: <working branch>
# artifact: <url>    # optional — the plan's presentation page (SKILL.md step 5:
#                    # published/updated ONLY at ideate's approval touches;
#                    # dispatch's mirror and define-goal's amends never touch it)
---

# <Plan title — a takeaway, not a label>

## What we're doing

<2–4 sentences in the owner's language. What will exist, for whom, and why now.>

## Current state

<What the user sees or experiences today — product behavior first, no file paths
in the opening lines. Then:>

Key discoveries:
- <finding with path:line>
- <pattern to follow with path:line>
- <constraint to work within>

## What will be true when done

<Each bullet names the EXACT command that proves it, in `config.verify`'s form. Every
command must FAIL at this plan's base commit and pass only once every phase has landed
— a check that already passes before any phase lands is measuring a piece, not the
whole. A subjective outcome that no command can settle keeps the review marker instead;
do not invent a command for it.>

- <observable outcome> — `<exact command>`
- <subjective outcome> — **needs independent review**
- Nothing else regressed — `<the repo's full verify command>`, green at base and at head

<Two rules govern the commands:>

<1. COMMITTED-TEST FORM. Each command must run a test the repo's own suite discovers —
`config.verify` must reach it as written. Never an ad-hoc command run once at settle: a
committed check is re-run by every later goal's gate, so a late phase that breaks an
early phase's outcome fails a gate, while a one-shot command leaves `status: done`
stamped against evidence that went stale the moment the next phase landed.>

<2. DRIVABLE-SURFACE CHECKS. Each command drives the real surface — the CLI, the API, the
suite, the rendered page — never a check that only reads or greps source. Phase
implementers read this plan, so the checks are visible to them by design; that is safe
only while the sole way to pass a check is to actually build the behavior it measures.>

Post-ship signal (optional): <the metric, log line, or behavior to check AFTER this
ships that says it actually worked — distinct from the acceptance criteria that gate
the merge — or "none: too small to measure">.

## What we're NOT doing

<Mandatory, never empty — explicit exclusions prevent scope sprawl. Name the
tempting adjacent work and why it's excluded or deferred.>

## Design

<Takeaway-headed subsections. Where the work touches existing code, this section
is CODE-SHAPED, not prose:>

### <Takeaway: e.g. "recordsService.update accepts links, as create already does">

```<lang>
// exact signatures introduced or changed, bodies elided
async function update(args: UpdateArgs & { links?: Link[] }): Promise<Row> { ... }
```

### Files

```
created   src/x/y.ts        — <one line: what this file becomes responsible for>
modified  src/a/b.ts        — <one line>
```

### <Call-flow sketch — ONLY where control flow is non-obvious>

<entry → step → step, or a small mermaid flowchart>

### Patterns to follow

<The existing codebase patterns the implementation should imitate — from
recon-patterns findings where recon ran: each a `path:line`, a short snippet where
the shape matters, and one line on why it's the house pattern (incl. how similar
things are TESTED). This is where recon-patterns output lands so every phase's
implementer inherits it; omit the section only when the work is genuinely
greenfield.>

## Open questions

<Every design fork the exploration raised. The agent may RECOMMEND an option; only
the owner resolves one. "Go with your recommendations" from the owner resolves ALL
open questions at once — record each as resolved with that provenance. A plan may
be handed to define-goal with questions still OPEN: an unresolved design question
is information, not a blocker, and a goal that trips over one has somewhere to
point. A resolved question keeps its one-line why forever.>

### OPEN — <the question, one line>
- Option A: <...>
- Option B: <...>
- Recommendation: <option + one-line why>

### RESOLVED <date> — <the question>
- <chosen option> — <one-line why> (<owner decision | owner: "go with your
  recommendations">)

## Phases

<Vertical slices, each independently verifiable end-to-end, each mapping 1:1 onto
one future goal. Slice test: if a phase cannot be verified without a LATER phase
existing, it is not a slice — re-cut. A decomposition ordered by layer ("all
schema, then all services, then all UI") is horizontal and produces nothing
testable until the last phase; cut through the layers instead — the thinnest
end-to-end path first, then widen.>

- [ ] Phase 1: <takeaway title — what a user/system can DO after this phase>
  - Files: <one line per file>
  - Verify: `<exact command>` · <plus any needs-independent-review item>
- [ ] Phase 2: <takeaway title>
  - Files: <...>
  - Verify: `<exact command>`

<AT 3 OR MORE PHASES, the LAST phase is an OUTCOME CHECK — the phase that measures the
WHOLE rather than another piece. It builds nothing: it runs every bullet in
`## What will be true when done`, shows each one failing at the plan's base commit and
passing at HEAD, and stops for the owner if any bullet cannot be shown failing at base
(a check that passes at base was measuring a piece). It depends on every other phase, so
`status: done` on the plan means the outcome check PASSED, not merely that the pieces got
built. A plan of 1-2 phases does not need one — the pieces and the whole are the same
thing at that size.>

- [ ] Phase N: <the outcome check — verification only, builds nothing>
  - Depends on: <every other phase>
  - Verify: every bullet in `## What will be true when done`, run in order, each shown
    failing at base and passing at HEAD
```

Checkbox lifecycle: ideate writes every phase `- [ ]`. Dispatch flips a phase to
`- [x]` in the same commit that settles its goal `completed`, and stamps the
frontmatter `status: done` when the last phase checks — a DISPLAY mirror only;
`index.yaml` remains the sole status authority, and dispatch's Phase 0 doctor
pass re-syncs a drifted checkbox in the plan-follows-index direction only.
