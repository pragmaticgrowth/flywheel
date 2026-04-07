/**
 * droid_spec — wrap `droid exec --use-spec [...]`. Spec mode is droid's
 * structured planning workflow that produces a written spec before execution.
 *
 * NOTE on autonomy: spec mode is stochastic. After the model calls
 * ExitSpecMode to approve the spec, it may try to execute on the approved
 * plan (Create/Edit/Execute tool calls). Without an `auto` level set, those
 * calls are blocked, and depending on how the model recovers, droid can exit
 * nonzero. Pass auto: "low" (default) to let the model write the spec file
 * and perform simple file edits cleanly.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DEFAULT_MODEL, DEFAULT_SPEC_MODEL } from "../droid/defaults.js";
import { spawnDroidExec } from "../droid/exec.js";
import { AutoLevelSchema } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createUnexpectedErrorResponse,
  execResultToToolResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerSpecTool(server: McpServer): void {
  server.registerTool(
    "droid_spec",
    {
      description:
        "Run droid in spec mode (`droid exec --use-spec [--spec-model <m>] [--spec-reasoning-effort <r>] [--auto <level>] '<prompt>'`). Spec mode produces a structured plan BEFORE execution — useful for non-trivial features where you want to lock alignment first. Defaults to auto='low' so the model can write the approved spec file and perform simple edits; pass auto='high' for full autonomy or omit it explicitly to run read-only (which may cause spurious exit-1 failures if the model tries to follow through on its own spec).",
      inputSchema: {
        prompt: z.string(),
        cwd: z.string().optional(),
        spec_model: z
          .string()
          .optional()
          .describe("Model used during spec authoring."),
        spec_reasoning_effort: z.string().optional(),
        model: z
          .string()
          .optional()
          .describe("Model used outside spec mode (the executor)."),
        auto: AutoLevelSchema.optional().describe(
          "Autonomy level. Defaults to 'low' to prevent spurious blocked-tool exits. Pass 'high' for real work or null to force read-only (not recommended for spec).",
        ),
        timeout_ms: z.number().int().positive().optional(),
      },
    },
    async ({
      prompt,
      cwd,
      spec_model,
      spec_reasoning_effort,
      model,
      auto,
      timeout_ms,
    }): Promise<McpToolResponse> => {
      try {
        const result = await spawnDroidExec(
          {
            prompt,
            use_spec: true,
            spec_model: spec_model ?? DEFAULT_SPEC_MODEL,
            spec_reasoning_effort,
            model: model ?? DEFAULT_MODEL,
            auto: auto ?? "low",
          },
          { cwd: resolveCwd(cwd), timeout_ms },
        );
        return execResultToToolResponse(result);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
