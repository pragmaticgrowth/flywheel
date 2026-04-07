/**
 * Register the generic `droid_exec` MCP tool.
 *
 * One-to-one passthrough: every flag from droid_exec --help is exposed as a
 * typed parameter. For convenience wrappers (research, review, etc.) see
 * src/tools/presets.ts.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { DEFAULT_MODEL } from "../droid/defaults.js";
import { spawnDroidExec } from "../droid/exec.js";
import type { DroidExecFlags } from "../droid/flags.js";
import { DroidExecInputShape, type DroidExecInput } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createUnexpectedErrorResponse,
  execResultToToolResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerDroidExec(server: McpServer): void {
  server.registerTool(
    "droid_exec",
    {
      description:
        "Generic droid-exec passthrough. Runs `droid exec [flags] <prompt>` with every CLI flag exposed as a typed parameter. Defaults output to stream-json and inherits the MCP server's cwd unless overridden. Prefer droid_research / droid_review_code / etc. for common workflows.",
      inputSchema: DroidExecInputShape,
    },
    async (input: DroidExecInput): Promise<McpToolResponse> => {
      try {
        // Drop tool-level fields (cwd, timeout_ms) — cwd goes to spawn opts,
        // timeout_ms is server-side. Everything else maps 1:1 onto flags.ts.
        const { cwd, timeout_ms, ...rest } = input;
        const flags: DroidExecFlags = {
          ...rest,
          // Force a custom default — droid's built-in fallback is
          // claude-opus-4-6, which we never want to use.
          model: input.model ?? DEFAULT_MODEL,
        };

        const result = await spawnDroidExec(flags, {
          cwd: resolveCwd(cwd),
          timeout_ms,
        });

        return execResultToToolResponse(result);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
