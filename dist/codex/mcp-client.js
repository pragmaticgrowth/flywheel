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
/**
 * MCP client default is 60s — far too short for Codex at medium/high/xhigh
 * reasoning with a real diff. 10 minutes matches codex exec's own default.
 */
const DEFAULT_REQUEST_TIMEOUT_MS = 600_000;
export class CodexMcpClient {
    client = null;
    transport = null;
    connectPromise = null;
    async ensureConnected() {
        if (this.client)
            return;
        if (this.connectPromise)
            return this.connectPromise;
        this.connectPromise = (async () => {
            const transport = new StdioClientTransport({
                command: "codex",
                args: ["mcp-server"],
                env: process.env,
                cwd: process.cwd(),
            });
            const client = new Client({ name: "mcp-do", version: "0.3.0" }, { capabilities: {} });
            await client.connect(transport);
            this.transport = transport;
            this.client = client;
        })();
        try {
            await this.connectPromise;
        }
        finally {
            this.connectPromise = null;
        }
    }
    async call(opts) {
        await this.ensureConnected();
        if (!this.client)
            throw new Error("codex mcp client not connected");
        const startedAt = Date.now();
        const requestOptions = {
            timeout: opts.timeout_ms ?? DEFAULT_REQUEST_TIMEOUT_MS,
        };
        let response;
        if (opts.thread_id) {
            response = await this.client.callTool({
                name: "codex-reply",
                arguments: {
                    threadId: opts.thread_id,
                    prompt: opts.prompt,
                },
            }, undefined, requestOptions);
        }
        else {
            const config = { ...(opts.config ?? {}) };
            if (opts.reasoning_effort) {
                config.model_reasoning_effort = opts.reasoning_effort;
            }
            const args = { prompt: opts.prompt };
            if (opts.model)
                args.model = opts.model;
            if (opts.sandbox)
                args.sandbox = opts.sandbox;
            if (opts.approval_policy)
                args["approval-policy"] = opts.approval_policy;
            if (opts.profile)
                args.profile = opts.profile;
            if (opts.base_instructions)
                args["base-instructions"] = opts.base_instructions;
            if (opts.include_plan_tool !== undefined) {
                args["include-plan-tool"] = opts.include_plan_tool;
            }
            if (opts.cwd)
                args.cwd = opts.cwd;
            if (Object.keys(config).length > 0)
                args.config = config;
            response = await this.client.callTool({
                name: "codex",
                arguments: args,
            }, undefined, requestOptions);
        }
        const structured = response.structuredContent ??
            undefined;
        const threadIdFromResp = typeof structured?.threadId === "string"
            ? structured.threadId
            : undefined;
        const thread_id = threadIdFromResp ?? opts.thread_id ?? "";
        let text = typeof structured?.content === "string"
            ? structured.content
            : "";
        if (!text && Array.isArray(response.content)) {
            const firstText = response.content.find((c) => typeof c === "object" &&
                c !== null &&
                c.type === "text" &&
                typeof c.text === "string");
            if (firstText)
                text = firstText.text;
        }
        return {
            thread_id,
            text,
            raw: structured,
            is_error: response.isError === true,
            duration_ms: Date.now() - startedAt,
        };
    }
    async close() {
        if (!this.client)
            return;
        try {
            await this.client.close();
        }
        catch {
            // best effort; transport may already be gone
        }
        this.client = null;
        this.transport = null;
    }
}
// ---------------------------------------------------------------------------
// Singleton — one codex mcp-server subprocess per mcp-do process.
// ---------------------------------------------------------------------------
let singleton = null;
let shutdownRegistered = false;
export function getCodexMcpClient() {
    if (!singleton) {
        singleton = new CodexMcpClient();
        if (!shutdownRegistered) {
            const cleanup = async () => {
                const s = singleton;
                singleton = null;
                if (s)
                    await s.close();
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
export function __resetCodexMcpClientForTests() {
    singleton = null;
}
//# sourceMappingURL=mcp-client.js.map