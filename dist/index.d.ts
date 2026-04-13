/**
 * opencode plugin entry — exports { server: Plugin } conforming to
 * @opencode-ai/plugin's PluginModule interface. This wraps the same
 * core tools that the MCP server provides, but as native opencode tools.
 *
 * The MCP stdio server (for Claude Code) lives in mcp-server.ts.
 */
import type { PluginModule } from "@opencode-ai/plugin";
declare const plugin: PluginModule;
export default plugin;
