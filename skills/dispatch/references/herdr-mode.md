# Dispatch — herdr execution mode (the brain)

This file is the queue-driven brain for `execution: herdr`. It governs ONLY the
**spawn substrate**: how dispatch starts, drives, senses, and recovers
implementers as persistent herdr panes instead of in-process background agents.
Everything else — the claim protocol, queue rules, `config` semantics, the
Integration steps, the permission-stall protocol, and Phase 4 reporting — is
UNCHANGED and lives in `SKILL.md`; this file defers back to it by name and never
restates it. The ops kit `pm.py` SHIPS INSIDE THIS PLUGIN (it is not in the target repo and
is not fetched from anywhere at runtime — it is vendored under this skill's
`scripts/`). Because the orchestrator's cwd is the target repo, you must resolve
its absolute path into `$PM` at preflight (Step 2) and invoke `python3 "$PM"`
everywhere. Use its confirmed flags verbatim (see this skill's `scripts/VENDORED.md`)
— never invent a flag. (herdr client 0.6.10, protocol 13.)

Conventions (set once at the top of every fire):

- `PM` — absolute path to the plugin's vendored `pm.py` (it is NOT in the target
  repo, so a bare `skills/dispatch/scripts/pm.py` will not resolve). Set once at
  preflight (Step 2) and use `python3 "$PM"` everywhere:

  ```
  PM="${CLAUDE_PLUGIN_ROOT:-}/skills/dispatch/scripts/pm.py"
  [ -f "$PM" ] || PM=$(ls -t ~/.claude/plugins/cache/*/pg-plugin/*/skills/dispatch/scripts/pm.py \
                       ~/.claude/plugins/marketplaces/*/skills/dispatch/scripts/pm.py 2>/dev/null | head -1)
  ```

- `ORCH` — the orchestrator's own `terminal_id` (a `term_…`). NOT `$HERDR_PANE_ID`
  (that is a `p_NN` pane id which `pm.py --term` rejects). Resolve it from the pane
  whose cwd is the repo root, and pass `--term "$ORCH"` to `spawn-exec` and `lanes`
  (it tells them which workspace/repo to act in):

  ```
  ORCH=$(herdr pane list | python3 -c "import sys,json,os; r=os.path.realpath('.'); \
    print(next(p['terminal_id'] for p in json.load(sys.stdin)['result']['panes'] \
    if os.path.realpath(p.get('cwd','')) == r))")
  ```

- `SLUG=$(basename "$PWD" | tr -c 'A-Za-z0-9' '-')` — repo slug for the cache path.
- Two DIFFERENT executor ids, both returned by `spawn-exec` (`exec_term` and
  `exec_pane` in its JSON) — record BOTH, use each in its own place, never
  rename one to the other:
  - `<exec_term>` = the executor's `terminal_id`. Use it for every `pm.py`
    `--term` (`dispatch`, `read`, `keys`, `status`).
  - `<exec_pane>` = the executor's `pane_id`. Use it for any RAW herdr pane
    command (`herdr wait output <pane>`).
- The completion marker is minted BY `pm.py dispatch --file` (Step 5), which
  returns `marker` + an anchored `wait_regex` — record and reuse those VERBATIM;
  never hand-mint or reuse a marker (a reused marker false-fires the next wait).

## Step 1 — When this file applies (the gate)

Follow this file ONLY when `index.yaml` `config.execution: herdr`. With
`execution` absent or `native`, the native in-process-agent path in `SKILL.md`
(Phase 3 / Re-entrancy) is authoritative — ignore this file entirely.

Three preconditions, checked at the gate:

1. **herdr reachable** — `capabilities` reports `ok` (Step 2). Unreachable →
   degrade to native + warn; do not hard-fail.
2. **Orchestrator inside a herdr pane** — you resolve `ORCH` to your own pane's
   `terminal_id` (Conventions; NOT `$HERDR_PANE_ID`, a `p_NN` id `pm.py` rejects).
   If `ORCH` resolution finds nothing (a plain `/loop` terminal not registered as
   a herdr pane), use the `terminal_id` of any agent pane in the repo's herdr
   workspace as `--term`, or degrade to native. Never override `$HERDR_SOCKET_PATH`.
3. **Claim protocol + queue rules unchanged** — every `index.yaml` write still
   goes through the `SKILL.md` claim protocol from the `<base>` checkout;
   WIP cap, ready/`depends_on`/`priority`, the stale-claim rule, and "implementers
   never touch `docs/goals/`" are still law. herdr changes only HOW an
   implementer runs, never WHO writes the ledger.

## Step 2 — Phase 0: preflight (once per session)

