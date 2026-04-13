/**
 * Pure translation from a typed DroidExecFlags object to an argv[] array
 * suitable for `spawn("droid", ["exec", ...argv])`. No defaults applied —
 * callers (e.g. exec.ts) are responsible for setting output_format: "stream-json"
 * before calling. This keeps the module pure and tests simple.
 *
 * Validation (mutual exclusion) lives here because it's inherent to the input
 * shape, not a runtime concern.
 */
/**
 * Raised for invalid combinations of flags detected at build time (before we
 * ever spawn droid). Callers should return these as isError responses from
 * the MCP tool layer instead of letting them bubble across the transport.
 */
export class DroidFlagsError extends Error {
    constructor(message) {
        super(message);
        this.name = "DroidFlagsError";
    }
}
function encodeTag(tag) {
    return typeof tag === "string" ? tag : JSON.stringify(tag);
}
export function buildDroidExecArgs(flags) {
    if (flags.prompt !== undefined && flags.prompt_file !== undefined) {
        throw new DroidFlagsError("prompt and prompt_file are mutually exclusive — pass one or the other");
    }
    if (flags.session_id !== undefined && flags.fork_session_id !== undefined) {
        throw new DroidFlagsError("session_id and fork_session_id are mutually exclusive — pass one or the other");
    }
    if (flags.auto !== undefined && flags.allow_unsafe === true) {
        throw new DroidFlagsError("auto and allow_unsafe are mutually exclusive — --skip-permissions-unsafe cannot be combined with --auto");
    }
    if (flags.mission === true && flags.auto !== "high" && flags.allow_unsafe !== true) {
        throw new DroidFlagsError("mission mode requires auto: 'high' or allow_unsafe: true");
    }
    const args = [];
    if (flags.prompt_file !== undefined) {
        args.push("--file", flags.prompt_file);
    }
    if (flags.model !== undefined) {
        args.push("--model", flags.model);
    }
    if (flags.reasoning_effort !== undefined) {
        args.push("--reasoning-effort", flags.reasoning_effort);
    }
    if (flags.auto !== undefined) {
        args.push("--auto", flags.auto);
    }
    if (flags.allow_unsafe === true) {
        args.push("--skip-permissions-unsafe");
    }
    if (flags.output_format !== undefined) {
        args.push("--output-format", flags.output_format);
    }
    if (flags.input_format !== undefined) {
        args.push("--input-format", flags.input_format);
    }
    if (flags.session_id !== undefined) {
        args.push("--session-id", flags.session_id);
    }
    if (flags.fork_session_id !== undefined) {
        args.push("--fork", flags.fork_session_id);
    }
    if (flags.cwd !== undefined) {
        args.push("--cwd", flags.cwd);
    }
    if (flags.worktree === true) {
        args.push("--worktree");
    }
    else if (typeof flags.worktree === "string") {
        args.push("--worktree", flags.worktree);
    }
    if (flags.worktree_dir !== undefined) {
        args.push("--worktree-dir", flags.worktree_dir);
    }
    if (flags.enabled_tools !== undefined && flags.enabled_tools.length > 0) {
        args.push("--enabled-tools", flags.enabled_tools.join(","));
    }
    if (flags.disabled_tools !== undefined && flags.disabled_tools.length > 0) {
        args.push("--disabled-tools", flags.disabled_tools.join(","));
    }
    if (flags.list_tools === true) {
        args.push("--list-tools");
    }
    if (flags.tags !== undefined) {
        for (const tag of flags.tags) {
            args.push("--tag", encodeTag(tag));
        }
    }
    if (flags.log_group_id !== undefined) {
        args.push("--log-group-id", flags.log_group_id);
    }
    if (flags.mission === true) {
        args.push("--mission");
    }
    if (flags.system_prompt !== undefined) {
        args.push("--append-system-prompt", flags.system_prompt);
    }
    if (flags.system_prompt_file !== undefined) {
        args.push("--append-system-prompt-file", flags.system_prompt_file);
    }
    if (flags.use_spec === true) {
        args.push("--use-spec");
    }
    if (flags.spec_model !== undefined) {
        args.push("--spec-model", flags.spec_model);
    }
    if (flags.spec_reasoning_effort !== undefined) {
        args.push("--spec-reasoning-effort", flags.spec_reasoning_effort);
    }
    // --settings is undocumented in `droid exec --help` but the binary accepts it.
    if (flags.settings_file !== undefined) {
        args.push("--settings", flags.settings_file);
    }
    // Positional prompt MUST be last so it's not consumed as a flag value.
    if (flags.prompt !== undefined) {
        args.push(flags.prompt);
    }
    return args;
}
//# sourceMappingURL=flags.js.map