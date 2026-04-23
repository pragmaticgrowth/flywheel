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
export interface OpencodeRunOptions {
    prompt: string;
    model: string;
    agent?: string;
    cwd: string;
    timeout_ms: number;
}
export interface OpencodeRunResult {
    argv: string[];
    ok: boolean;
    stdout: string;
    stderr: string;
    exit_code: number | null;
    signal: NodeJS.Signals | null;
    duration_ms: number;
    timed_out: boolean;
    error_message?: string;
}
export declare function spawnOpencodeRun(opts: OpencodeRunOptions): Promise<OpencodeRunResult>;
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
export declare function cleanOpencodeOutput(raw: string): string;
