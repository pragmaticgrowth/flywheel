/**
 * Wires every mcp-droid tool into the server in one call.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerDroidExec } from "./exec.js";
import { registerMetaTools } from "./meta.js";
import { registerMissionTools } from "./missions.js";
import { registerPresetTools } from "./presets.js";
import { registerSessionTools } from "./sessions.js";
import { registerSpecTool } from "./spec.js";

export function registerAllTools(server: McpServer): void {
  registerDroidExec(server);
  registerMetaTools(server);
  registerSessionTools(server);
  registerMissionTools(server);
  registerSpecTool(server);
  registerPresetTools(server);
}
