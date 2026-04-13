/**
 * Droid provider adapter — wraps spawnDroidExec into the unified RunResult.
 */

import { spawnDroidExec } from "../droid/exec.js";
import type { RunOptions, RunResult } from "./types.js";

export async function runDroid(opts: RunOptions): Promise<RunResult> {
  const result = await spawnDroidExec(
    {
      prompt: opts.prompt,
      model: opts.model,
      auto: opts.auto,
      reasoning_effort: opts.reasoning_effort,
      session_id: opts.session_id,
      tags: opts.tags,
      system_prompt_file: opts.system_prompt_file,
    },
    {
      cwd: opts.cwd,
      timeout_ms: opts.timeout_ms,
    },
  );

  if (result.ok) {
    return {
      provider: "droid",
      ok: true,
      text: result.parsed.text || "",
      duration_ms: result.duration_ms,
      session_id: result.parsed.session_id,
      model: result.parsed.model || opts.model,
    };
  }

  return {
    provider: "droid",
    ok: false,
    text: "",
    error_message: result.error_message || "droid exec failed",
    duration_ms: result.duration_ms,
    model: opts.model,
  };
}
