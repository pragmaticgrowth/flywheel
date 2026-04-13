/**
 * opencode_cross_review — parallel code review through 3 opencode models
 * spanning distinct training lineages. Mirrors droid_cross_review but routes
 * through `opencode run --agent review` instead of `droid exec`.
 *
 * Default models: GLM-5-Turbo (Zhipu), GPT-5.4-Mini (OpenAI), MiniMax-M2.7
 * (MiniMax / Alibaba lineage). Three distinct families for maximum blind-spot
 * coverage — picked from providers the user has already authed in opencode
 * (zai-coding-plan, openai, minimax-coding-plan).
 */
import { cleanOpencodeOutput, spawnOpencodeRun, } from "../opencode/exec.js";
import { OpencodeCrossReviewInputShape, } from "../schemas/opencode-cross-review.js";
import { resolveCwd } from "../utils/cwd.js";
import { createErrorResponse, createUnexpectedErrorResponse, } from "../utils/errors.js";
const DEFAULT_MODELS = [
    "zai-coding-plan/glm-5-turbo",
    "openai/gpt-5.4-mini",
    "minimax-coding-plan/MiniMax-M2.7",
];
const MODEL_LABELS = {
    "zai-coding-plan/glm-5-turbo": "GLM-5-Turbo (Zhipu)",
    "zai-coding-plan/glm-5.1": "GLM-5.1 (Zhipu Deep)",
    "zai-coding-plan/glm-4.7-flash": "GLM-4.7 Flash (Zhipu)",
    "openai/gpt-5.4-mini": "GPT-5.4-Mini (OpenAI)",
    "openai/gpt-5.4-fast": "GPT-5.4 Fast (OpenAI)",
    "openai/gpt-5.4": "GPT-5.4 (OpenAI)",
    "minimax-coding-plan/MiniMax-M2.7": "MiniMax M2.7 (MiniMax)",
    "minimax-coding-plan/MiniMax-M2.7-highspeed": "MiniMax M2.7 HS (MiniMax)",
};
function labelFor(model) {
    return MODEL_LABELS[model] ?? model;
}
/**
 * Wraps the user's prompt with cross-review framing so each model produces
 * structured, actionable output. Kept minimal so the agent's own system
 * prompt (~/.config/opencode/agents/review.md) drives the review format.
 */
function buildReviewPrompt(userPrompt) {
    return `Your findings will be merged with independent reviews from other models. Be specific: cite file:line for every finding. Focus on real bugs and edge cases, not style. Max 300 words.

${userPrompt}`;
}
const DEFAULT_TIMEOUT_MS = 240_000;
export function registerOpencodeCrossReviewTool(server) {
    server.registerTool("opencode_cross_review", {
        description: "Cross-model code review via opencode — runs the same review prompt through 3 different model families (default: GLM-5-Turbo, GPT-5.4-Mini, MiniMax-M2.7) in parallel using opencode's review agent and merges findings. Different model families have different blind spots, so this catches more issues than single-model review. Requires opencode installed (~/.opencode/bin/opencode) and a 'review' agent defined in ~/.config/opencode/agents/review.md.",
        inputSchema: OpencodeCrossReviewInputShape,
    }, async (input) => {
        try {
            const models = input.models ?? DEFAULT_MODELS;
            if (models.length === 0) {
                return createErrorResponse("models array must not be empty");
            }
            const cwd = resolveCwd(input.cwd);
            const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS;
            const agent = input.agent ?? "review";
            const reviewPrompt = buildReviewPrompt(input.prompt);
            const results = await Promise.allSettled(models.map(async (model) => {
                const result = await spawnOpencodeRun({
                    prompt: reviewPrompt,
                    model,
                    agent,
                    cwd,
                    timeout_ms: timeoutMs,
                });
                return {
                    model,
                    label: labelFor(model),
                    ok: result.ok,
                    text: result.ok
                        ? cleanOpencodeOutput(result.stdout) || "(no output)"
                        : result.error_message ?? "failed",
                    duration_ms: result.duration_ms,
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
            sections.push(`# OpenCode Cross-Model Review (${succeeded.length}/${modelResults.length} models responded)\n`);
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
                models_requested: models.length,
                models_succeeded: succeeded.length,
                models_failed: failed.length,
                agent,
                results: modelResults.map((r) => ({
                    model: r.model,
                    label: r.label,
                    ok: r.ok,
                    duration_ms: r.duration_ms,
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
//# sourceMappingURL=opencode-cross-review.js.map