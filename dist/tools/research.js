/**
 * do_research — unified web research tool.
 *
 * One tool, two depths:
 *   depth: "deep" (default) — thorough, parallel web search, GLM-5-Turbo,
 *     structured Key Findings / Sources / Confidence / Open Questions report.
 *   depth: "fast" — quick lookup, <200 words, MiniMax-M2.7.
 *
 * Previously shipped as two tools (do_research + do_research_fast). Merged
 * in April 2026 because the only difference was model + prompt template.
 */
import { z } from "zod";
import { homedir } from "node:os";
import { join } from "node:path";
import { resolveProvider, resolveModel, DEFAULT_MODELS, FAST_MODELS, } from "../config.js";
import { runWithProvider } from "../providers/index.js";
import { PresetInputShape } from "../schemas/preset.js";
import { resolveCwd } from "../utils/cwd.js";
import { createUnexpectedErrorResponse, } from "../utils/errors.js";
const DROIDS_DIR = join(homedir(), ".factory", "droids");
const RESEARCHER_PROFILE = join(DROIDS_DIR, "deep-researcher.md");
const DEEP_TEMPLATE = `<task>
Deep research on the topic below. Search the web, documentation, forums, and code repositories.
Synthesize findings into a structured report with source citations.
</task>

<output_contract>
Structure your response as:
1. **Key Findings** — bullet points, most important first
2. **Sources** — URL + one-line summary per source
3. **Confidence** — what you're certain about vs uncertain
4. **Open Questions** — what remains unknown or needs further investigation
</output_contract>

<grounding_rules>
- Clearly separate observed facts from inferences
- Cite sources for every factual claim
- State "I could not verify" rather than guessing
- Do not fabricate URLs or documentation references
- Separate "what the docs say" from "what the community reports"
</grounding_rules>`;
const FAST_TEMPLATE = `<task>
Quick research on the topic below. Provide a concise, actionable answer.
Prioritize speed over exhaustiveness.
</task>

<output_contract>
Keep response under 200 words. Structure as:
1. **Answer** — direct response
2. **Source** — primary reference (URL if available)
3. **Caveat** — anything the caller should verify
</output_contract>

<grounding_rules>
- Only state facts you can verify
- Prefer official docs over community posts
- Say "unsure" rather than guessing
</grounding_rules>`;
export function registerResearchTool(server) {
    server.registerTool("do_research", {
        description: "Web research via headless AI. Two depths: `depth: 'deep'` (default) runs thorough parallel search and returns a structured report with sources/confidence/open-questions. `depth: 'fast'` returns a concise <200-word answer with one primary source — use it for quick lookups (version numbers, API signatures, defaults). Headless model keeps results out of main context.",
        inputSchema: {
            ...PresetInputShape,
            depth: z
                .enum(["deep", "fast"])
                .optional()
                .describe("Research depth. `deep` (default) — thorough structured report. `fast` — concise <200-word answer for quick lookups."),
        },
    }, async (input) => {
        try {
            const depth = input.depth ?? "deep";
            const provider = resolveProvider(input.provider);
            const defaultModel = depth === "fast"
                ? provider === "droid"
                    ? FAST_MODELS.droid
                    : FAST_MODELS.opencode
                : provider === "droid"
                    ? DEFAULT_MODELS.droid
                    : DEFAULT_MODELS.opencode;
            const model = resolveModel(input.model ?? defaultModel, provider);
            const template = depth === "fast" ? FAST_TEMPLATE : DEEP_TEMPLATE;
            const prompt = `${template}\n\n${input.prompt}`;
            const result = await runWithProvider(provider, {
                prompt,
                model,
                cwd: resolveCwd(input.cwd),
                timeout_ms: input.timeout_ms,
                auto: input.auto ?? "high",
                reasoning_effort: input.reasoning_effort,
                session_id: input.session_id,
                tags: input.tags,
                system_prompt_file: provider === "droid" ? RESEARCHER_PROFILE : undefined,
                agent: provider === "opencode" ? "research" : undefined,
            });
            const structured = {
                provider: result.provider,
                model: result.model,
                depth,
                duration_ms: result.duration_ms,
            };
            if (result.session_id)
                structured.session_id = result.session_id;
            if (!result.ok) {
                return {
                    content: [
                        {
                            type: "text",
                            text: result.error_message || `do_research (${depth}) failed via ${provider}`,
                        },
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
        catch (err) {
            return createUnexpectedErrorResponse(err);
        }
    });
}
//# sourceMappingURL=research.js.map