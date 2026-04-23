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
export type CodexSandbox = "read-only" | "workspace-write" | "danger-full-access";
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
export interface CodexCallResult {
    thread_id: string;
    text: string;
    /** Full structuredContent from the MCP response (for debugging). */
    raw: Record<string, unknown> | undefined;
    is_error: boolean;
    duration_ms: number;
}
export declare class CodexMcpClient {
    private client;
    private transport;
    private connectPromise;
    private ensureConnected;
    call(opts: CodexCallOptions): Promise<CodexCallResult>;
    close(): Promise<void>;
}
export declare function getCodexMcpClient(): CodexMcpClient;
/** Test-only: reset the singleton. */
export declare function __resetCodexMcpClientForTests(): void;
