/**
 * Thin wrapper around `opencode run` for MCP tools that want to delegate a
 * one-shot prompt to a specific opencode agent + model. Mirrors the shape of
 * spawnDroidExec but intentionally much smaller — opencode's output is plain
 * text (no stream-json), so we only capture stdout/stderr and an exit code.
 *
 * Binary resolution:
 *   1. OPENCODE_BIN env var (explicit override)
 *   2. `opencode` on PATH
 *   3. ~/.opencode/bin/opencode (default install location)
 */
import { spawn } from "node:child_process";
import { delimiter } from "node:path";
import { homedir } from "node:os";
import { join } from "node:path";
const DEFAULT_OPENCODE_BIN_DIR = join(homedir(), ".opencode", "bin");
const SIGKILL_GRACE_MS = 3_000;
function resolveOpencodeBin() {
    return process.env.OPENCODE_BIN ?? "opencode";
}
/**
 * Build a PATH that includes ~/.opencode/bin so `opencode` resolves even when
 * the MCP server was launched from a minimal shell environment (common when
 * Claude Code spawns mcp-do at user scope).
 */
function buildEnv() {
    const existing = process.env.PATH ?? "";
    const parts = existing.split(delimiter);
    if (!parts.includes(DEFAULT_OPENCODE_BIN_DIR)) {
        parts.push(DEFAULT_OPENCODE_BIN_DIR);
    }
    return {
        ...process.env,
        PATH: parts.join(delimiter),
        // Disable automatic ~/.claude/CLAUDE.md loading so opencode sessions from
        // MCP calls don't drag the global Claude Code prompt into the model's
        // context — keeps cross-reviews focused on the review prompt itself.
        OPENCODE_DISABLE_CLAUDE_CODE: "1",
        // Opencode uses color escapes by default. Strip them at the source so
        // downstream text parsing doesn't have to.
        NO_COLOR: "1",
    };
}
export function spawnOpencodeRun(opts) {
    const bin = resolveOpencodeBin();
    const argv = ["run"];
    if (opts.agent)
        argv.push("--agent", opts.agent);
    if (opts.model)
        argv.push("--model", opts.model);
    argv.push(opts.prompt);
    const startedAt = Date.now();
    return new Promise((resolve) => {
        let child;
        try {
            child = spawn(bin, argv, {
                cwd: opts.cwd,
                env: buildEnv(),
                stdio: ["ignore", "pipe", "pipe"],
            });
        }
        catch (err) {
            resolve({
                argv,
                ok: false,
                stdout: "",
                stderr: "",
                exit_code: null,
                signal: null,
                duration_ms: Date.now() - startedAt,
                timed_out: false,
                error_message: `failed to spawn ${bin}: ${err instanceof Error ? err.message : String(err)}`,
            });
            return;
        }
        let stdout = "";
        let stderr = "";
        let timedOut = false;
        let sigkillTimer = null;
        const timeoutTimer = setTimeout(() => {
            timedOut = true;
            child.kill("SIGTERM");
            sigkillTimer = setTimeout(() => child.kill("SIGKILL"), SIGKILL_GRACE_MS);
        }, opts.timeout_ms);
        child.stdout?.on("data", (chunk) => {
            stdout += chunk.toString("utf8");
        });
        child.stderr?.on("data", (chunk) => {
            stderr += chunk.toString("utf8");
        });
        child.on("error", (err) => {
            clearTimeout(timeoutTimer);
            if (sigkillTimer)
                clearTimeout(sigkillTimer);
            resolve({
                argv,
                ok: false,
                stdout,
                stderr,
                exit_code: null,
                signal: null,
                duration_ms: Date.now() - startedAt,
                timed_out: false,
                error_message: `spawn error: ${err.message}`,
            });
        });
        child.on("exit", (code, signal) => {
            clearTimeout(timeoutTimer);
            if (sigkillTimer)
                clearTimeout(sigkillTimer);
            const duration_ms = Date.now() - startedAt;
            if (timedOut) {
                resolve({
                    argv,
                    ok: false,
                    stdout,
                    stderr,
                    exit_code: code,
                    signal,
                    duration_ms,
                    timed_out: true,
                    error_message: `opencode run timed out after ${opts.timeout_ms}ms`,
                });
                return;
            }
            if (code !== 0) {
                const tail = stderr.trim().slice(-800) || stdout.trim().slice(-800) || "(no output)";
                resolve({
                    argv,
                    ok: false,
                    stdout,
                    stderr,
                    exit_code: code,
                    signal,
                    duration_ms,
                    timed_out: false,
                    error_message: `opencode run exited ${code}${signal ? ` (signal ${signal})` : ""}: ${tail}`,
                });
                return;
            }
            resolve({
                argv,
                ok: true,
                stdout,
                stderr,
                exit_code: code,
                signal,
                duration_ms,
                timed_out: false,
            });
        });
    });
}
/**
 * Strip opencode's CLI chrome from stdout so callers get the assistant text
 * only. Removes ANSI escapes, the `> agent · model` banner, tool-call trace
 * lines (`→ Read file.ts`, `✱ Grep "pattern"`, `← Write file.ts`,
 * `% WebFetch https://...`, `✗ Error: ...`), and the trailing `time` summary.
 *
 * The trace-line regex is intentionally narrow: each prefix must be followed
 * by a known tool verb or pattern so that legitimate assistant output like
 * `$ npm install` or `✓ All tests passed` is preserved.
 */
export function cleanOpencodeOutput(raw) {
    // 1. Strip ANSI escape sequences.
    // eslint-disable-next-line no-control-regex
    const noAnsi = raw.replace(/\x1b\[[0-9;]*m/g, "");
    // 2. Drop framing lines that are opencode UI chrome, not model output.
    //    Match narrowly — only lines that look like opencode's specific trace
    //    format, not arbitrary lines starting with these Unicode chars.
    const lines = noAnsi.split("\n");
    const kept = [];
    for (const rawLine of lines) {
        const line = rawLine.replace(/\s+$/, "");
        if (/^> [\w-]+ · /.test(line))
            continue; // "> review · glm-5-turbo"
        if (/^→ (Read|Glob|Grep|Task|WebFetch|WebSearch|TodoWrite|LSP) /.test(line))
            continue;
        if (/^← (Read|Write|Edit|Glob|Grep|Task|WebFetch|WebSearch|LSP) /.test(line))
            continue;
        if (/^✱ (Grep|Glob|Read|WebSearch) /.test(line))
            continue;
        if (/^⚙ /.test(line))
            continue; // tool execution marker
        if (/^% (WebFetch|WebSearch) /.test(line))
            continue;
        if (/^✗ (Error|Failed|Timeout)/.test(line))
            continue;
        if (/^\s*opencode run /.test(line))
            continue; // `time` trailing echo
        kept.push(line);
    }
    return kept.join("\n").trim();
}
//# sourceMappingURL=exec.js.map