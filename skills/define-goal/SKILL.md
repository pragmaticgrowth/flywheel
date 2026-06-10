---
name: define-goal
description: Use when the user asks to define, create, or set a goal, clarify success criteria, run goal-backed work ("set a goal", "use /goal for this", "/define-goal"), or turn a fuzzy intention into a measurable objective. Shapes the intent into a quality-checked objective and hands back a copy-pasteable `/goal` line (objective + verification evidence + stop condition). Defines goals only; never starts the implementation work.
---

# Define Goal

## Overview

Shape the user's intent into an objective an agent can pursue honestly. Prefer measurable
outcomes, explicit evidence, and bounded scope over activity descriptions.

This skill covers goal definition only. Do not create intermediate planning artifacts,
durable snapshots, ledgers, decision logs, or resume files from this skill.

Claude Code has no goal tools — there is no `create_goal` or `get_goal`. Goal-backed
execution is driven by the built-in `/goal` command, which only the user can run: after
each turn, a separate evaluator model reads the conversation transcript and checks whether
the stated condition holds; if not, Claude keeps working with the evaluator's reason as
guidance. The output of this skill is therefore a **handoff**: a finished, copy-pasteable
`/goal` line, not a tool call.

## Workflow

1. Confirm that goal definition is actually needed.
   - Use this skill when the user asks to create or set a goal, asks for goal-backed work,
     or wants help turning an intention into a clear objective.
   - If the user only asks for ordinary implementation work, do the work directly instead
     of forcing goal creation.

2. Restate the likely goal in concrete terms.
   A usable goal names:
   - the specific outcome that will be true
   - the main artifact, system, repo, environment, or user-facing behavior involved
   - how completion will be verified
   - what is in scope
   - what is out of scope when ambiguity would matter
   - the stop condition for asking the user instead of grinding

3. Make it quantitative when the domain supports it.
   Prefer numbers that represent real success, not decorative precision:
   - pass/fail validators: exact tests, checks, CI jobs, evals, commands, or acceptance criteria
   - quality thresholds: latency, error rate, cost, accuracy, recall, precision, coverage,
     flake rate, bundle size, memory, uptime, completion rate, or manual review criteria
   - artifact constraints: file paths, affected modules, allowed commands, output formats,
     target environments, deadlines, or maximum blast radius
   - evidence counts: number of reproduced failures, successful reruns, reviewed examples,
     migrated records, addressed comments, or verified cases

4. Repair weak goals before handing them off.
   - Rewrite vague goals into measurable objectives when local context makes the rewrite safe.
   - Ask one concise clarification question when the missing detail changes the intended
     outcome or validation.
   - Reject pure activity goals such as "make progress," "keep investigating," "improve
     things," or "work on X" unless they are sharpened into a verifiable outcome.

5. Check for an active goal before proposing a new one.
   - Goal state is session-scoped and owned by the user; there is no tool to query it.
   - If a goal was already set earlier in this session and still matches the intent,
     continue under it instead of proposing a duplicate.
   - If an active goal conflicts with the new request, ask whether to finish the current
     goal first or replace it.

6. Hand off the goal only after it passes the quality bar.
   - Compose a single `/goal` line: objective, verification evidence, scope bounds when
     they constrain the work, and a bounded stop clause (e.g., "or stop after 20 turns
     and ask").
   - Phrase it as a checkable completion condition. The evaluator is a separate model
     reading the transcript, so name evidence that will actually appear there: command
     output, test results, file contents surfaced during the work.
   - Present it in a code block for the user to run — built-in slash commands cannot be
     invoked by Claude. For headless or scheduled runs, show the
     `claude -p "/goal …"` form instead.
   - Do not propose `/goal` for an ordinary multi-step task unless the user explicitly
     asked for goal-backed work.

## Goal Quality Bar

Before handing off the `/goal` line, the objective should answer:

- What concrete thing will be true when this is done?
- What evidence will prove it?
- What quantitative or binary threshold defines success?
- What scope boundaries matter?
- What should cause the agent to stop and ask?

Good:

> /goal checkout API p95 latency is below 250 ms on the documented slow path via the
> smallest safe server-side change, verified by `npm run test:checkout` passing and the
> existing local latency benchmark showing p95 under 250 ms across 3 consecutive runs —
> or stop after 20 turns and ask

Good:

> /goal all open change-request review comments on PR 123 are resolved, touching only the
> affected auth files and tests, verified by the targeted auth test command passing and
> `gh pr view 123` showing no unresolved change-request threads — or stop after 15 turns
> and ask

Weak:

> Make checkout faster.

Weak:

> Keep investigating the PR comments.

## Quantification Heuristics

- For bugs, define success as reproduction first, fix second, and a failing-then-passing
  validator when possible.
- For tests, name the exact command and required pass condition.
- For performance, name the metric, target threshold, measurement method, and number of runs.
- For quality work, define an observable acceptance bar such as reviewed examples,
  lint/typecheck/test pass, or user-approved artifact.
- For research, define the decision the research must enable, the sources or systems in
  scope, and the evidence standard.
- For operations, define healthy state, monitoring window, failure threshold, and rollback
  or escalation trigger.

## Clarifying Questions

Ask only when a reasonable rewrite would risk pursuing the wrong outcome. Keep the question
short and oriented around the missing validator or scope boundary.

Useful question shapes:

- "What metric should define success here: latency, cost, accuracy, or user-visible behavior?"
- "Which environment should I verify against: local, staging, or production?"
- "What is the minimum evidence you want before I mark this goal complete?"

If the user cannot provide a metric, propose the most honest binary validator available and
ask for confirmation.

## Related Skills

- For a recurring or unattended run rather than a single goal, design the full loop
  contract with **loop-architect**.
- To park the contract as an agent-ready GitHub issue instead of running it now, use
  **wish**.
