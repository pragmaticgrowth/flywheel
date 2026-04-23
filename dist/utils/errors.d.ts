/**
 * Helpers for converting internal results into the MCP isError shape.
 * Every tool handler MUST wrap its body in try/catch and call
 * createUnexpectedErrorResponse on uncaught failures, so exceptions never
 * cross the MCP transport boundary (spec §9).
 */
import type { SpawnDroidExecResult } from "../droid/exec.js";
export interface McpToolResponse {
    [key: string]: unknown;
    content: Array<{
        type: "text";
        text: string;
    }>;
    isError?: boolean;
    structuredContent?: Record<string, unknown>;
}
export declare function createJsonResponse(value: unknown, pretty?: boolean): McpToolResponse;
export declare function createErrorResponse(message: string): McpToolResponse;
export declare function createUnexpectedErrorResponse(err: unknown): McpToolResponse;
/**
 * Convert a SpawnDroidExecResult into the canonical MCP success/failure
 * shape. Includes the parsed stream-json text on success and a structured
 * payload with session_id, model, usage, etc.
 */
export declare function execResultToToolResponse(result: SpawnDroidExecResult): McpToolResponse;
