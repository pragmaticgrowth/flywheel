/**
 * Pure parser for `droid exec --output-format stream-json` output.
 *
 * Verified event shapes (from docs/fixtures/stream-json-hello.jsonl and
 * spec §7):
 *
 *   { type: "system", subtype: "init", cwd, session_id, model, tools[], reasoning_effort }
 *   { type: "message", role: "user" | "assistant", id, text, timestamp, session_id }
 *   { type: "reasoning", id, text, timestamp, session_id }
 *   { type: "completion", finalText, numTurns, durationMs, session_id, timestamp, usage }
 *
 * Unknown event types are collected in `events[]` but never fail the parse.
 * Anything looking like an error (type/subtype matching /error|failed/i) goes
 * into `errors[]`. If `errors[]` is non-empty after parsing, the caller should
 * treat the overall run as failed, even if the process exit code was 0.
 */
export interface DroidUsage {
    input_tokens?: number;
    output_tokens?: number;
    cache_read_input_tokens?: number;
    cache_creation_input_tokens?: number;
    thinking_tokens?: number;
}
export interface DroidEvent {
    type?: string;
    subtype?: string;
    [key: string]: unknown;
}
export interface ParsedStreamJson {
    session_id?: string;
    model?: string;
    cwd?: string;
    text: string;
    usage?: DroidUsage;
    num_turns?: number;
    duration_ms?: number;
    events: DroidEvent[];
    errors: DroidEvent[];
}
export declare function parseStreamJson(stdout: string): ParsedStreamJson;
