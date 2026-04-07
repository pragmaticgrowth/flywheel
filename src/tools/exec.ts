/**
 * Register the generic `droid_exec` MCP tool.
 *
 * One-to-one passthrough: every flag from droid_exec --help is exposed as a
 * typed parameter. For convenience wrappers (research, review, etc.) see
 * src/tools/presets.ts.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
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
        const flags: DroidExecFlags = {
          prompt: input.prompt,
          prompt_file: input.prompt_file,
          model: input.model,
          auto: input.auto,
          allow_unsafe: input.allow_unsafe,
          output_format: input.output_format,
          input_format: input.input_format,
          session_id: input.session_id,
          fork_session_id: input.fork_session_id,
          cwd: undefined, // flag-level --cwd; we pass cwd via spawn opts instead
          worktree: input.worktree,
          worktree_dir: input.worktree_dir,
          enabled_tools: input.enabled_tools,
          disabled_tools: input.disabled_tools,
          tags: input.tags,
          log_group_id: input.log_group_id,
          mission: input.mission,
          system_prompt: input.system_prompt,
          system_prompt_file: input.system_prompt_file,
          reasoning_effort: input.reasoning_effort,
          spec_model: input.spec_model,
          spec_reasoning_effort: input.spec_reasoning_effort,
          use_spec: input.use_spec,
          settings_file: input.settings_file,
          list_tools: input.list_tools,
        };

        const resolvedCwd = resolveCwd(input.cwd);

        const result = await spawnDroidExec(flags, {
          cwd: resolvedCwd,
          timeout_ms: input.timeout_ms,
        });

        return execResultToToolResponse(result);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
