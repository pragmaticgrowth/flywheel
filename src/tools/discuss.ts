/**
 * do_discuss — iterative plan/architecture discussion with GPT-5.4 via the
 * persistent `codex mcp-server` backend.
 *
 * First turn:  args { prompt }                    → codex tool
 * Follow-up:   args { prompt, thread_id }         → codex-reply tool
 *
 * The Codex subprocess persists across turns, so follow-up turns are 10x
 * faster than `codex exec` (no cold start, no config reload).
 *
 * Read-only sandbox — this tool is a thinking partner, not a coder.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getCodexMcpClient } from "../codex/mcp-client.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

const DISCUSS_SYSTEM = `You are a senior engineering reviewer acting as a sounding board.

When the user presents a plan, proposal, or approach:
1. Identify the core objective in one sentence.
2. Surface risks, blockers, and hidden assumptions — be specific, cite why.
3. Challenge choices that look weak. Propose concrete alternatives.
4. Call out what's missing (edge cases, rollback story, observability, tests).
5. End with a clear verdict: proceed / proceed with changes / reconsider.

Be direct. Short sentences. No cheerleading. If the plan is good, say so and
point out the strongest parts. If it's bad, say so and say why.

At the very end, always emit this JSON block (exact format, single line allowed):

<discuss-json>
{"objective": "<one sentence>", "risks": ["..."], "blockers": ["..."], "alternatives": ["..."], "missing": ["..."], "verdict": "proceed" | "proceed-with-changes" | "reconsider"}
</discuss-json>`;

const JSON_RE = /<discuss-json>\s*([\s\S]*?)\s*<\/discuss-json>/;

export interface DiscussStructured {
  objective?: string;
  risks: string[];
  blockers: string[];
  alternatives: string[];
  missing: string[];
  verdict?: "proceed" | "proceed-with-changes" | "reconsider";
}

export function parseDiscussJson(text: string): DiscussStructured {
  const empty: DiscussStructured = {
    risks: [],
    blockers: [],
    alternatives: [],
    missing: [],
  };
  const m = JSON_RE.exec(text);
  if (!m) return empty;
  try {
    const parsed = JSON.parse(m[1]) as Partial<DiscussStructured>;
    return {
      objective:
        typeof parsed.objective === "string" ? parsed.objective : undefined,
      risks: Array.isArray(parsed.risks) ? parsed.risks.filter((x) => typeof x === "string") : [],
      blockers: Array.isArray(parsed.blockers)
        ? parsed.blockers.filter((x) => typeof x === "string")
        : [],
      alternatives: Array.isArray(parsed.alternatives)
        ? parsed.alternatives.filter((x) => typeof x === "string")
        : [],
      missing: Array.isArray(parsed.missing) ? parsed.missing.filter((x) => typeof x === "string") : [],
      verdict:
        parsed.verdict === "proceed" ||
        parsed.verdict === "proceed-with-changes" ||
        parsed.verdict === "reconsider"
          ? parsed.verdict
          : undefined,
    };
  } catch {
    return empty;
  }
}

export function stripDiscussJsonBlock(text: string): string {
  return text.replace(JSON_RE, "").trim();
}

export function registerDiscussTool(server: McpServer): void {
  server.registerTool(
    "do_discuss",
    {
      description:
        "Discuss a plan, architecture, or approach with GPT-5.4 xHigh via a persistent Codex MCP backend. Sounding board for design decisions — returns a structured critique (objective, risks, blockers, alternatives, missing, verdict) plus the full markdown response. Pass thread_id to continue an existing discussion (follow-ups are ~10x faster than first turn). Read-only sandbox; does not write code.",
      inputSchema: {
        prompt: z
          .string()
          .describe(
            "The plan, proposal, diff, or question to discuss. Include context — acceptance criteria, constraints, prior decisions.",
          ),
        thread_id: z
          .string()
          .optional()
          .describe(
            "Existing Codex thread to continue. Omit to start a new discussion.",
          ),
        model: z
          .string()
          .optional()
          .describe("Codex model override. Default: gpt-5.4."),
        reasoning_effort: z
          .enum(["minimal", "low", "medium", "high", "xhigh"])
          .optional()
          .describe("Reasoning depth. Default: xhigh (deepest)."),
        cwd: z
          .string()
          .optional()
          .describe("Working directory. Defaults to the MCP server's cwd."),
      },
    },
    async (input): Promise<McpToolResponse> => {
      try {
        const client = getCodexMcpClient();

        // Restate the JSON contract in the body of every call so that
        // resumed threads — including ones that were first started by a
        // different tool (do_audit) — still emit the discuss JSON shape.
        const BODY_CONTRACT = `Reply with a short critique, then at the very end emit EXACTLY this JSON block:

<discuss-json>
{"objective":"<one sentence>","risks":["..."],"blockers":["..."],"alternatives":["..."],"missing":["..."],"verdict":"proceed"|"proceed-with-changes"|"reconsider"}
</discuss-json>`;

        const bodyWithContract = `${input.prompt}\n\n---\n${BODY_CONTRACT}`;

        const prompt = input.thread_id
          ? bodyWithContract
          : `${DISCUSS_SYSTEM}\n\n---\n\n${bodyWithContract}`;

        const model = input.model ?? "gpt-5.4";
        const reasoning = input.reasoning_effort ?? "xhigh";

        const result = await client.call({
          prompt,
          thread_id: input.thread_id,
          model,
          reasoning_effort: reasoning,
          sandbox: "read-only",
          approval_policy: "never",
          cwd: resolveCwd(input.cwd),
        });

        if (result.is_error) {
          return createErrorResponse(
            `codex discuss reported an error.\nthread_id: ${result.thread_id || "(none)"}\n\n${result.text || "(no message)"}`,
          );
        }

        const parsed = parseDiscussJson(result.text);
        const visible = stripDiscussJsonBlock(result.text);

        const meta: string[] = [];
        if (result.thread_id) meta.push(`thread_id: ${result.thread_id}`);
        meta.push(`model: ${model} (${reasoning})`);
        meta.push(`duration: ${Math.round(result.duration_ms / 100) / 10}s`);

        return {
          content: [
            { type: "text", text: `${visible}\n\n---\n${meta.join("\n")}` },
          ],
          structuredContent: {
            thread_id: result.thread_id,
            verdict: parsed.verdict,
            objective: parsed.objective,
            risks: parsed.risks,
            blockers: parsed.blockers,
            alternatives: parsed.alternatives,
            missing: parsed.missing,
            text: visible,
            model,
            reasoning_effort: reasoning,
            duration_ms: result.duration_ms,
          },
        };
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
