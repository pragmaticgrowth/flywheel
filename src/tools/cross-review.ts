/**
 * droid_cross_review — runs the same review prompt through multiple model
 * families in parallel and returns a merged report with each model's findings
 * labeled by name.
 *
 * Default models: GLM-5-Turbo (Zhipu), GPT-5.4-Mini (OpenAI VP),
 * GLM-5.1 (Zhipu deepest).
 * Multiple training lineages = multiple blind spots covered.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawnDroidExec } from "../droid/exec.js";
import {
  CrossReviewInputShape,
  type CrossReviewInput,
} from "../schemas/cross-review.js";
import { resolveCwd } from "../utils/cwd.js";
import { access } from "node:fs/promises";
import {
  createErrorResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

const REVIEWER_PROFILE = join(
  homedir(),
  ".factory",
  "droids",
  "code-reviewer.md",
);

async function profileExists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

const DEFAULT_MODELS = [
  "custom:glm-5-turbo",
  "custom:VP-GPT-5.4-Mini-48",
  "custom:glm-5.1",
];

const MODEL_LABELS: Record<string, string> = {
  "custom:glm-5-turbo": "GLM-5-Turbo (Zhipu)",
  "custom:BYOK-GLM-5-Turbo-33": "GLM-5-Turbo (Zhipu)",
  "custom:VP-GPT-5.4-Mini-48": "GPT-5.4-Mini (OpenAI)",
  "custom:VP-GPT-5.4-15": "GPT-5.4 (OpenAI)",
  "custom:glm-5.1": "GLM-5.1 (Zhipu Deep)",
  "custom:BYOK-GLM-5.1-31": "GLM-5.1 (Zhipu Deep)",
  "custom:MiniMax-M2.7": "MiniMax M2.7",
  "custom:BYOK-MiniMax-M2.7-30": "MiniMax M2.7",
};

function labelFor(model: string): string {
  return MODEL_LABELS[model] ?? model;
}

/**
 * Wraps the user's prompt with cross-review framing so each model
 * produces structured, actionable output even if the caller's prompt is terse.
 * Kept minimal to avoid conflicting with the code-reviewer.md system prompt.
 */
function buildReviewPrompt(userPrompt: string): string {
  return `Your findings will be merged with independent reviews from other models. Be specific: cite file:line for every finding. Focus on real bugs and edge cases, not style. Max 300 words.

${userPrompt}`;
}

const DEFAULT_TIMEOUT_MS = 180_000;

interface ModelResult {
  model: string;
  label: string;
  ok: boolean;
  text: string;
  duration_ms: number;
  session_id?: string;
}

export function registerCrossReviewTool(server: McpServer): void {
  server.registerTool(
    "droid_cross_review",
    {
      description:
        "Cross-model code review — runs the same review prompt through 3 different models (GLM-5-Turbo, GPT-5.4-Mini, GLM-5.1) in parallel and merges findings. Different models have different blind spots, so this catches more issues than single-model review. Each model gets structured instructions to produce actionable, file:line-specific findings.",
      inputSchema: CrossReviewInputShape,
    },
    async (input: CrossReviewInput): Promise<McpToolResponse> => {
      try {
        const models = input.models ?? DEFAULT_MODELS;
        if (models.length === 0) {
          return createErrorResponse("models array must not be empty");
        }

        if (!(await profileExists(REVIEWER_PROFILE))) {
          return createErrorResponse(
            `code-reviewer profile not found at ${REVIEWER_PROFILE}`,
          );
        }

        const cwd = resolveCwd(input.cwd);
        const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS;
        const reviewPrompt = buildReviewPrompt(input.prompt);

        // Run all models in parallel
        const results = await Promise.allSettled(
          models.map(async (model): Promise<ModelResult> => {
            const result = await spawnDroidExec(
              {
                prompt: reviewPrompt,
                model,
                auto: "high",
                system_prompt_file: REVIEWER_PROFILE,
              },
              { cwd, timeout_ms: timeoutMs },
            );

            return {
              model,
              label: labelFor(model),
              ok: result.ok,
              text: result.ok
                ? result.parsed.text || "(no output)"
                : result.error_message || "failed",
              duration_ms: result.duration_ms,
              session_id: result.parsed.session_id,
            };
          }),
        );

        // Merge results
        const modelResults: ModelResult[] = results.map((r, i) => {
          if (r.status === "fulfilled") return r.value;
          return {
            model: models[i],
            label: labelFor(models[i]),
            ok: false,
            text: r.reason instanceof Error ? r.reason.message : String(r.reason),
            duration_ms: 0,
          };
        });

        const succeeded = modelResults.filter((r) => r.ok);
        const failed = modelResults.filter((r) => !r.ok);

        // Build merged report
        const sections: string[] = [];
        sections.push(
          `# Cross-Model Review (${succeeded.length}/${modelResults.length} models responded)\n`,
        );

        for (const r of modelResults) {
          const status = r.ok ? `${r.duration_ms}ms` : "FAILED";
          sections.push(`## ${r.label} [${status}]\n`);
          sections.push(r.text);
          sections.push(""); // blank line between sections
        }

        if (failed.length > 0) {
          sections.push(
            `---\n**${failed.length} model(s) failed:** ${failed.map((r) => r.label).join(", ")}`,
          );
        }

        const text = sections.join("\n");

        // structuredContent omits full text per model to avoid duplicating
        // what's already in content.text — callers use the text report.
        const structured: Record<string, unknown> = {
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
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
