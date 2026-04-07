/**
 * Session tools: continue, fork, list, search. Continue + fork wrap
 * `droid exec -s <id>` / `--fork <id>`. List reads sessions-index.json
 * (raw cwd, no encoding). Search shells out to `droid search <query> --json`.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { DEFAULT_MODEL } from "../droid/defaults.js";
import {
  runDroidProcess,
  spawnDroidExec,
  type DroidProcessOptions,
} from "../droid/exec.js";
import type { DroidExecFlags } from "../droid/flags.js";
import { listSessions } from "../droid/sessions.js";
import { AutoLevelSchema, ReasoningEffortSchema } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createJsonResponse,
  createUnexpectedErrorResponse,
  execResultToToolResponse,
  type McpToolResponse,
} from "../utils/errors.js";

interface SessionExecInput {
  prompt: string;
  cwd?: string;
  model?: string;
  auto?: z.infer<typeof AutoLevelSchema>;
  reasoning_effort?: z.infer<typeof ReasoningEffortSchema>;
  timeout_ms?: number;
}

async function runSessionExec(
  extra: Pick<DroidExecFlags, "session_id" | "fork_session_id">,
  input: SessionExecInput,
): Promise<McpToolResponse> {
  try {
    const result = await spawnDroidExec(
      {
        ...extra,
        prompt: input.prompt,
        model: input.model ?? DEFAULT_MODEL,
        auto: input.auto,
        reasoning_effort: input.reasoning_effort,
      },
      { cwd: resolveCwd(input.cwd), timeout_ms: input.timeout_ms },
    );
    return execResultToToolResponse(result);
  } catch (err) {
    return createUnexpectedErrorResponse(err);
  }
}

const sessionExecShape = {
  prompt: z.string(),
  cwd: z.string().optional(),
  model: z.string().optional(),
  auto: AutoLevelSchema.optional(),
  reasoning_effort: ReasoningEffortSchema.optional(),
  timeout_ms: z.number().int().positive().optional(),
};

export function registerSessionTools(server: McpServer): void {
  server.registerTool(
    "droid_session_continue",
    {
      description:
        "Continue an existing droid session by id — loads conversation history for context and runs the new prompt in the same thread. Equivalent to `droid exec -s <session_id> '<prompt>'`.",
      inputSchema: { session_id: z.string(), ...sessionExecShape },
    },
    async ({ session_id, ...input }) => runSessionExec({ session_id }, input),
  );

  server.registerTool(
    "droid_session_fork",
    {
      description:
        "Fork an existing session into a new one, preserving its history up to the checkpoint. Useful for 'take a different approach from this point'. The NEW session_id shows up in the response metadata.",
      inputSchema: {
        session_id: z.string().describe("The session to fork from."),
        ...sessionExecShape,
      },
    },
    async ({ session_id, ...input }) =>
      runSessionExec({ fork_session_id: session_id }, input),
  );

  server.registerTool(
    "droid_session_list",
    {
      description:
        "List droid sessions from ~/.factory/sessions-index.json, filtered by cwd by default (pass all=true to see every session). Returns session_id, title, mtime, messages_count — sorted newest first.",
      inputSchema: {
        cwd: z.string().optional(),
        all: z
          .boolean()
          .optional()
          .describe("Ignore the cwd filter and return every session."),
        search: z
          .string()
          .optional()
          .describe("Case-insensitive substring filter on the session title."),
        limit: z.number().int().positive().optional(),
      },
    },
    async ({ cwd, all, search, limit }): Promise<McpToolResponse> => {
      try {
        const sessions = await listSessions({
          cwd: resolveCwd(cwd),
          all,
          search,
          limit,
        });
        return createJsonResponse({ count: sessions.length, sessions });
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_session_search",
    {
      description:
        "Full-text search across droid sessions via `droid search <query> --json`. Runs from the given (or default) cwd, so results are scoped to sessions in that project by default.",
      inputSchema: {
        query: z.string(),
        cwd: z.string().optional(),
        kind: z
          .enum(["message_text", "document", "tool_use", "tool_result", "all"])
          .optional(),
        limit_sessions: z.number().int().positive().optional(),
        limit_hits: z.number().int().positive().optional(),
        context_chars: z.number().int().positive().optional(),
        reindex: z.boolean().optional(),
        timeout_ms: z.number().int().positive().optional(),
      },
    },
    async ({
      query,
      cwd,
      kind,
      limit_sessions,
      limit_hits,
      context_chars,
      reindex,
      timeout_ms,
    }): Promise<McpToolResponse> => {
      try {
        const args = ["search", query, "--json"];
        if (kind) args.push("--kind", kind);
        if (limit_sessions !== undefined)
          args.push("--limit-sessions", String(limit_sessions));
        if (limit_hits !== undefined)
          args.push("--limit-hits", String(limit_hits));
        if (context_chars !== undefined)
          args.push("--context-chars", String(context_chars));
        if (reindex) args.push("--reindex");

        const opts: DroidProcessOptions = {
          cwd: resolveCwd(cwd),
          timeout_ms: timeout_ms ?? 120_000,
        };
        const proc = await runDroidProcess(args, opts);

        if (proc.spawn_error !== null) {
          return createErrorResponse(`droid search: ${proc.spawn_error}`);
        }
        if (proc.timed_out) {
          return createErrorResponse(
            `droid search timed out after ${opts.timeout_ms}ms`,
          );
        }
        if (proc.exit_code !== 0) {
          return createErrorResponse(
            `droid search failed: ${proc.stderr.trim() || `exit ${proc.exit_code}`}`,
          );
        }

        // `droid search --json` may return either a top-level array of
        // hits or an object — normalize to an object so structuredContent
        // stays a JSON object.
        try {
          const parsed: unknown = JSON.parse(proc.stdout);
          if (Array.isArray(parsed)) {
            return createJsonResponse({ count: parsed.length, hits: parsed });
          }
          return createJsonResponse(parsed);
        } catch {
          return createJsonResponse({ raw_stdout: proc.stdout });
        }
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
