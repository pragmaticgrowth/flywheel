/**
 * do_audit — post-delivery auditor. Runs via the persistent Codex MCP
 * backend (same subprocess as do_discuss).
 *
 * Returns a fully-typed structured verdict: pass / concerns / blockers, plus
 * blockers, concerns, missed_requirements, strengths, next_steps — all as
 * typed arrays in structuredContent.
 *
 * Pass thread_id from a prior do_discuss to audit against the plan the same
 * Codex session already critiqued (it has the full prior conversation).
 *
 * Read-only sandbox. Default reasoning effort: high.
 */
import { z } from "zod";
import { getCodexMcpClient } from "../codex/mcp-client.js";
import { resolveCwd } from "../utils/cwd.js";
import { createErrorResponse, createUnexpectedErrorResponse, } from "../utils/errors.js";
const AUDIT_SYSTEM = `You are a senior engineering auditor reviewing delivered work.

You will receive:
- The original plan or acceptance criteria (context).
- The diff or files that were actually delivered.

Evaluate the delivery against the plan. Produce a markdown report with these
sections in this exact order, then emit a JSON block at the very end:

## Verdict
One of: pass | concerns | blockers

## Blockers
Bullet list. Each item: file:line — one-sentence fix. Empty list if none.

## Concerns
Bullet list, same format.

## Missed Requirements
Anything from the plan not delivered. Empty if fully covered.

## Strengths
Specific things done well — one line each.

## Suggested Next Steps
Ordered, concrete, actionable.

Then emit EXACTLY this JSON block at the end (all arrays of strings):

<audit-json>
{"verdict": "pass" | "concerns" | "blockers", "blockers": ["..."], "concerns": ["..."], "missed_requirements": ["..."], "strengths": ["..."], "next_steps": ["..."]}
</audit-json>

Be direct. No preamble. No filler. If everything is fine, say "pass" and keep
the sections short but still emit the JSON block.`;
const JSON_RE = /<audit-json>\s*([\s\S]*?)\s*<\/audit-json>/;
export function parseAuditJson(text) {
    const empty = {
        blockers: [],
        concerns: [],
        missed_requirements: [],
        strengths: [],
        next_steps: [],
    };
    const m = JSON_RE.exec(text);
    if (!m)
        return empty;
    try {
        const parsed = JSON.parse(m[1]);
        const strArr = (v) => Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
        return {
            verdict: parsed.verdict === "pass" ||
                parsed.verdict === "concerns" ||
                parsed.verdict === "blockers"
                ? parsed.verdict
                : undefined,
            blockers: strArr(parsed.blockers),
            concerns: strArr(parsed.concerns),
            missed_requirements: strArr(parsed.missed_requirements),
            strengths: strArr(parsed.strengths),
            next_steps: strArr(parsed.next_steps),
        };
    }
    catch {
        return empty;
    }
}
export function stripAuditJsonBlock(text) {
    return text.replace(JSON_RE, "").trim();
}
export function registerAuditTool(server) {
    server.registerTool("do_audit", {
        description: "Audit delivered work with GPT-5.4 High via a persistent Codex MCP backend. Returns a fully typed structured verdict: verdict (pass/concerns/blockers), blockers[], concerns[], missed_requirements[], strengths[], next_steps[]. Pass thread_id from a prior do_discuss to audit against that same conversation (Codex remembers the plan it helped shape). Read-only sandbox.",
        inputSchema: {
            context: z
                .string()
                .describe("Original plan, acceptance criteria, or what was requested. Baseline for the audit."),
            diff: z
                .string()
                .describe("The delivered work — git diff, file contents, or description of changes."),
            thread_id: z
                .string()
                .optional()
                .describe("Existing Codex thread (e.g. from a prior do_discuss). If given, Codex audits with full prior conversation context."),
            model: z
                .string()
                .optional()
                .describe("Codex model override. Default: gpt-5.4."),
            reasoning_effort: z
                .enum(["minimal", "low", "medium", "high", "xhigh"])
                .optional()
                .describe("Reasoning depth. Default: high."),
            cwd: z
                .string()
                .optional()
                .describe("Working directory. Defaults to the MCP server's cwd."),
        },
    }, async (input) => {
        try {
            const client = getCodexMcpClient();
            // The JSON-emit contract must be in EVERY call body, not just the
            // first-turn system prompt — because this tool may audit on a
            // thread_id that was started by do_discuss (different JSON format)
            // or a prior do_audit. Restating the contract keeps the response
            // shape stable regardless of thread history.
            const BODY_CONTRACT = `Produce a markdown audit (## Verdict / ## Blockers / ## Concerns / ## Missed Requirements / ## Strengths / ## Suggested Next Steps), and at the very end emit EXACTLY this JSON block:

<audit-json>
{"verdict":"pass"|"concerns"|"blockers","blockers":["..."],"concerns":["..."],"missed_requirements":["..."],"strengths":["..."],"next_steps":["..."]}
</audit-json>`;
            const body = [
                "# Context (original plan / acceptance criteria)",
                input.context.trim(),
                "",
                "# Delivered work",
                input.diff.trim(),
                "",
                BODY_CONTRACT,
            ].join("\n");
            const prompt = input.thread_id
                ? body
                : `${AUDIT_SYSTEM}\n\n---\n\n${body}`;
            const model = input.model ?? "gpt-5.4";
            const reasoning = input.reasoning_effort ?? "high";
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
                return createErrorResponse(`codex audit reported an error.\nthread_id: ${result.thread_id || "(none)"}\n\n${result.text || "(no message)"}`);
            }
            const parsed = parseAuditJson(result.text);
            const visible = stripAuditJsonBlock(result.text);
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
                    blockers: parsed.blockers,
                    concerns: parsed.concerns,
                    missed_requirements: parsed.missed_requirements,
                    strengths: parsed.strengths,
                    next_steps: parsed.next_steps,
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
//# sourceMappingURL=audit.js.map