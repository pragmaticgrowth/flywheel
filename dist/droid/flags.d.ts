/**
 * Pure translation from a typed DroidExecFlags object to an argv[] array
 * suitable for `spawn("droid", ["exec", ...argv])`. No defaults applied —
 * callers (e.g. exec.ts) are responsible for setting output_format: "stream-json"
 * before calling. This keeps the module pure and tests simple.
 *
 * Validation (mutual exclusion) lives here because it's inherent to the input
 * shape, not a runtime concern.
 */
export type AutoLevel = "low" | "medium" | "high";
export type ReasoningEffort = "off" | "low" | "medium" | "high" | "max" | "xhigh" | "minimal" | "none";
export type TagSpec = string | {
    name: string;
    metadata?: Record<string, unknown>;
};
export interface DroidExecFlags {
    prompt?: string;
    prompt_file?: string;
    model?: string;
    auto?: AutoLevel;
    allow_unsafe?: boolean;
    output_format?: "text" | "json" | "stream-json";
    input_format?: "text" | "stream-json";
    session_id?: string;
    fork_session_id?: string;
    cwd?: string;
    worktree?: boolean | string;
    worktree_dir?: string;
    enabled_tools?: string[];
    disabled_tools?: string[];
    tags?: TagSpec[];
    log_group_id?: string;
    mission?: boolean;
    system_prompt?: string;
    system_prompt_file?: string;
    reasoning_effort?: ReasoningEffort;
    spec_model?: string;
    spec_reasoning_effort?: string;
    use_spec?: boolean;
    settings_file?: string;
    list_tools?: boolean;
}
/**
 * Raised for invalid combinations of flags detected at build time (before we
 * ever spawn droid). Callers should return these as isError responses from
 * the MCP tool layer instead of letting them bubble across the transport.
 */
export declare class DroidFlagsError extends Error {
    constructor(message: string);
}
export declare function buildDroidExecArgs(flags: DroidExecFlags): string[];