1. **Resolve the kit + your pane.** Set `$PM` (the plugin's `pm.py`) and `$ORCH`
   (your `terminal_id`) per Conventions. Empty `$PM` → the plugin isn't installed
   where expected; report and degrade to native. Optional, one-time per machine
   (recommended — sharpens blocked/working/done detection):
   `herdr integration install claude`.
2. **Probe herdr.** `python3 "$PM" capabilities`. If
   the result is `ok:false`, or `server.running:false` (server stopped — it
   still reports client/protocol), or the protocol/version is too old for the
   primitives below → **degrade to native mode** (run the `SKILL.md` native
   path for the rest of the session) and note the degrade + reason in the
   Phase 4 report. This is a warn, never a hard-fail.
3. **Merge-rights preflight.** `merge: auto` → the SAME `gh pr merge` allow-rule
   preflight defined in `SKILL.md` (Integration), surfaced here only so it isn't
   missed in herdr's Phase 0 — once per session, before the first integration. Not
   a second preflight.
4. **Load the runtime cache.** Read this session's mission cache at
   `~/.local/state/pg-dispatch/<SLUG>/missions.json` — a JSON object
   `{ "<goalId>": {branch, worktree, term, pane, session, marker, wait_regex, started, respawned} }`
   (full schema in Step 9). Absent → start with an empty `{}`. This Tier-2 cache is machine-local and
   rebuildable (Step 9); it is never the source of truth.

## Step 3 — Phase 1: reconcile (every fire)

Run `python3 "$PM" lanes --term "$ORCH" --branch-prefix goal/`
to get the worktree×agent reconcile filtered to `goal/` branches (foreign
worktrees are counted but ignored). In herdr mode **"live agent" = a
`lanes`-visible pane on `goal/<id>`** — cross-session visible, strictly better
than native's "spawned this session". Classify each `in_progress` goal **in
this order — a lane with no live agent is NOT automatically a zombie.** A goal
that just finished its `/goal` goes idle, so `lanes` reports `zombie: true` for
it even though the work is done; the marker/commit checks below therefore take
precedence over the zombie rule:

- **marker fired (done)** — `python3 "$PM" read --term "<exec_term>" --session
  "<sid>"` for the mission's pane and grep its output with the recorded
  `wait_regex` (anchored — the marker alone on a line), NEVER a bare substring:
  the dispatched pointer contains the marker string, so a substring grep
  false-fires on the prompt echo; only the agent's own final standalone print
  counts. Present → Step 8 (Phase 5). (Same authoritative check as Step 6.)
- **committed-but-unintegrated** — no marker, but commits exist on `goal/NNN`
  (`git ls-remote origin goal/NNN`, or `git -C <worktree> log`) and it is not
  yet integrated → Step 8 (Phase 5). This is the pane-gone-but-work-landed case.
- **live** — lane present, agent `working`/`idle`, and no marker yet → leave it;
  if the lane reports `blocked` → Step 7 (Phase 4b).
- **zombie (truly dead)** — `lanes` shows the `goal/NNN` worktree but no live
  agent, AND there is no marker and no committed work to integrate → the
  implementer died before finishing. If the mission entry already has
  `respawned: true` → it died a second time → set `blocked` (claim protocol)
  with the reason. Otherwise respawn ONCE via Step 5 with `--reuse`, reuse the
  worktree, note in the contract what is already committed on `goal/NNN`, and
  set `respawned: true` on the entry. (`missions.json` is machine-local, so on a
  fresh session this counter is gone — the `SKILL.md` commit-since-`claimed`
  heuristic is the cross-session backstop: with no cache entry, a zombie whose
  `goal/NNN` already has commits that did NOT advance since the prior fire is
  treated as a second death → `blocked`, not a blind re-spawn. Only an empty or
  freshly-advancing branch earns the one respawn.)

Heal `index.yaml`↔reality drift via the `SKILL.md` stale-claim rule (an
`in_progress` entry with no live lane and no open PR is a dead/stale claim).
Also **shepherd open factory PRs exactly as `SKILL.md` Phase 1** (PR merged /
CI red / unaddressed review comments / green+addressed / newly opened) —
unchanged; do that before claiming new work so finished work always beats new.

## Step 4 — Phase 2: capacity & claim

**PAUSE guard first:** if `~/.local/state/pg-dispatch/PAUSE` exists, skip this
phase AND Phase 3 entirely (claiming pushes via `git`, which the brake does not
auto-block — claiming now would strand an `in_progress` goal you cannot spawn).
Reconcile + report only until it is `rm`-ed.

`free = config.wip − live implementers` (count `goal/`-lane live agents from
Step 3). For each free slot, pick the next ready `not_started` goal honoring
`priority`, `depends_on`, and per-goal `base:`/`skills:` (ready = `not_started`
AND every `depends_on` entry `completed`, per `SKILL.md` Phase 2). **Claim it
via the `SKILL.md` claim protocol BEFORE spawning** — one goal per round, the
pushed status flip is the claim. `free == 0` → skip spawning this fire; still
monitor (Step 6) and integrate (Step 8).

## Step 5 — Phase 3: spawn (per claimed goal)

Per claimed goal `NNN` (resolved `<base>` = per-goal `base:` else `config.base`):

1. **Fetch.** `git fetch origin`.
2. **Spawn the executor pane** (native worktree = git worktree + workspace +
   tab in one call; fresh `claude --dangerously-skip-permissions`):

   ```
   python3 "$PM" spawn-exec \
     --term "$ORCH" --slug "$SLUG" \
     --branch "goal/NNN" --base "origin/<base>" --backend claude
   ```

   On a **respawn** (zombie from Step 3), add `--reuse` to open the existing
   `goal/NNN` worktree instead of creating a fresh one. From its JSON, record
   BOTH the executor's `exec_term` (terminal_id → `<exec_term>`) and `exec_pane`
   (pane_id → `<exec_pane>`), plus the session id (`<sid>`) and `worktree_path` —
   you need all of them for the later calls to this pane.
3. **Clear the folder-trust prompt.** A fresh `claude` in a new worktree opens
   on Claude Code's "Is this a project you trust?" gate; `spawn-exec` reports it
   as `trust_accepted: false`. Clear it BEFORE any dispatch (a brief sent into
   the trust widget is lost). `read` to confirm, then accept the pre-highlighted
   "Yes, I trust this folder" with `keys`:

   ```
   python3 "$PM" read --term "<exec_term>"          # see the prompt
   python3 "$PM" keys --term "<exec_term>" Enter    # option 1 pre-highlighted
   ```

   Re-read until the composer (`❯`) is ready. When `trust_accepted: true` (e.g.
   `--reuse` of an already-trusted worktree) and no prompt is present, skip this.
4. **Set the model** (only if `config.model != inherit`). `spawn-exec` has NO
   `--model` flag — the backend launches as plain `claude`. Send the model
   selector into the fresh pane FIRST:

   ```
   python3 "$PM" dispatch \
     --term "<exec_term>" --text "/model <config.model>"
   ```

5. **Write the mission brief to a file.** Compose the implementer contract as
   **plain prose** (there is NO `/goal` command to send — the fresh claude just
   executes the brief) and write it to
   `~/.local/state/pg-dispatch/<SLUG>/NNN-brief.md`. Do NOT put a `TASK_DONE_…`
   line in the file — `pm.py` adds the marker itself; a bare marker in the body
   false-fires the wait. The brief tells the agent to:
   - **Read `docs/goals/NNN.md`** and satisfy its "Goal contract" end to end
     (bulk detail lives there, in the worktree).
   - It is on branch **`goal/NNN`** in an isolated worktree from `origin/<base>`.
   - **Mandatory skills** (Skill tool): `config.skills` + the goal frontmatter's
     `skills:` + `writing-plans` if >2 files + `test-driven-development` for every
     code change + `verification-before-completion` before claiming done.
   - **Never edit `docs/goals/`** — the orchestrator owns queue state.
   - **Commit and push `goal/NNN`.**
   - Per `config.merge`: `pr` → open a PR targeting `<base>` whose body contains
     "Goal: NNN" (plain-language summary + verification evidence); `auto` → leave
     it for the orchestrator. Never self-merge.
   - On a **respawn**, add a line naming what is already committed on `goal/NNN`.
6. **Dispatch the brief.** `dispatch --file` mints a UNIQUE marker, sends a short
   "Read <brief> and execute it fully; when done and verified print <marker> on
   its own line" pointer, and verifies the pane went `working`:

   ```
   python3 "$PM" dispatch --term "<exec_term>" \
     --file ~/.local/state/pg-dispatch/<SLUG>/NNN-brief.md
   ```

   From the JSON, record `marker` and the anchored `wait_regex` VERBATIM — never
   hand-build them. `dispatch` refuses a `working`/`blocked` pane (clear the trust
   prompt in item 3 first); that refusal is expected monitor discipline, never
   re-send to a busy pane.
7. **Record the mission** to `~/.local/state/pg-dispatch/<SLUG>/missions.json`:
   `"NNN": {branch: "goal/NNN", worktree: "<worktree_path>", term: "<exec_term>",
   pane: "<exec_pane>", session: "<sid>", marker: "<marker>",
   wait_regex: "<wait_regex>", started: "<date>", respawned: false}` —
   `marker`/`wait_regex` are copied from the dispatch output; set
   `respawned: true` when you re-`--reuse` a zombie.

## Step 6 — Phase 4: monitor (non-blocking)

The fire must stay short, and it is idempotent — never block the whole fire on a
wait, and never depend on a background process's result surviving to the next
fire. So per live mission, the **authoritative completion check happens fresh
EVERY fire** by reading the pane, not by trusting a backgrounded wait:

1. **Completion check (authoritative, every fire).** Read the pane and grep its
   output with the mission's recorded `wait_regex` (the anchored marker pattern
   pm.py returned at dispatch — marker alone on a line):

   ```
   python3 "$PM" read --term "<exec_term>" --session "<sid>" \
     | grep -E "<wait_regex>"
   ```

   Match ONLY the anchored pattern — NEVER a bare substring. The pointer pm.py
   dispatched contains the marker string ("…print <marker>…"), so a substring
   grep matches that echo and false-fires; only the agent's own final standalone
   print counts. Match present → Step 8 (Phase 5). This re-derives completion
   from current reality each fire, so a marker printed between fires is never lost.
