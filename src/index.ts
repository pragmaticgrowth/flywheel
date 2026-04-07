#!/usr/bin/env node
/**
 * mcp-droid — local stdio MCP server that wraps the Factory AI `droid` CLI.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerAllTools } from "./tools/index.js";

const VERSION = "0.1.0";

async function main(): Promise<void> {
  const server = new McpServer({
    name: "mcp-droid",
    version: VERSION,
  });

  registerAllTools(server);

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  // stderr is safe — stdout is the MCP transport and must stay clean.
  console.error("mcp-droid fatal:", err);
  process.exit(1);
});
