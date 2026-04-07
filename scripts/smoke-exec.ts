/**
 * Manual smoke test for src/droid/exec.ts. Runs a real `droid exec` and
 * prints the parsed result. Invoke with:
 *
 *   npx tsx scripts/smoke-exec.ts
 *
 * Verifies:
 *   - spawn + stream-json parsing end-to-end
 *   - session_id capture from init event
 *   - text capture from completion event
 *   - ok: true on a normal run
 *
 * And a second run with a bad model to verify the exit-code failure path.
 */

import { spawnDroidExec } from "../src/droid/exec.js";

async function run(label: string, flags: Parameters<typeof spawnDroidExec>[0]) {
  console.log(`\n=== ${label} ===`);
  const result = await spawnDroidExec(flags);
  console.log(
    JSON.stringify(
      {
        ok: result.ok,
        failure: result.failure,
        error_message: result.error_message,
        exit_code: result.exit_code,
        signal: result.signal,
        duration_ms: result.duration_ms,
        argv: result.argv,
        parsed: {
          session_id: result.parsed.session_id,
          model: result.parsed.model,
          cwd: result.parsed.cwd,
          text: result.parsed.text,
          num_turns: result.parsed.num_turns,
          duration_ms: result.parsed.duration_ms,
          usage: result.parsed.usage,
          event_count: result.parsed.events.length,
          error_count: result.parsed.errors.length,
        },
        stdout_bytes: result.stdout.length,
        stderr_bytes: result.stderr.length,
        stderr_head: result.stderr.slice(0, 200),
      },
      null,
      2,
    ),
  );
}

async function main() {
  // Happy path: cheapest BYOK model, trivial prompt.
  await run("happy path — custom:glm-5-turbo", {
    prompt: "reply with exactly: hi",
    model: "custom:glm-5-turbo",
  });

  // Failure path: bad model. Should return ok: false, failure: nonzero_exit.
  await run("failure path — invalid model", {
    prompt: "hi",
    model: "not-a-real-model",
  });
}

main().catch((err) => {
  console.error("smoke test crashed:", err);
  process.exit(1);
});
