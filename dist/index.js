#!/usr/bin/env node
/**
 * mcp-do — local stdio MCP server that wraps droid CLI and opencode CLI
 * as a unified tool surface for Claude Code. The "3rd eye" — offloads
 * research, review, architecture analysis, and bug hunting to cheap
 * headless models with intelligent structured prompts.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadConfig } from "./config.js";
import { registerAllTools } from "./tools/index.js";
const VERSION = "0.4.1";
async function main() {
    // Load config (default provider, etc.) before registering tools.
    await loadConfig();
    const server = new McpServer({
        name: "mcp-do",
        version: VERSION,
    });
    registerAllTools(server);
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
main().catch((err) => {
    // stderr is safe — stdout is the MCP transport and must stay clean.
    console.error("mcp-do fatal:", err);
    process.exit(1);
});
//# sourceMappingURL=index.js.map