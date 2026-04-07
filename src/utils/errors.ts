/**
 * Helpers for converting internal results into the MCP isError shape.
 * Every tool handler MUST wrap its body in try/catch and call
 * createUnexpectedErrorResponse on uncaught failures, so exceptions never
 * cross the MCP transport boundary (spec §9).
 */

import type { SpawnDroidExecResult } from "../droid/exec.js";

export interface McpToolResponse {
  [key: string]: unknown;
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
  structuredContent?: Record<string, unknown>;
}

export function createTextResponse(
  text: string,
  structuredContent?: Record<string, unknown>,
): McpToolResponse {
  const resp: McpToolResponse = { content: [{ type: "text", text }] };
  if (structuredContent !== undefined) resp.structuredContent = structuredContent;
  return resp;
}

export function createJsonResponse(
  value: unknown,
  pretty = true,
): McpToolResponse {
  const text = pretty ? JSON.stringify(value, null, 2) : JSON.stringify(value);
  return {
    content: [{ type: "text", text }],
    structuredContent: typeof value === "object" && value !== null
      ? (value as Record<string, unknown>)
      : { value },
  };
}

export function createErrorResponse(message: string): McpToolResponse {
  return {
    isError: true,
    content: [{ type: "text", text: message }],
  };
}

export function createUnexpectedErrorResponse(err: unknown): McpToolResponse {
  const message =
    err instanceof Error ? `${err.name}: ${err.message}` : String(err);
  return createErrorResponse(`unexpected internal error: ${message}`);
}

/**
 * Convert a SpawnDroidExecResult into the canonical MCP success/failure
 * shape. Includes the parsed stream-json text on success and a structured
 * payload with session_id, model, usage, etc.
 */
export function execResultToToolResponse(
  result: SpawnDroidExecResult,
): McpToolResponse {
  if (!result.ok) {
    const detail = [
      `droid exec failed (${result.failure ?? "unknown"}): ${result.error_message ?? "no message"}`,
      result.stderr.trim() && `--- stderr ---\n${result.stderr.trim()}`,
    ]
      .filter(Boolean)
      .join("\n");
    return createErrorResponse(detail);
  }

  const structured: Record<string, unknown> = {
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
  const lines: string[] = [];
  if (result.parsed.text) lines.push(result.parsed.text);
  const meta: string[] = [];
  if (result.parsed.session_id) meta.push(`session_id: ${result.parsed.session_id}`);
  if (result.parsed.model) meta.push(`model: ${result.parsed.model}`);
  if (result.parsed.usage?.input_tokens !== undefined) {
    meta.push(
      `tokens: ${result.parsed.usage.input_tokens} in / ${result.parsed.usage.output_tokens ?? 0} out`,
    );
  }
  if (meta.length > 0) {
    if (lines.length > 0) lines.push("");
    lines.push(`---`, ...meta);
  }

  return {
    content: [{ type: "text", text: lines.join("\n") || "(no output)" }],
    structuredContent: structured,
  };
}
