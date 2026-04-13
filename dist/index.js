/**
 * opencode plugin entry — exports { server: Plugin } conforming to
 * @opencode-ai/plugin's PluginModule interface. This wraps the same
 * core tools that the MCP server provides, but as native opencode tools.
 *
 * The MCP stdio server (for Claude Code) lives in mcp-server.ts.
 */
import { tool } from "@opencode-ai/plugin";
import { loadConfig, resolveProvider, resolveModel, DEFAULT_MODELS, DEEP_MODELS, FAST_MODELS, CROSS_REVIEW_MODELS, PR_REVIEW_MODELS, labelFor } from "./config.js";
import { runWithProvider } from "./providers/index.js";
import { listModels } from "./droid/models.js";
import { listProfiles } from "./droid/profiles.js";
import { listSessions } from "./droid/sessions.js";
import { spawnDroidExec } from "./droid/exec.js";
import { buildResearchPrompt, buildResearchFastPrompt, buildReviewPrompt, buildExplorePrompt, buildArchitectPrompt, buildSilentScanPrompt, buildTypeCheckPrompt, buildAdversarialReviewPrompt, buildCrossReviewPrompt, buildPrReviewPrompt, } from "./prompts/index.js";
import { homedir } from "node:os";
import { join } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
const execFileAsync = promisify(execFile);
const DROIDS_DIR = join(homedir(), ".factory", "droids");
const z = tool.schema;
// ── Common arg shapes ──────────────────────────────────────────────
const presetArgs = {
    prompt: z.string().describe("What to research, review, explore, etc."),
    provider: z.enum(["droid", "opencode"]).optional().describe("Execution backend (default: configured default)."),
    model: z.string().optional().describe("Override model. Accepts short aliases or provider-specific IDs."),
    cwd: z.string().optional().describe("Working directory override."),
    timeout_ms: z.number().optional().describe("Timeout in milliseconds."),
};
function makePreset(def) {
    return tool({
        description: def.description,
        args: presetArgs,
        async execute(args, ctx) {
            const provider = resolveProvider(args.provider);
            const model = resolveModel(args.model ?? def.defaultModel[provider], provider);
            const prompt = def.promptBuilder(args.prompt);
            const cwd = args.cwd ?? ctx.directory;
            const result = await runWithProvider(provider, {
                prompt,
                model,
                cwd,
                timeout_ms: args.timeout_ms,
                auto: def.autoLevel,
                system_prompt_file: provider === "droid" && def.droidProfile ? def.droidProfile : undefined,
                agent: provider === "opencode" ? def.opencodeAgent : undefined,
            });
            if (!result.ok)
                throw new Error(result.error_message || "tool failed");
            return result.text;
        },
    });
}
// ── Git helper (for PR review) ─────────────────────────────────────
async function git(args, cwd) {
    try {
        const { stdout } = await execFileAsync("git", args, { cwd, maxBuffer: 10 * 1024 * 1024 });
        return { stdout: stdout.trim(), ok: true };
    }
    catch {
        return { stdout: "", ok: false };
    }
}
// ── Plugin server function ─────────────────────────────────────────
const server = async (input) => {
    await loadConfig();
    return {
        tool: {
            // ── Presets ──────────────────────────────────────────────
            do_research: makePreset({
                description: "Deep web research — parallel search across web, Reddit, HN, docs. Returns structured findings with source citations.",
                promptBuilder: buildResearchPrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "deep-researcher.md"),
                opencodeAgent: "research",
                autoLevel: "high",
            }),
            do_research_fast: makePreset({
                description: "Quick research lookup — concise answer under 200 words. Uses fastest model.",
                promptBuilder: buildResearchFastPrompt,
                defaultModel: FAST_MODELS,
                droidProfile: join(DROIDS_DIR, "deep-researcher.md"),
                opencodeAgent: "research",
                autoLevel: "high",
            }),
            do_review: makePreset({
                description: "Code review for bugs, security, and edge cases. Returns severity-rated findings with file:line citations.",
                promptBuilder: buildReviewPrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "code-reviewer.md"),
                opencodeAgent: "review",
            }),
            do_explore: makePreset({
                description: "Codebase navigation — answers 'where is X?' and 'how does Y work?' with file:line references.",
                promptBuilder: buildExplorePrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "code-explorer.md"),
                opencodeAgent: "droid-explore",
            }),
            do_architect: makePreset({
                description: "Architecture analysis — evaluates structure, identifies risks, recommends improvements with trade-offs.",
                promptBuilder: buildArchitectPrompt,
                defaultModel: DEEP_MODELS,
                droidProfile: join(DROIDS_DIR, "code-architect.md"),
            }),
            do_silent_scan: makePreset({
                description: "Silent failure scanner — finds swallowed errors, empty catches, ignored promises, missing error handling.",
                promptBuilder: buildSilentScanPrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "silent-failure-hunter.md"),
            }),
            do_type_check: makePreset({
                description: "TypeScript type design review — flags leaks, unsafe casts, missing nullability, incorrect generics.",
                promptBuilder: buildTypeCheckPrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "type-design-analyzer.md"),
            }),
            do_adversarial_review: makePreset({
                description: "Adversarial review that challenges design choices, assumptions, and tradeoffs.",
                promptBuilder: buildAdversarialReviewPrompt,
                defaultModel: DEFAULT_MODELS,
                droidProfile: join(DROIDS_DIR, "code-reviewer.md"),
                opencodeAgent: "review",
                autoLevel: "high",
            }),
            // ── Cross review ────────────────────────────────────────
            do_cross_review: tool({
                description: "Cross-model code review — runs review through 3 different model families in parallel. Different lineages catch different blind spots.",
                args: {
                    prompt: z.string().describe("What to review (file, diff, or description)."),
                    provider: z.enum(["droid", "opencode"]).optional(),
                    cwd: z.string().optional(),
                    timeout_ms: z.number().optional(),
                },
                async execute(args, ctx) {
                    const provider = resolveProvider(args.provider);
                    const models = CROSS_REVIEW_MODELS[provider];
                    const cwd = args.cwd ?? ctx.directory;
                    const reviewPrompt = buildCrossReviewPrompt(args.prompt);
                    const results = await Promise.allSettled(models.map(async (model) => {
                        const result = await runWithProvider(provider, {
                            prompt: reviewPrompt,
                            model,
                            cwd,
                            timeout_ms: args.timeout_ms ?? 240_000,
                            auto: "high",
                            system_prompt_file: provider === "droid" ? join(DROIDS_DIR, "code-reviewer.md") : undefined,
                            agent: provider === "opencode" ? "review" : undefined,
                        });
                        return { model, label: labelFor(model), ok: result.ok, text: result.ok ? result.text : (result.error_message ?? "failed"), duration_ms: result.duration_ms };
                    }));
                    const sections = [`# Cross-Model Review [${provider}]\n`];
                    for (const r of results) {
                        if (r.status === "fulfilled") {
                            sections.push(`## ${r.value.label} [${r.value.ok ? `${r.value.duration_ms}ms` : "FAILED"}]\n${r.value.text}\n`);
                        }
                        else {
                            sections.push(`## (failed)\n${r.reason}\n`);
                        }
                    }
                    return sections.join("\n");
                },
            }),
            // ── PR review ────────────────────────────────────────────
            do_pr_review: tool({
                description: "Comprehensive PR review — auto-gathers git diff, commits, changed files, then sends to deep analysis model.",
                args: {
                    prompt: z.string().optional().describe("Additional context or focus areas."),
                    provider: z.enum(["droid", "opencode"]).optional(),
                    base: z.string().optional().describe("Base branch (auto-detects main/master/develop)."),
                    scope: z.enum(["full", "staged", "unstaged"]).optional(),
                    model: z.string().optional(),
                    cwd: z.string().optional(),
                    timeout_ms: z.number().optional(),
                },
                async execute(args, ctx) {
                    const cwd = args.cwd ?? ctx.directory;
                    const provider = resolveProvider(args.provider);
                    const scope = args.scope ?? "full";
                    const { ok: isGitRepo } = await git(["rev-parse", "--is-inside-work-tree"], cwd);
                    if (!isGitRepo)
                        throw new Error(`not a git repository: ${cwd}`);
                    let base = args.base;
                    if (!base) {
                        for (const candidate of ["main", "master", "develop"]) {
                            const { ok } = await git(["rev-parse", "--verify", candidate], cwd);
                            if (ok) {
                                base = candidate;
                                break;
                            }
                        }
                        if (!base)
                            throw new Error("could not detect base branch");
                    }
                    const [branchR, diffR, statR, logR] = await Promise.all([
                        git(["rev-parse", "--abbrev-ref", "HEAD"], cwd),
                        scope === "staged" ? git(["diff", "--cached"], cwd) :
                            scope === "unstaged" ? git(["diff"], cwd) :
                                git(["diff", `${base}...HEAD`], cwd),
                        scope === "staged" ? git(["diff", "--cached", "--stat"], cwd) :
                            scope === "unstaged" ? git(["diff", "--stat"], cwd) :
                                git(["diff", `${base}...HEAD`, "--stat"], cwd),
                        scope === "full" ? git(["log", `${base}..HEAD`, "--oneline", "--no-decorate"], cwd) : Promise.resolve({ stdout: "", ok: true }),
                    ]);
                    if (!diffR.stdout)
                        return `No changes to review (${branchR.stdout || "HEAD"} is up to date with ${base}).`;
                    let diff = diffR.stdout;
                    const MAX = 80_000;
                    const truncated = Buffer.byteLength(diff) > MAX;
                    if (truncated)
                        diff = Buffer.from(diff).subarray(0, MAX).toString("utf8");
                    const prCtx = {
                        branch: branchR.stdout || "HEAD",
                        base,
                        commitLog: logR.stdout,
                        diffStat: statR.stdout,
                        diff,
                        diffTruncated: truncated,
                        focus: args.prompt,
                    };
                    const prompt = buildPrReviewPrompt(prCtx);
                    const model = resolveModel(args.model ?? PR_REVIEW_MODELS[provider], provider);
                    const result = await runWithProvider(provider, {
                        prompt,
                        model,
                        cwd,
                        timeout_ms: args.timeout_ms ?? 300_000,
                        auto: "high",
                        agent: provider === "opencode" ? "pr-reviewer" : undefined,
                    });
                    if (!result.ok)
                        throw new Error(result.error_message || "PR review failed");
                    const commits = logR.stdout ? logR.stdout.split("\n").filter(Boolean).length : 0;
                    const header = `# PR Review [${provider}] — ${branchR.stdout} → ${base}\n**Model:** ${labelFor(model)} | **${commits} commits** | ${truncated ? "diff truncated" : `${Buffer.byteLength(diffR.stdout)} bytes`}\n\n`;
                    return header + result.text;
                },
            }),
            // ── Generic exec ─────────────────────────────────────────
            do_exec: tool({
                description: "Generic execution passthrough. Prefer specialized tools for common workflows.",
                args: {
                    prompt: z.string().describe("Prompt to send."),
                    provider: z.enum(["droid", "opencode"]).optional(),
                    model: z.string().optional(),
                    cwd: z.string().optional(),
                    timeout_ms: z.number().optional(),
                },
                async execute(args, ctx) {
                    const provider = resolveProvider(args.provider);
                    const model = resolveModel(args.model ?? DEFAULT_MODELS[provider], provider);
                    const cwd = args.cwd ?? ctx.directory;
                    const result = await runWithProvider(provider, {
                        prompt: args.prompt,
                        model,
                        cwd,
                        timeout_ms: args.timeout_ms,
                    });
                    if (!result.ok)
                        throw new Error(result.error_message || "exec failed");
                    return result.text;
                },
            }),
            // ── Meta tools ───────────────────────────────────────────
            do_list_models: tool({
                description: "List custom (BYOK) models from ~/.factory/settings.json.",
                args: {},
                async execute() {
                    const models = await listModels();
                    return JSON.stringify({ count: models.length, models }, null, 2);
                },
            }),
            do_list_profiles: tool({
                description: "List droid agent profiles (global + project-local).",
                args: {
                    cwd: z.string().optional(),
                },
                async execute(args, ctx) {
                    const profiles = await listProfiles({ cwd: args.cwd ?? ctx.directory });
                    return JSON.stringify({ count: profiles.length, profiles }, null, 2);
                },
            }),
            // ── Session tools (droid only) ───────────────────────────
            do_session_list: tool({
                description: "List droid sessions, filtered by cwd.",
                args: {
                    cwd: z.string().optional(),
                    all: z.boolean().optional().describe("Ignore cwd filter."),
                    search: z.string().optional(),
                    limit: z.number().optional(),
                },
                async execute(args, ctx) {
                    const sessions = await listSessions({
                        cwd: args.cwd ?? ctx.directory,
                        all: args.all,
                        search: args.search,
                        limit: args.limit,
                    });
                    return JSON.stringify({ count: sessions.length, sessions }, null, 2);
                },
            }),
            do_session_continue: tool({
                description: "Continue an existing droid session by ID.",
                args: {
                    session_id: z.string(),
                    prompt: z.string(),
                    model: z.string().optional(),
                    cwd: z.string().optional(),
                    timeout_ms: z.number().optional(),
                },
                async execute(args, ctx) {
                    const result = await spawnDroidExec({
                        session_id: args.session_id,
                        prompt: args.prompt,
                        model: args.model ?? DEFAULT_MODELS.droid,
                    }, { cwd: args.cwd ?? ctx.directory, timeout_ms: args.timeout_ms });
                    if (!result.ok)
                        throw new Error(result.stderr || "session continue failed");
                    return result.stdout;
                },
            }),
        },
    };
};
const plugin = { server };
export default plugin;
//# sourceMappingURL=index.js.map