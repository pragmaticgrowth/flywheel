/**
 * Wires every tool into the server in one call.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerCrossReviewTool } from "./cross-review.js";
import { registerExecTool } from "./exec.js";
import { registerMetaTools } from "./meta.js";
import { registerPresetTools } from "./presets.js";
import { registerPrReviewTool } from "./pr-review.js";
import { registerSessionTools } from "./sessions.js";

export function registerAllTools(server: McpServer): void {
  registerExecTool(server);
  registerMetaTools(server);
  registerSessionTools(server);
  registerPresetTools(server);
  registerCrossReviewTool(server);
  registerPrReviewTool(server);
}
