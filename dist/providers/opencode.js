/**
 * OpenCode provider adapter — wraps spawnOpencodeRun into the unified RunResult.
 */
import { cleanOpencodeOutput, spawnOpencodeRun, } from "../opencode/exec.js";
export async function runOpencode(opts) {
    const result = await spawnOpencodeRun({
        prompt: opts.prompt,
        model: opts.model,
        agent: opts.agent,
        cwd: opts.cwd,
        timeout_ms: opts.timeout_ms ?? 240_000,
    });
    if (result.ok) {
        return {
            provider: "opencode",
            ok: true,
            text: cleanOpencodeOutput(result.stdout) || "",
            duration_ms: result.duration_ms,
            model: opts.model,
        };
    }
    return {
        provider: "opencode",
        ok: false,
        text: "",
        error_message: result.error_message || "opencode run failed",
        duration_ms: result.duration_ms,
        model: opts.model,
    };
}
//# sourceMappingURL=opencode.js.map