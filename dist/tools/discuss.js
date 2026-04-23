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
import { getCodexMcpClient } from "../codex/mcp-client.js";
import { resolveCwd } from "../utils/cwd.js";
import { createErrorResponse, createUnexpectedErrorResponse, } from "../utils/errors.js";
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
export function parseDiscussJson(text) {
    const empty = {
        risks: [],
        blockers: [],
        alternatives: [],
        missing: [],
    };
    const m = JSON_RE.exec(text);
    if (!m)
        return empty;
    try {
        const parsed = JSON.parse(m[1]);
        return {
            objective: typeof parsed.objective === "string" ? parsed.objective : undefined,
            risks: Array.isArray(parsed.risks) ? parsed.risks.filter((x) => typeof x === "string") : [],
            blockers: Array.isArray(parsed.blockers)
                ? parsed.blockers.filter((x) => typeof x === "string")
                : [],
            alternatives: Array.isArray(parsed.alternatives)
                ? parsed.alternatives.filter((x) => typeof x === "string")
                : [],
            missing: Array.isArray(parsed.missing) ? parsed.missing.filter((x) => typeof x === "string") : [],
            verdict: parsed.verdict === "proceed" ||
                parsed.verdict === "proceed-with-changes" ||
                parsed.verdict === "reconsider"
                ? parsed.verdict
                : undefined,
        };
    }
    catch {
        return empty;
    }
}
export function stripDiscussJsonBlock(text) {
    return text.replace(JSON_RE, "").trim();
}
const BODY_CONTRACT = `Reply with a short critique, then at the very end emit EXACTLY this JSON block:

<discuss-json>
{"objective":"<one sentence>","risks":["..."],"blockers":["..."],"alternatives":["..."],"missing":["..."],"verdict":"proceed"|"proceed-with-changes"|"reconsider"}
</discuss-json>`;
/**
 * Build the user-facing body for do_discuss. Pure function — easy to test.
 *
 * `prompt` is always the primary input. Optional `paths` and/or `base_ref`
 * give Codex additional code context to read/inspect itself before
 * answering (keeps MCP payload small, lets Codex correlate with
 * surrounding code).
 */
export function buildDiscussBody(input) {
    const pathsList = input.paths && input.paths.length > 0
        ? input.paths.map((p) => `- ${p}`).join("\n")
        : "";
    const pathspec = input.paths && input.paths.length > 0
        ? ` -- ${input.paths.map((p) => JSON.stringify(p)).join(" ")}`
        : "";
    const contextSections = [];
    if (input.base_ref) {
        contextSections.push(`Before responding, read the proposed changes by running:\n\`git diff ${input.base_ref}...HEAD${pathspec}\`\nin the working directory.`);
    }
    if (input.paths && input.paths.length > 0 && !input.base_ref) {
        contextSections.push(`Before responding, read the following file(s) or directories in the working directory to ground your critique:\n${pathsList}`);
    }
    const parts = [];
    if (contextSections.length > 0) {
        parts.push(contextSections.join("\n\n"));
        parts.push("---");
    }
    parts.push(input.prompt.trim());
    parts.push("---");
    parts.push(BODY_CONTRACT);
    return parts.join("\n\n");
}
export function registerDiscussTool(server) {
    server.registerTool("do_discuss", {
        description: "Discuss a plan, architecture, or approach with GPT-5.4 xHigh via a persistent Codex MCP backend. Sounding board for design decisions — returns a structured critique (objective, risks, blockers, alternatives, missing, verdict) plus the full markdown response. " +
            "Optional scope: pass `paths` (files Codex should read) or `base_ref` (e.g. \"main\" — Codex runs `git diff <ref>...HEAD [-- paths]` itself) to ground the discussion in code without embedding it in the prompt. " +
            "Pass `thread_id` to continue an existing discussion (follow-ups are ~10x faster than first turn). Read-only sandbox; does not write code.",
        inputSchema: {
            prompt: z
                .string()
                .describe("The plan, proposal, or question to discuss. Include constraints and prior decisions. For code discussions, prefer `paths` / `base_ref` over pasting diffs inline."),
            paths: z
                .array(z.string())
                .optional()
                .describe("File or directory paths for Codex to read from the working directory before responding. Keeps MCP payload small; Codex has read-only sandbox access so it can read any file in cwd."),
            base_ref: z
                .string()
                .optional()
                .describe('Git base ref (e.g. "main", "HEAD~3"). When set, Codex runs `git diff base_ref...HEAD [-- paths]` itself before responding. Combine with `paths` to scope the diff.'),
            thread_id: z
                .string()
                .optional()
                .describe("Existing Codex thread to continue. Omit to start a new discussion."),
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
    }, async (input) => {
        try {
            const client = getCodexMcpClient();
            const bodyWithContract = buildDiscussBody({
                prompt: input.prompt,
                paths: input.paths,
                base_ref: input.base_ref,
            });
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
                return createErrorResponse(`codex discuss reported an error.\nthread_id: ${result.thread_id || "(none)"}\n\n${result.text || "(no message)"}`);
            }
            const parsed = parseDiscussJson(result.text);
            const visible = stripDiscussJsonBlock(result.text);
            const meta = [];
            if (result.thread_id)
                meta.push(`thread_id: ${result.thread_id}`);
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
        }
        catch (err) {
            return createUnexpectedErrorResponse(err);
        }
    });
}
//# sourceMappingURL=discuss.js.map