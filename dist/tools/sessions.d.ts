/**
 * Session tools: do_session_continue + do_session_list.
 * Sessions remain droid-only — opencode session management requires
 * a running `opencode serve` instance.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerSessionTools(server: McpServer): void;
