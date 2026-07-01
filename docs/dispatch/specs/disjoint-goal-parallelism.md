# Spec (not-build): file-disjoint parallel-worktree dispatch

Status: **design only — deliberately not implemented.** This documents the one
credible way to run more than one goal at a time, so the option is on record and
can be decided later instead of re-invented from scratch (or re-invented as v3).

Local-only doc (`docs/`): never commit, never push.

## Why this exists

The v4 dispatch model is sequential: one ready goal per run, one foreground
implementer, direct-to-branch, local gate, no worktrees, no PRs. That shape is
scar tissue — v3's per-goal worktree PRs + parallel `wip` implementers +
CI-gated auto-merge livelocked on two real autonomous runs (PR-shepherding
churn, offline CI runners blocking every merge, stale `goal/*` /
`worktree-agent-*` branch garbage; CHANGELOG 4.0.0).

The recurring question — "can't we work many goals at once when the queue is
big?" — deserves a real answer, not just "no." This is the steelman.

## The one shape that is NOT v3

Run N genuinely **file-disjoint** goals concurrently, each in its own
`isolation: worktree` implementer, each gated **locally** in its own worktree,
then integrate by **fast-forward / sequential squash-merge** back onto the
working branch at the end of the run. No PRs, no CI merge gate — so the specific
mechanism that livelocked v3 (CI-as-merge-gate + PR shepherding) is absent.

Pipeline sketch (conceptual, if ever built as a Workflow):

```
1. Partition:  read the queue; select goals whose declared touch-sets are
               provably disjoint (see "hard part" below). Cap N small (2–3).
2. Fan out:    one worktree implementer per goal (isolation: worktree),
               each on its own throwaway branch off gate_base.
3. Gate each:  run pg_validate + config.verify INSIDE that worktree
               (deps installed per worktree — see risk C).
4. Integrate:  sequentially squash-merge each PASS worktree onto the working
               branch, re-running the gate after each merge. First conflict or
               post-merge gate failure → block that goal, keep the rest.
5. Report:     same one-line report; blocked/needs-you unchanged.
```

## Why it still probably isn't worth it

The speedup only materializes when the queue is **large AND the goals are
cleanly file-disjoint**. Real queues are usually small and interdependent
(`depends_on` chains), where sequential already wins and this buys nothing but
overhead. Concretely, the costs it re-imports:

- **A. Disjointness prediction is the hard part.** You must know each goal's
  touch-set *before* implementing. Goals don't declare that reliably; a wrong
  guess surfaces as an integration conflict at step 4 — exactly the "substantive
  conflict, never guess through" case the sequential model avoids by
  construction.
- **B. End-of-run merge arbitration returns.** Sequential squash-merge with a
  re-gate after each merge reintroduces conflict handling and partial-failure
  bookkeeping (some goals land, some block) — the coordination surface v4
  deleted.
- **C. Per-worktree dependency setup.** Each worktree is a fresh checkout with no
  installed deps. v4.0.1 was a hotfix for exactly this: an acceptance command in
  a deps-less base worktree produced a *false PASS*. Every parallel worktree
  multiplies that reproducibility surface and the install cost.
- **D. Autonomous-loop babysitting.** A `/loop` that manages N worktrees per fire
  is back to burning tokens shepherding concurrent work — the v3 failure mode in
  a new coat.

## Verdict

Keep in the back pocket; do not build now. The intra-goal concurrency we already
have (nested read-only recon, the multi-lens fresh-check panel, adversarial
verify) captures most of the quality upside at none of the coordination cost.

Revisit ONLY if a real workload shows: a persistently large queue (say 15+
ready), goals that are naturally file-disjoint (separate modules/services), and
a measured wall-clock pain that sequential can't absorb. Even then, prototype the
**partition + per-worktree local gate** in isolation first and prove step 1's
disjointness detection before wiring integration — that is the make-or-break
piece, and it is the piece v3 never actually solved.
