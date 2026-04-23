/**
 * Wires every tool into the server in one call.
 */
import { registerAuditTool } from "./audit.js";
import { registerCrossReviewTool } from "./cross-review.js";
import { registerDiscussTool } from "./discuss.js";
import { registerExecTool } from "./exec.js";
import { registerMetaTools } from "./meta.js";
import { registerPresetTools } from "./presets.js";
import { registerPrReviewTool } from "./pr-review.js";
import { registerResearchTool } from "./research.js";
import { registerSessionTools } from "./sessions.js";
export function registerAllTools(server) {
    registerExecTool(server);
    registerMetaTools(server);
    registerSessionTools(server);
    registerPresetTools(server);
    registerResearchTool(server);
    registerCrossReviewTool(server);
    registerPrReviewTool(server);
    registerDiscussTool(server);
    registerAuditTool(server);
}
//# sourceMappingURL=index.js.map