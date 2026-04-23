/**
 * do_cross_review — unified cross-model code review.
 * Runs the same review prompt through 3 models from different training
 * lineages in parallel and merges findings. Works with both droid and opencode.
 */
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { resolveProvider, CROSS_REVIEW_MODELS, labelFor, } from "../config.js";
import { runWithProvider } from "../providers/index.js";
import { buildCrossReviewPrompt } from "../prompts/index.js";
import { CrossReviewInputShape, } from "../schemas/cross-review.js";
import { resolveCwd } from "../utils/cwd.js";
import { createErrorResponse, createUnexpectedErrorResponse, } from "../utils/errors.js";
const REVIEWER_PROFILE = join(homedir(), ".factory", "droids", "code-reviewer.md");
const DEFAULT_TIMEOUT_MS = 240_000;
export function registerCrossReviewTool(server) {
    server.registerTool("do_cross_review", {
        description: "Cross-model code review — runs the same review through 3 different model families in parallel and merges findings. Different training lineages have different blind spots, catching 3-5x more issues combined. Includes structured grounding rules to prevent hallucinated findings.",
        inputSchema: CrossReviewInputShape,
    }, async (input) => {
        try {
            const provider = resolveProvider(input.provider);
            const models = input.models ?? CROSS_REVIEW_MODELS[provider];
            if (models.length === 0) {
                return createErrorResponse("models array must not be empty");
            }
            // Droid: check profile exists
            if (provider === "droid") {
                try {
                    await access(REVIEWER_PROFILE);
                }
                catch {
                    return createErrorResponse(`code-reviewer profile not found at ${REVIEWER_PROFILE}`);
                }
            }
            const cwd = resolveCwd(input.cwd);
            const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS;
            const reviewPrompt = buildCrossReviewPrompt(input.prompt);
            const agent = input.agent ?? "review";
            const results = await Promise.allSettled(models.map(async (model) => {
                const result = await runWithProvider(provider, {
                    prompt: reviewPrompt,
                    model,
                    cwd,
                    timeout_ms: timeoutMs,
                    // Droid
                    auto: "high",
                    system_prompt_file: provider === "droid" ? REVIEWER_PROFILE : undefined,
                    // Opencode
                    agent: provider === "opencode" ? agent : undefined,
                });
                return {
                    model,
                    label: labelFor(model),
                    ok: result.ok,
                    text: result.ok
                        ? result.text || "(no output)"
                        : result.error_message ?? "failed",
                    duration_ms: result.duration_ms,
                    session_id: result.session_id,
                };
            }));
            const modelResults = results.map((r, i) => {
                if (r.status === "fulfilled")
                    return r.value;
                return {
                    model: models[i],
                    label: labelFor(models[i]),
                    ok: false,
                    text: r.reason instanceof Error
                        ? r.reason.message
                        : String(r.reason),
                    duration_ms: 0,
                };
            });
            const succeeded = modelResults.filter((r) => r.ok);
            const failed = modelResults.filter((r) => !r.ok);
            const sections = [];
            sections.push(`# Cross-Model Review [${provider}] (${succeeded.length}/${modelResults.length} models responded)\n`);
            for (const r of modelResults) {
                const status = r.ok ? `${r.duration_ms}ms` : "FAILED";
                sections.push(`## ${r.label} [${status}]\n`);
                sections.push(r.text);
                sections.push("");
            }
            if (failed.length > 0) {
                sections.push(`---\n**${failed.length} model(s) failed:** ${failed.map((r) => r.label).join(", ")}`);
            }
            const text = sections.join("\n");
            const structured = {
                provider,
                models_requested: models.length,
                models_succeeded: succeeded.length,
                models_failed: failed.length,
                results: modelResults.map((r) => ({
                    model: r.model,
                    label: r.label,
                    ok: r.ok,
                    duration_ms: r.duration_ms,
                    session_id: r.session_id,
                })),
            };
            return {
                content: [{ type: "text", text }],
                structuredContent: structured,
                isError: succeeded.length === 0 ? true : undefined,
            };
        }
        catch (err) {
            return createUnexpectedErrorResponse(err);
        }
    });
}
//# sourceMappingURL=cross-review.js.map