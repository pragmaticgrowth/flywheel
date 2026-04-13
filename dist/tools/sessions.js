/**
 * Session tools: do_session_continue + do_session_list.
 * Sessions remain droid-only — opencode session management requires
 * a running `opencode serve` instance.
 */
import { z } from "zod";
import { DEFAULT_MODELS } from "../config.js";
import { spawnDroidExec } from "../droid/exec.js";
import { listSessions } from "../droid/sessions.js";
import { AutoLevelSchema, ReasoningEffortSchema } from "../schemas/exec.js";
import { resolveCwd } from "../utils/cwd.js";
import { createJsonResponse, createUnexpectedErrorResponse, execResultToToolResponse, } from "../utils/errors.js";
const sessionExecShape = {
    prompt: z.string(),
    cwd: z.string().optional(),
    model: z.string().optional(),
    auto: AutoLevelSchema.optional(),
    reasoning_effort: ReasoningEffortSchema.optional(),
    timeout_ms: z.number().int().positive().optional(),
};
export function registerSessionTools(server) {
    server.registerTool("do_session_continue", {
        description: "Continue an existing droid session by id — loads conversation history and runs the new prompt in the same thread.",
        inputSchema: { session_id: z.string(), ...sessionExecShape },
    }, async ({ session_id, prompt, cwd, model, auto, reasoning_effort, timeout_ms, }) => {
        try {
            const result = await spawnDroidExec({
                session_id,
                prompt,
                model: model ?? DEFAULT_MODELS.droid,
                auto,
                reasoning_effort,
            }, { cwd: resolveCwd(cwd), timeout_ms });
            return execResultToToolResponse(result);
        }
        catch (err) {
            return createUnexpectedErrorResponse(err);
        }
    });
    server.registerTool("do_session_list", {
        description: "List droid sessions, filtered by cwd by default. Pass scan_disk=true for the complete list (sessions-index.json is incomplete for `droid exec` sessions).",
        inputSchema: {
            cwd: z.string().optional(),
            all: z.boolean().optional().describe("Ignore cwd filter."),
            search: z.string().optional().describe("Substring filter on title."),
            scan_disk: z
                .boolean()
                .optional()
                .describe("Walk disk for complete results (slower but authoritative)."),
            limit: z.number().int().positive().optional(),
        },
    }, async ({ cwd, all, search, scan_disk, limit }) => {
        try {
            const sessions = await listSessions({
                cwd: resolveCwd(cwd),
                all,
                search,
                scan_disk,
                limit,
            });
            return createJsonResponse({
                count: sessions.length,
                source: scan_disk ? "disk_walk" : "sessions_index",
                sessions,
            });
        }
        catch (err) {
            return createUnexpectedErrorResponse(err);
        }
    });
}
//# sourceMappingURL=sessions.js.map