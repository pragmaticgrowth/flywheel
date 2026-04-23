/**
 * CodexMcpClient — a persistent MCP client connected to `codex mcp-server`.
 *
 * Why: `codex exec` cold-starts per call (20+s latency). `codex mcp-server`
 * is a long-running stdio MCP server that exposes two tools — `codex` and
 * `codex-reply` — and keeps the session alive across many turns, making
 * each follow-up turn 10-15x faster.
 *
 * Design:
 *   - Lazy-spawned singleton. First call spawns the subprocess; subsequent
 *     calls reuse it.
 *   - stdio transport (no network, no ports).
 *   - Inherits parent env so `~/.codex/config.toml` auth just works.
 *   - Call `close()` on server shutdown to kill the child.
 *
 * The Codex MCP server's `codex` tool accepts:
 *   prompt, model, sandbox, approval-policy, profile, cwd, include-plan-tool,
 *   base-instructions, config. The `config` object holds any TOML override
 *   (model_reasoning_effort, etc.).
 *
 * Response shape:
 *   { structuredContent: { threadId, content }, content: [{ type, text }] }
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

export type CodexSandbox =
  | "read-only"
  | "workspace-write"
  | "danger-full-access";
export type CodexApprovalPolicy = "untrusted" | "on-request" | "never";
export type CodexReasoning = "minimal" | "low" | "medium" | "high" | "xhigh";

export interface CodexCallOptions {
  prompt: string;
  /** Continue an existing thread. Routes to `codex-reply` instead of `codex`. */
  thread_id?: string;
  model?: string;
  reasoning_effort?: CodexReasoning;
  sandbox?: CodexSandbox;
  approval_policy?: CodexApprovalPolicy;
  profile?: string;
  base_instructions?: string;
  include_plan_tool?: boolean;
  cwd?: string;
  /** Extra TOML overrides for ~/.codex/config.toml. Values are TOML-parsed. */
  config?: Record<string, unknown>;
  /** Per-call MCP request timeout in ms. Default 10 min. */
  timeout_ms?: number;
}

/**
 * MCP client default is 60s — far too short for Codex at medium/high/xhigh
 * reasoning with a real diff. 10 minutes matches codex exec's own default.
 */
const DEFAULT_REQUEST_TIMEOUT_MS = 600_000;

export interface CodexCallResult {
  thread_id: string;
  text: string;
  /** Full structuredContent from the MCP response (for debugging). */
  raw: Record<string, unknown> | undefined;
  is_error: boolean;
  duration_ms: number;
}

export class CodexMcpClient {
  private client: Client | null = null;
  private transport: StdioClientTransport | null = null;
  private connectPromise: Promise<void> | null = null;

  private async ensureConnected(): Promise<void> {
    if (this.client) return;
    if (this.connectPromise) return this.connectPromise;

    this.connectPromise = (async () => {
      const transport = new StdioClientTransport({
        command: "codex",
        args: ["mcp-server"],
        env: process.env as Record<string, string>,
        cwd: process.cwd(),
      });
      const client = new Client(
        { name: "mcp-do", version: "0.3.0" },
        { capabilities: {} },
      );
      await client.connect(transport);
      this.transport = transport;
      this.client = client;
    })();

    try {
      await this.connectPromise;
    } finally {
      this.connectPromise = null;
    }
  }

  async call(opts: CodexCallOptions): Promise<CodexCallResult> {
    await this.ensureConnected();
    if (!this.client) throw new Error("codex mcp client not connected");

    const startedAt = Date.now();

    const requestOptions = {
      timeout: opts.timeout_ms ?? DEFAULT_REQUEST_TIMEOUT_MS,
    };

    let response: Awaited<ReturnType<Client["callTool"]>>;
    if (opts.thread_id) {
      response = await this.client.callTool(
        {
          name: "codex-reply",
          arguments: {
            threadId: opts.thread_id,
            prompt: opts.prompt,
          },
        },
        undefined,
        requestOptions,
      );
    } else {
      const config: Record<string, unknown> = { ...(opts.config ?? {}) };
      if (opts.reasoning_effort) {
        config.model_reasoning_effort = opts.reasoning_effort;
      }

      const args: Record<string, unknown> = { prompt: opts.prompt };
      if (opts.model) args.model = opts.model;
      if (opts.sandbox) args.sandbox = opts.sandbox;
      if (opts.approval_policy) args["approval-policy"] = opts.approval_policy;
      if (opts.profile) args.profile = opts.profile;
      if (opts.base_instructions) args["base-instructions"] = opts.base_instructions;
      if (opts.include_plan_tool !== undefined) {
        args["include-plan-tool"] = opts.include_plan_tool;
      }
      if (opts.cwd) args.cwd = opts.cwd;
      if (Object.keys(config).length > 0) args.config = config;

      response = await this.client.callTool(
        {
          name: "codex",
          arguments: args,
        },
        undefined,
        requestOptions,
      );
    }

    const structured =
      (response.structuredContent as Record<string, unknown> | undefined) ??
      undefined;

    const threadIdFromResp =
      typeof structured?.threadId === "string"
        ? (structured.threadId as string)
        : undefined;
    const thread_id = threadIdFromResp ?? opts.thread_id ?? "";

    let text =
      typeof structured?.content === "string"
        ? (structured.content as string)
        : "";
    if (!text && Array.isArray(response.content)) {
      const firstText = response.content.find(
        (c): c is { type: "text"; text: string } =>
          typeof c === "object" &&
          c !== null &&
          (c as { type?: string }).type === "text" &&
          typeof (c as { text?: string }).text === "string",
      );
      if (firstText) text = firstText.text;
    }

    return {
      thread_id,
      text,
      raw: structured,
      is_error: response.isError === true,
      duration_ms: Date.now() - startedAt,
    };
  }

  async close(): Promise<void> {
    if (!this.client) return;
    try {
      await this.client.close();
    } catch {
      // best effort; transport may already be gone
    }
    this.client = null;
    this.transport = null;
  }
}

// ---------------------------------------------------------------------------
// Singleton — one codex mcp-server subprocess per mcp-do process.
// ---------------------------------------------------------------------------

let singleton: CodexMcpClient | null = null;
let shutdownRegistered = false;

export function getCodexMcpClient(): CodexMcpClient {
  if (!singleton) {
    singleton = new CodexMcpClient();
    if (!shutdownRegistered) {
      const cleanup = async (): Promise<void> => {
        const s = singleton;
        singleton = null;
        if (s) await s.close();
      };
      process.on("exit", () => {
        // synchronous exit — no async work possible
      });
      process.on("SIGINT", () => {
        void cleanup().finally(() => process.exit(0));
      });
      process.on("SIGTERM", () => {
        void cleanup().finally(() => process.exit(0));
      });
      shutdownRegistered = true;
    }
  }
  return singleton;
}

/** Test-only: reset the singleton. */
export function __resetCodexMcpClientForTests(): void {
  singleton = null;
}
