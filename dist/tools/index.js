/**
 * Wires every tool into the server in one call.
 */
import { registerCrossReviewTool } from "./cross-review.js";
import { registerExecTool } from "./exec.js";
import { registerMetaTools } from "./meta.js";
import { registerPresetTools } from "./presets.js";
import { registerPrReviewTool } from "./pr-review.js";
import { registerSessionTools } from "./sessions.js";
export function registerAllTools(server) {
    registerExecTool(server);
    registerMetaTools(server);
    registerSessionTools(server);
    registerPresetTools(server);
    registerCrossReviewTool(server);
    registerPrReviewTool(server);
}
//# sourceMappingURL=index.js.map