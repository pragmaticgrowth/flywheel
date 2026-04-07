/**
 * Session tools: continue, fork, list, search.
 *
 * continue + fork wrap `droid exec -s <id>` / `--fork <id>`.
 * list reads ~/.factory/sessions-index.json (raw cwd — no encoding needed).
 * search wraps `droid search <query> --json`.
 */

import { spawn } from "node:child_process";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { spawnDroidExec } from "../droid/exec.js";
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

export function registerSessionTools(server: McpServer): void {
  server.registerTool(
    "droid_session_continue",
    {
      description:
        "Continue an existing droid session by id — loads conversation history for context and runs the new prompt in the same thread. Equivalent to `droid exec -s <session_id> '<prompt>'`.",
      inputSchema: {
        session_id: z.string(),
        prompt: z.string(),
        cwd: z.string().optional(),
        model: z.string().optional(),
        auto: AutoLevelSchema.optional(),
        reasoning_effort: ReasoningEffortSchema.optional(),
        timeout_ms: z.number().int().positive().optional(),
      },
    },
    async ({
      session_id,
      prompt,
      cwd,
      model,
      auto,
      reasoning_effort,
      timeout_ms,
    }): Promise<McpToolResponse> => {
      try {
        const result = await spawnDroidExec(
          { session_id, prompt, model, auto, reasoning_effort },
          { cwd: resolveCwd(cwd), timeout_ms },
        );
        return execResultToToolResponse(result);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_session_fork",
    {
      description:
        "Fork an existing session into a new one, preserving its history up to the checkpoint. Useful for 'take a different approach from this point'. Returns the NEW session_id in the response metadata.",
      inputSchema: {
        session_id: z.string().describe("The session to fork from."),
        prompt: z.string(),
        cwd: z.string().optional(),
        model: z.string().optional(),
        auto: AutoLevelSchema.optional(),
        reasoning_effort: ReasoningEffortSchema.optional(),
        timeout_ms: z.number().int().positive().optional(),
      },
    },
    async ({
      session_id,
      prompt,
      cwd,
      model,
      auto,
      reasoning_effort,
      timeout_ms,
    }): Promise<McpToolResponse> => {
      try {
        const result = await spawnDroidExec(
          {
            fork_session_id: session_id,
            prompt,
            model,
            auto,
            reasoning_effort,
          },
          { cwd: resolveCwd(cwd), timeout_ms },
        );
        return execResultToToolResponse(result);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
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

        const result = await runDroidSearch(args, {
          cwd: resolveCwd(cwd),
          timeout_ms: timeout_ms ?? 120_000,
        });

        if (!result.ok) {
          return createErrorResponse(
            `droid search failed: ${result.error ?? result.stderr.trim()}`,
          );
        }

        try {
          const parsed = JSON.parse(result.stdout);
          return createJsonResponse(parsed);
        } catch {
          return createJsonResponse({ raw_stdout: result.stdout });
        }
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}

interface DroidSearchResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  error?: string;
}

async function runDroidSearch(
  args: string[],
  opts: { cwd: string; timeout_ms: number },
): Promise<DroidSearchResult> {
  return new Promise((resolve) => {
    const child = spawn("droid", args, {
      cwd: opts.cwd,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
    }, opts.timeout_ms);

    child.stdout?.on("data", (d: Buffer) => {
      stdout += d.toString("utf8");
    });
    child.stderr?.on("data", (d: Buffer) => {
      stderr += d.toString("utf8");
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        stdout,
        stderr,
        exit_code: null,
        error: `spawn error: ${err.message}`,
      });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({
        ok: code === 0,
        stdout,
        stderr,
        exit_code: code,
        error: code !== 0 ? stderr.trim() || `exit ${code}` : undefined,
      });
    });
  });
}
