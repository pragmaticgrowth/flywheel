/**
 * do_pr_review — comprehensive single-pass PR review with auto git context.
 * Gathers git diff, commits, and changed files, then dispatches to GPT-5.4 xHigh.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  type ProviderName,
  resolveProvider,
  resolveModel,
  PR_REVIEW_MODELS,
  labelFor,
} from "../config.js";
import { runWithProvider } from "../providers/index.js";
import { buildPrReviewPrompt } from "../prompts/index.js";
import type { PrReviewContext } from "../prompts/pr-review.js";
import {
  PrReviewInputShape,
  type PrReviewInput,
} from "../schemas/pr-review.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

const execFileAsync = promisify(execFile);

const DEFAULT_TIMEOUT_MS = 300_000;
const MAX_DIFF_BYTES = 80_000;
const BASE_CANDIDATES = ["main", "master", "develop"];

async function git(
  args: string[],
  cwd: string,
): Promise<{ stdout: string; ok: boolean }> {
  try {
    const { stdout } = await execFileAsync("git", args, {
      cwd,
      maxBuffer: 10 * 1024 * 1024,
    });
    return { stdout: stdout.trim(), ok: true };
  } catch {
    return { stdout: "", ok: false };
  }
}

async function detectBase(cwd: string): Promise<string | null> {
  for (const candidate of BASE_CANDIDATES) {
    const { ok } = await git(["rev-parse", "--verify", candidate], cwd);
    if (ok) return candidate;
  }
  return null;
}

interface GitContext {
  branch: string;
  base: string;
  commitLog: string;
  diffStat: string;
  diff: string;
  diffTruncated: boolean;
  commitCount: number;
  filesChanged: number;
  diffBytes: number;
}

async function gatherGitContext(
  cwd: string,
  base: string,
  scope: "full" | "staged" | "unstaged",
): Promise<GitContext> {
  const { stdout: branch } = await git(
    ["rev-parse", "--abbrev-ref", "HEAD"],
    cwd,
  );

  let diffArgs: string[];
  let logArgs: string[] | null;
  let statArgs: string[];

  if (scope === "staged") {
    diffArgs = ["diff", "--cached"];
    statArgs = ["diff", "--cached", "--stat"];
    logArgs = null;
  } else if (scope === "unstaged") {
    diffArgs = ["diff"];
    statArgs = ["diff", "--stat"];
    logArgs = null;
  } else {
    diffArgs = ["diff", `${base}...HEAD`];
    statArgs = ["diff", `${base}...HEAD`, "--stat"];
    logArgs = ["log", `${base}..HEAD`, "--oneline", "--no-decorate"];
  }

  const [diffResult, statResult, logResult] = await Promise.all([
    git(diffArgs, cwd),
    git(statArgs, cwd),
    logArgs ? git(logArgs, cwd) : Promise.resolve({ stdout: "", ok: true }),
  ]);

  let diff = diffResult.stdout;
  let diffTruncated = false;
  const diffBytes = Buffer.byteLength(diff, "utf8");

  if (diffBytes > MAX_DIFF_BYTES) {
    diff = diff.slice(0, MAX_DIFF_BYTES);
    diffTruncated = true;
  }

  const commitCount = logResult.stdout
    ? logResult.stdout.split("\n").filter(Boolean).length
    : 0;
  const statMatch = statResult.stdout.match(/(\d+) files? changed/);
  const filesChanged = statMatch ? parseInt(statMatch[1], 10) : 0;

  return {
    branch: branch || "HEAD",
    base,
    commitLog: logResult.stdout,
    diffStat: statResult.stdout,
    diff,
    diffTruncated,
    commitCount,
    filesChanged,
    diffBytes,
  };
}

export function registerPrReviewTool(server: McpServer): void {
  server.registerTool(
    "do_pr_review",
    {
      description:
        "Comprehensive PR review — auto-gathers git diff, commits, and changed files, then sends to GPT-5.4 xHigh for deep single-pass analysis. Covers bugs, security, edge cases, type safety, test gaps, and breaking changes. Returns structured findings with verdict (APPROVE / REQUEST_CHANGES / COMMENT).",
      inputSchema: PrReviewInputShape,
    },
    async (input: PrReviewInput): Promise<McpToolResponse> => {
      try {
        const cwd = resolveCwd(input.cwd);
        const provider: ProviderName = resolveProvider(input.provider);
        const scope = input.scope ?? "full";

        const { ok: isGitRepo } = await git(
          ["rev-parse", "--is-inside-work-tree"],
          cwd,
        );
        if (!isGitRepo) {
          return createErrorResponse(`not a git repository: ${cwd}`);
        }

        let base: string | undefined = input.base;
        if (!base) {
          const detected = await detectBase(cwd);
          if (!detected) {
            return createErrorResponse(
              "could not detect base branch (tried main, master, develop). Specify the base param.",
            );
          }
          base = detected;
        }

        const ctx = await gatherGitContext(cwd, base, scope);

        if (!ctx.diff) {
          return {
            content: [
              {
                type: "text",
                text: `No changes to review (${ctx.branch} is up to date with ${base}).`,
              },
            ],
          };
        }

        const prCtx: PrReviewContext = {
          branch: ctx.branch,
          base: ctx.base,
          commitLog: ctx.commitLog,
          diffStat: ctx.diffStat,
          diff: ctx.diff,
          diffTruncated: ctx.diffTruncated,
          focus: input.focus,
        };
        const prompt = buildPrReviewPrompt(prCtx);

        const defaultModel = PR_REVIEW_MODELS[provider];
        const model = resolveModel(input.model ?? defaultModel, provider);
        const timeoutMs = input.timeout_ms ?? DEFAULT_TIMEOUT_MS;

        const result = await runWithProvider(provider, {
          prompt,
          model,
          cwd,
          timeout_ms: timeoutMs,
          auto: "high",
          system_prompt_file: undefined,
        });

        const structured: Record<string, unknown> = {
          provider: result.provider,
          model: result.model,
          branch: ctx.branch,
          base: ctx.base,
          commits: ctx.commitCount,
          files_changed: ctx.filesChanged,
          diff_bytes: ctx.diffBytes,
          diff_truncated: ctx.diffTruncated,
          duration_ms: result.duration_ms,
        };
        if (result.session_id) structured.session_id = result.session_id;

        if (!result.ok) {
          return {
            content: [
              {
                type: "text",
                text: result.error_message || "PR review failed",
              },
            ],
            structuredContent: structured,
            isError: true,
          };
        }

        const header = `# PR Review [${provider}] — ${ctx.branch} → ${base}\n**Model:** ${labelFor(model)} | **${ctx.commitCount} commits** | **${ctx.filesChanged} files** | ${ctx.diffTruncated ? "diff truncated" : `${ctx.diffBytes} bytes`}\n\n`;

        return {
          content: [{ type: "text", text: header + result.text }],
          structuredContent: structured,
        };
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
