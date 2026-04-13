/**
 * Helpers for converting internal results into the MCP isError shape.
 * Every tool handler MUST wrap its body in try/catch and call
 * createUnexpectedErrorResponse on uncaught failures, so exceptions never
 * cross the MCP transport boundary (spec §9).
 */
export function createJsonResponse(value, pretty = true) {
    const text = pretty ? JSON.stringify(value, null, 2) : JSON.stringify(value);
    // MCP spec: structuredContent MUST be a JSON object, not an array or
    // primitive. Wrap anything that isn't a plain object so callers don't
    // have to remember this rule.
    let structured;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
        structured = value;
    }
    else if (Array.isArray(value)) {
        structured = { items: value };
    }
    else {
        structured = { value };
    }
    return {
        content: [{ type: "text", text }],
        structuredContent: structured,
    };
}
export function createErrorResponse(message) {
    return {
        isError: true,
        content: [{ type: "text", text: message }],
    };
}
export function createUnexpectedErrorResponse(err) {
    const message = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
    return createErrorResponse(`unexpected internal error: ${message}`);
}
/**
 * Convert a SpawnDroidExecResult into the canonical MCP success/failure
 * shape. Includes the parsed stream-json text on success and a structured
 * payload with session_id, model, usage, etc.
 */
export function execResultToToolResponse(result) {
    if (!result.ok) {
        // Surface every piece of context we have. Droid has been observed to
        // exit nonzero with empty stderr and useful content only in stdout
        // (stream-json events: completion.finalText, tool_result with
        // isError:true, etc.) — so we include all of it.
        const sections = [
            `droid exec failed (${result.failure ?? "unknown"}): ${result.error_message ?? "no message"}`,
            `exit_code=${result.exit_code ?? "null"} signal=${result.signal ?? "null"} duration_ms=${result.duration_ms}`,
        ];
        if (result.parsed.session_id) {
            sections.push(`session_id=${result.parsed.session_id}`);
        }
        if (result.parsed.text && result.parsed.text.trim()) {
            const trimmed = result.parsed.text.trim();
            const sliced = trimmed.slice(0, 2000);
            sections.push(`--- parsed.text ---\n${sliced}${sliced.length < trimmed.length ? "\n… (truncated)" : ""}`);
        }
        if (result.parsed.errors.length > 0) {
            const errJson = JSON.stringify(result.parsed.errors, null, 2);
            const sliced = errJson.slice(0, 2000);
            sections.push(`--- parsed.errors (${result.parsed.errors.length}) ---\n${sliced}${sliced.length < errJson.length ? "\n… (truncated)" : ""}`);
        }
        // Include up to the last few stream events for context (most recent last).
        if (result.parsed.events.length > 0) {
            const tail = result.parsed.events.slice(-5);
            sections.push(`--- last ${tail.length} stream events (of ${result.parsed.events.length}) ---\n${tail
                .map((e) => {
                const type = typeof e.type === "string" ? e.type : "?";
                const subtype = typeof e.subtype === "string" ? `.${e.subtype}` : "";
                const preview = JSON.stringify(e).slice(0, 200);
                return `[${type}${subtype}] ${preview}`;
            })
                .join("\n")}`);
        }
        if (result.stderr.trim()) {
            sections.push(`--- stderr ---\n${result.stderr.trim().slice(0, 2000)}`);
        }
        if (result.stdout.trim() && result.parsed.events.length === 0) {
            // Only show raw stdout if stream parsing failed (no events captured).
            // Otherwise the parsed summary above is more useful.
            sections.push(`--- raw stdout tail ---\n${result.stdout.trim().slice(-2000)}`);
        }
        return createErrorResponse(sections.join("\n"));
    }
    const structured = {
        session_id: result.parsed.session_id,
        model: result.parsed.model,
        cwd: result.parsed.cwd,
        text: result.parsed.text,
        num_turns: result.parsed.num_turns,
        duration_ms: result.parsed.duration_ms,
        usage: result.parsed.usage,
        exit_code: result.exit_code,
        spawn_duration_ms: result.duration_ms,
    };
    // Build a human-readable text body. The first line is the assistant's
    // final text; trailing lines surface session metadata so chained calls
    // (e.g. droid_session_continue) can grab the session_id at a glance.
    const lines = [];
    if (result.parsed.text)
        lines.push(result.parsed.text);
    const meta = [];
    if (result.parsed.session_id)
        meta.push(`session_id: ${result.parsed.session_id}`);
    if (result.parsed.model)
        meta.push(`model: ${result.parsed.model}`);
    if (result.parsed.usage?.input_tokens !== undefined) {
        meta.push(`tokens: ${result.parsed.usage.input_tokens} in / ${result.parsed.usage.output_tokens ?? 0} out`);
    }
    if (meta.length > 0) {
        if (lines.length > 0)
            lines.push("");
        lines.push(`---`, ...meta);
    }
    return {
        content: [{ type: "text", text: lines.join("\n") || "(no output)" }],
        structuredContent: structured,
    };
}
//# sourceMappingURL=errors.js.map