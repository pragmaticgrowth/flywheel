/**
 * Mission tools: start, list, status, progress. droid_mission_cancel is
 * intentionally NOT implemented in v1 — cancellation semantics need
 * investigation (spec §6.3).
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerMissionTools(server: McpServer): void;
