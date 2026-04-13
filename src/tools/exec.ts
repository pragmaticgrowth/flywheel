/**
 * do_exec — generic passthrough for power users.
 * Supports both droid and opencode backends via provider param.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import {
  resolveProvider,
  resolveModel,
  DEFAULT_MODELS,
  type ProviderName,
} from "../config.js";
import { spawnDroidExec } from "../droid/exec.js";
import type { DroidExecFlags } from "../droid/flags.js";
import { DroidExecInputShape, type DroidExecInput } from "../schemas/exec.js";
import { ProviderSchema } from "../schemas/preset.js";
import { runWithProvider } from "../providers/index.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createUnexpectedErrorResponse,
  execResultToToolResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerExecTool(server: McpServer): void {
  server.registerTool(
    "do_exec",
    {
      description:
        "Generic execution passthrough. For droid: every CLI flag is exposed. For opencode: runs `opencode run` with model + agent + prompt. Prefer specialized tools (do_research, do_review, etc.) for common workflows — they include intelligent prompts.",
      inputSchema: {
        ...DroidExecInputShape,
        provider: ProviderSchema,
      },
    },
    async (
      input: DroidExecInput & { provider?: string },
    ): Promise<McpToolResponse> => {
      try {
        const provider: ProviderName = resolveProvider(input.provider);

        if (provider === "opencode") {
          // Opencode path — simpler, only prompt + model + agent
          const model = resolveModel(
            input.model ?? DEFAULT_MODELS.opencode,
            "opencode",
          );
          const result = await runWithProvider("opencode", {
            prompt: input.prompt ?? "",
            model,
            cwd: resolveCwd(input.cwd),
            timeout_ms: input.timeout_ms,
            agent: undefined, // generic exec, no preset agent
          });

          const structured: Record<string, unknown> = {
            provider: "opencode",
            model: result.model,
            duration_ms: result.duration_ms,
          };

          if (!result.ok) {
            return {
              content: [
                { type: "text", text: result.error_message || "opencode run failed" },
              ],
              structuredContent: structured,
              isError: true,
            };
          }

          return {
            content: [{ type: "text", text: result.text }],
            structuredContent: structured,
          };
        }

        // Droid path — full flag passthrough
        const { cwd, timeout_ms, provider: _p, ...rest } = input;
        const flags: DroidExecFlags = {
          ...rest,
          model: resolveModel(
            input.model ?? DEFAULT_MODELS.droid,
            "droid",
          ),
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
