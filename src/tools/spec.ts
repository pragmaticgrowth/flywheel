/**
 * droid_spec — wrap `droid exec --use-spec [...]`. Spec mode is droid's
 * structured planning workflow that produces a written spec before execution.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DEFAULT_MODEL, DEFAULT_SPEC_MODEL } from "../droid/defaults.js";
import { spawnDroidExec } from "../droid/exec.js";
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
        "Run droid in spec mode (`droid exec --use-spec [--spec-model <m>] [--spec-reasoning-effort <r>] '<prompt>'`). Spec mode produces a structured plan before execution — useful for non-trivial features where you want to lock alignment before any code is written.",
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
        timeout_ms: z.number().int().positive().optional(),
      },
    },
    async ({
      prompt,
      cwd,
      spec_model,
      spec_reasoning_effort,
      model,
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