2. **Agent status** comes from the Step 3 `lanes` result already gathered — read
   `agent_status` for this mission's `goal/NNN` lane: `working` → leave it for
   the next fire; `blocked` → Step 7 (Phase 4b). (Marker is handled by step 1
   above, not by `agent_status`.)
3. **Optional in-turn wake-up hint** (NON-authoritative — never the primary
   mechanism): if you want this turn to wake the moment a marker prints rather
   than waiting for the next fire, you may background a wait:

   ```
   herdr wait output "<exec_pane>" --match "<wait_regex>" --regex --timeout 600000 &
   ```

   (positional `<exec_pane>`; `<wait_regex>` is the recorded anchored pattern, so
   the prompt echo doesn't wake it.) Its
   result is a convenience only — a raw wait can miss a marker printed between
   re-arms, and a background process's result is lost across fires; the step-1
   read+grep is what actually decides completion.
4. **Set sidebar visibility:**

   ```
   python3 "$PM" status --term "<exec_term>" --text "goal NNN"
   ```

   (`status --term <exec_term> --text`, ≤24 chars; the pane LABEL never changes —
   this is the channel that does.)

## Step 7 — Phase 4b: tiered block handling

Gated on `config.autonomy` ∈ `conservative | balanced | bold`, default
`balanced`. First capture the question:

```
python3 "$PM" read --term "<exec_term>" --session "<sid>"
```

(identity-safe pane read — resolve `--term` + `--session` so you read YOUR pane,
never a stale id.)

- **Tier 1 — auto-answer.** The question is answerable from the goal contract +
  the repo's CLAUDE.md/AGENTS.md + a quick recon. **A `blocked` pane is answered
  with `keys`, not `dispatch`** — `dispatch` refuses a `blocked` pane on purpose
  (text sent there could ESC-cancel the question widget). Claude's question is a
  selectable widget: from the `pm.py read` output, choose the option, then drive
  the widget with arrow keys + Enter:

  ```
  python3 "$PM" keys --term "<exec_term>" --session "<sid>" Down Enter
  ```

  (herdr key vocab: `Esc Up Down Left Right Tab Enter`; repeat `Down`/`Up` to land
  on the chosen option before `Enter`.) The agent resumes. Use `dispatch --text`
  ONLY for an idle/working pane (a nudge), never to answer a block.
  `autonomy: conservative` lowers the bar to escalate (escalate sooner); `bold`
  raises it (auto-answer more); `balanced` (default) is the behavior described
  here.
- **Tier 2 — escalate.** A genuine product/scope call that is not yours to
  decide:
  1. herdr toast:
     `python3 "$PM" notify --title "goal NNN blocked" --body "<question>"`
     (best-effort; a disabled/rate-limited toast is reported, not a failure).
  2. Send the PushNotification per `SKILL.md` Phase 4 (the stalled-factory
     notification — one per distinct blocker set).
  3. Mark the goal `blocked` via the claim protocol with the question as the
     `reason`. This frees the wip slot so the factory keeps moving.

## Step 8 — Phase 5: verify → push → integrate → cleanup

1. **Verify git reality** in `worktree_path`: confirm commits exist on
   `goal/NNN`, then run the goal's acceptance commands there and SHOW the
   output. A marker with no commits, or a failing verify, is not done →
   respawn-once (Step 5 `--reuse`) or `blocked` per the Step 3 zombie rule.
2. **Push.** The implementer pushes `goal/NNN`; the orchestrator confirms with
   `git ls-remote origin goal/NNN` (non-empty). Committed-but-unpushed → the
   orchestrator pushes from the worktree.
3. **Integrate per `config.merge`:**
   - `pr` → open a PR targeting `<base>` with body "Goal: NNN", surface it
     under needs-you, **do not merge**.
   - `auto` → run the `SKILL.md` Integration steps VERBATIM: orchestrator-only,
     one goal at a time, sync-with-current-base then re-verify before the
     `gh pr merge`. Substantive conflict → `blocked`. A harness merge-denial →
     keep the goal `in_progress` (hold its slot) per the `SKILL.md`
     permission-stall protocol — never `blocked`.
4. **Complete.** Flip `completed` via the claim protocol. Then clean up:
   - Find the lane workspace id:
     `python3 "$PM" lanes --term "$ORCH" --branch-prefix goal/`
     → take the lane's workspace id for `goal/NNN` → `<lane_ws>`.
   - `herdr worktree remove --workspace "<lane_ws>"` — for a native worktree
     lane this removes BOTH the checkout AND its workspace (which closes the
     lane's tab/pane), so no separate pane-close command is needed.
   - `git worktree prune`
   - **After a successful merge ONLY:** `git push origin --delete goal/NNN`.
   - Delete the `"NNN"` entry from `missions.json`.

## Step 9 — State, recovery & the PAUSE brake

Three tiers, reconciled **1 → 2 → 3** each fire; on disagreement Tier 1 +
Tier 3 win and Tier 2 is rebuilt:

| Tier | Where | Holds | Authority |
|---|---|---|---|
| 1 | `index.yaml` | claim status | Truth, cross-machine |
| 2 | `~/.local/state/pg-dispatch/<SLUG>/missions.json` | `goal → {branch, worktree, term, pane, session, marker, wait_regex, started, respawned}` | Runtime cache, machine-local |
| 3 | herdr (`lanes` = agent/worktree list) + git (branches/commits/PRs) | what's actually alive | Reality, always reconcilable |

**Recovery scenarios** (all reconstruct from ledger + git + live panes):

- **Orchestrator pane dies, server alive** → implementer panes keep running; a
  re-attached/fresh orchestrator runs `lanes`, rebuilds `missions.json` from the
  live panes + `index.yaml`, and resumes. No work lost.
- **Machine/server restart** → panes gone; `lanes` finds `goal/NNN` worktrees
  with no agent → zombies → respawn-once reusing committed work (Step 3), or
  shepherd the PR if one is already open.
- **State cache lost (new machine)** → `missions.json` is only a cache;
  reconstruct from `index.yaml` + git + any live panes. The claim ledger and
  branch commits are durable.
- **All-stop (human)** → `touch ~/.local/state/pg-dispatch/PAUSE` makes the
  mutating `pm.py` ops (`dispatch`, `keys`, `spawn-exec`) refuse with reason
  `"paused"`; the read-only ops (`capabilities`, `lanes`, `read`, `status`)
  still work, so a paused orchestrator can still reconcile and report. `rm` it
  to resume. **Check PAUSE before claiming:** the claim protocol pushes through
  `git` (not `pm.py`), so it is NOT auto-blocked — when PAUSE is present, skip
  Phase 2 (claim) and Phase 3 (spawn) entirely this fire so you never strand an
  `in_progress` goal with no pane. In-flight missions are left untouched;
  integration mutations also wait for the un-pause.

## Step 10 — Worktree hard-cases ("perfect" management)

1. **Respawn reuses the worktree.** A dead implementer's commits are valuable —
   respawn fresh ONCE with `spawn-exec --reuse` and a "here's what's already
   committed" note (Step 3/Step 5); dies again → `blocked`.
2. **Never create a second worktree on a checked-out branch.** Git refuses it;
   the unique `goal/NNN` per goal plus the `lanes` gate before create prevent it
   — `lanes` is the pre-create check.
3. **Cleanup discipline.** On complete/abandon: `herdr worktree remove
   --workspace <lane_ws>` + `git worktree prune` + delete the branch
   (`git push origin --delete goal/NNN` after merge only) — no orphans.
4. **Stale base at integration.** The orchestrator syncs-with-current-base and
   re-verifies before EVERY merge (`SKILL.md` Integration); substantive conflict
   → `blocked`.
5. **Parallel same-file collisions.** Isolated worktrees mean no mid-work
   contention; collisions surface only at serialized integration, where
   sync + re-verify catches them and `wip` bounds the blast radius.
