/**
 * Unified preset tools — each wraps a structured prompt template + provider
 * dispatch. Works with both droid (via profile files) and opencode (via agents).
 *
 * Intelligent prompts (Codex-inspired: task + output_contract + grounding_rules)
 * are prepended to the user's prompt automatically. Tool descriptions stay brief.
 */
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { resolveProvider, resolveModel, DEFAULT_MODELS, DEEP_MODELS, } from "../config.js";
import { runWithProvider } from "../providers/index.js";
import { buildReviewPrompt, buildExplorePrompt, buildArchitectPrompt, } from "../prompts/index.js";
import { PresetInputShape } from "../schemas/preset.js";
import { resolveCwd } from "../utils/cwd.js";
import { createErrorResponse, createUnexpectedErrorResponse, } from "../utils/errors.js";
const DROIDS_DIR = join(homedir(), ".factory", "droids");
const PRESETS = [
    {
        name: "do_review",
        description: "Code review for bugs, security, and edge cases. Returns severity-rated findings with file:line citations. Skeptical by default — only reports material issues, not style.",
        promptBuilder: buildReviewPrompt,
        droid: {
            profile_file: join(DROIDS_DIR, "code-reviewer.md"),
            default_model: DEFAULT_MODELS.droid,
        },
        opencode: {
            agent: "review",
            default_model: DEFAULT_MODELS.opencode,
        },
    },
    {
        name: "do_explore",
        description: "Codebase navigation — answers 'where is X?' and 'how does Y work?' with file:line references and call chains. Read-only.",
        promptBuilder: buildExplorePrompt,
        droid: {
            profile_file: join(DROIDS_DIR, "code-explorer.md"),
            default_model: DEFAULT_MODELS.droid,
        },
        opencode: {
            agent: "droid-explore",
            default_model: DEFAULT_MODELS.opencode,
        },
    },
    {
        name: "do_architect",
        description: "Architecture analysis — evaluates structure, identifies risks, and recommends improvements with explicit trade-off assessments. Uses the deepest analysis model.",
        promptBuilder: buildArchitectPrompt,
        droid: {
            profile_file: join(DROIDS_DIR, "code-architect.md"),
            default_model: DEEP_MODELS.droid,
        },
        opencode: {
            default_model: DEEP_MODELS.opencode,
        },
    },
];
async function profileExists(path) {
    try {
        await access(path);
        return true;
    }
    catch {
        return false;
    }
}
function makePresetHandler(spec) {
    return async (input) => {
        try {
            const provider = resolveProvider(input.provider);
            // Resolve model for this provider
            const defaultModel = provider === "droid"
                ? spec.droid.default_model
                : spec.opencode.default_model;
            const model = resolveModel(input.model ?? defaultModel, provider);
            // Build the intelligent prompt (our template + user prompt)
            const prompt = spec.promptBuilder(input.prompt);
            // Droid: check profile exists
            if (provider === "droid" && !(await profileExists(spec.droid.profile_file))) {
                return createErrorResponse(`droid profile not found at ${spec.droid.profile_file}`);
            }
            const result = await runWithProvider(provider, {
                prompt,
                model,
                cwd: resolveCwd(input.cwd),
                timeout_ms: input.timeout_ms,
                // Droid-specific
                auto: input.auto ?? spec.droid.default_auto,
                reasoning_effort: input.reasoning_effort,
                session_id: input.session_id,
                tags: input.tags,
                system_prompt_file: provider === "droid" ? spec.droid.profile_file : undefined,
                // Opencode-specific
                agent: provider === "opencode" ? spec.opencode.agent : undefined,
            });
            const structured = {
                provider: result.provider,
                model: result.model,
                duration_ms: result.duration_ms,
            };
            if (result.session_id)
                structured.session_id = result.session_id;
            if (!result.ok) {
                return {
                    content: [
                        {
                            type: "text",
                            text: result.error_message || `${spec.name} failed via ${provider}`,
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
    };
}
export function registerPresetTools(server) {
    for (const spec of PRESETS) {
        server.registerTool(spec.name, {
            description: spec.description,
            inputSchema: PresetInputShape,
        }, makePresetHandler(spec));
    }
}
//# sourceMappingURL=presets.js.map