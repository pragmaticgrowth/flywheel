/**
 * Unit tests for the MCP response helpers in src/utils/errors.ts.
 *
 * Covers the 4 wrapping cases of createJsonResponse, the simple error
 * helpers, and every branch of execResultToToolResponse (success + 4
 * failure modes from DroidExecFailure).
 */

import { describe, expect, it } from "vitest";
import {
  createErrorResponse,
  createJsonResponse,
  createUnexpectedErrorResponse,
  execResultToToolResponse,
} from "./errors.js";
import type { SpawnDroidExecResult } from "../droid/exec.js";
import type { ParsedStreamJson } from "../droid/output.js";

function emptyParsed(): ParsedStreamJson {
  return { text: "", events: [], errors: [] };
}

function makeResult(
  overrides: Partial<SpawnDroidExecResult> = {},
): SpawnDroidExecResult {
  return {
    argv: ["exec", "hi"],
    exit_code: 0,
    signal: null,
    duration_ms: 100,
    stdout: "",
    stderr: "",
    parsed: emptyParsed(),
    ok: true,
    ...overrides,
  };
}

describe("createJsonResponse", () => {
  it("wraps a plain object as structuredContent directly", () => {
    const r = createJsonResponse({ count: 5, items: ["a", "b"] });
    expect(r.isError).toBeUndefined();
    expect(r.structuredContent).toEqual({ count: 5, items: ["a", "b"] });
    expect(r.content[0]?.text).toContain('"count": 5');
  });

  it("wraps an array as { items: [...] }", () => {
    const r = createJsonResponse([1, 2, 3]);
    expect(r.structuredContent).toEqual({ items: [1, 2, 3] });
  });

  it("wraps a primitive number as { value: n }", () => {
    const r = createJsonResponse(42);
    expect(r.structuredContent).toEqual({ value: 42 });
  });

  it("wraps a primitive string as { value: '...' }", () => {
    const r = createJsonResponse("hello");
    expect(r.structuredContent).toEqual({ value: "hello" });
  });

  it("wraps null as { value: null }", () => {
    const r = createJsonResponse(null);
    expect(r.structuredContent).toEqual({ value: null });
  });

  it("respects pretty=false (single-line JSON)", () => {
    const r = createJsonResponse({ a: 1 }, false);
    expect(r.content[0]?.text).toBe('{"a":1}');
  });

  it("uses 2-space indentation by default", () => {
    const r = createJsonResponse({ a: 1 });
    expect(r.content[0]?.text).toBe('{\n  "a": 1\n}');
  });
});

describe("createErrorResponse", () => {
  it("returns isError=true with the message in content", () => {
    const r = createErrorResponse("oh no");
    expect(r.isError).toBe(true);
    expect(r.content).toEqual([{ type: "text", text: "oh no" }]);
  });

  it("does not set structuredContent on errors", () => {
    const r = createErrorResponse("oh no");
    expect(r.structuredContent).toBeUndefined();
  });
});

describe("createUnexpectedErrorResponse", () => {
  it("formats Error instances as 'Name: message'", () => {
    const err = new TypeError("bad type");
    const r = createUnexpectedErrorResponse(err);
    expect(r.isError).toBe(true);
    expect(r.content[0]?.text).toBe(
      "unexpected internal error: TypeError: bad type",
    );
  });

  it("formats string throws as String(...)", () => {
    const r = createUnexpectedErrorResponse("just a string");
    expect(r.content[0]?.text).toBe(
      "unexpected internal error: just a string",
    );
  });

  it("formats objects via String(...)", () => {
    const r = createUnexpectedErrorResponse({ foo: "bar" });
    // String({foo:"bar"}) → "[object Object]"
    expect(r.content[0]?.text).toContain("unexpected internal error:");
  });
});

describe("execResultToToolResponse — success path", () => {
  it("returns text + structuredContent for a successful run", () => {
    const result = makeResult({
      stdout: "stuff",
      parsed: {
        text: "hello there",
        events: [],
        errors: [],
        session_id: "sid-1",
        model: "custom:glm-5-turbo",
        cwd: "/Users/serkan/nt-dev",
        num_turns: 1,
        duration_ms: 5000,
        usage: { input_tokens: 100, output_tokens: 50 },
      },
    });
    const r = execResultToToolResponse(result);
    expect(r.isError).toBeUndefined();
    expect(r.content[0]?.text).toContain("hello there");
    expect(r.content[0]?.text).toContain("session_id: sid-1");
    expect(r.content[0]?.text).toContain("model: custom:glm-5-turbo");
    expect(r.content[0]?.text).toContain("tokens: 100 in / 50 out");
    expect(r.structuredContent?.session_id).toBe("sid-1");
    expect(r.structuredContent?.text).toBe("hello there");
    expect(r.structuredContent?.model).toBe("custom:glm-5-turbo");
    expect(r.structuredContent?.cwd).toBe("/Users/serkan/nt-dev");
  });

  it("substitutes '(no output)' when there's no parsed text", () => {
    const result = makeResult({
      parsed: { text: "", events: [], errors: [] },
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toBe("(no output)");
  });

  it("includes only meta lines when there's no text but session metadata exists", () => {
    const result = makeResult({
      parsed: {
        text: "",
        events: [],
        errors: [],
        session_id: "sid-1",
        model: "custom:m",
      },
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toContain("session_id: sid-1");
    expect(r.content[0]?.text).toContain("model: custom:m");
  });
});

describe("execResultToToolResponse — failure paths", () => {
  it("formats nonzero_exit failures with stderr", () => {
    const result = makeResult({
      ok: false,
      exit_code: 1,
      stderr: "Invalid model: custom:fake",
      failure: "nonzero_exit",
      error_message: "Invalid model: custom:fake",
    });
    const r = execResultToToolResponse(result);
    expect(r.isError).toBe(true);
    expect(r.content[0]?.text).toContain("droid exec failed (nonzero_exit)");
    expect(r.content[0]?.text).toContain("exit_code=1");
    expect(r.content[0]?.text).toContain("--- stderr ---");
    expect(r.content[0]?.text).toContain("Invalid model: custom:fake");
  });

  it("formats spawn_error failures", () => {
    const result = makeResult({
      ok: false,
      exit_code: null,
      failure: "spawn_error",
      error_message: "failed to spawn droid: ENOENT",
    });
    const r = execResultToToolResponse(result);
    expect(r.isError).toBe(true);
    expect(r.content[0]?.text).toContain("droid exec failed (spawn_error)");
    expect(r.content[0]?.text).toContain("ENOENT");
    expect(r.content[0]?.text).toContain("exit_code=null");
  });

  it("formats timeout failures", () => {
    const result = makeResult({
      ok: false,
      exit_code: null,
      signal: "SIGTERM",
      failure: "timeout",
      error_message: "droid exec timed out after 5000ms",
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toContain("droid exec failed (timeout)");
    expect(r.content[0]?.text).toContain("signal=SIGTERM");
  });

  it("formats stream_errors failures", () => {
    const result = makeResult({
      ok: false,
      exit_code: 0,
      stdout: "stuff",
      parsed: {
        text: "partial output",
        events: [{ type: "system", subtype: "init" }],
        errors: [{ type: "tool_error", message: "permission denied" }],
        session_id: "sid-1",
      },
      failure: "stream_errors",
      error_message: "permission denied",
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toContain("droid exec failed (stream_errors)");
    expect(r.content[0]?.text).toContain("session_id=sid-1");
    expect(r.content[0]?.text).toContain("--- parsed.text ---");
    expect(r.content[0]?.text).toContain("partial output");
    expect(r.content[0]?.text).toContain("--- parsed.errors (1) ---");
    expect(r.content[0]?.text).toContain("permission denied");
    expect(r.content[0]?.text).toContain("--- last 1 stream events");
  });

  it("formats flags_error failures", () => {
    const result = makeResult({
      ok: false,
      exit_code: null,
      argv: [],
      failure: "flags_error",
      error_message: "prompt and prompt_file are mutually exclusive",
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toContain("droid exec failed (flags_error)");
    expect(r.content[0]?.text).toContain("mutually exclusive");
  });

  it("includes raw stdout tail only when stream parsing captured zero events", () => {
    const result = makeResult({
      ok: false,
      exit_code: 1,
      stdout: "this is a non-stream-json text dump from droid",
      stderr: "",
      parsed: { text: "", events: [], errors: [] },
      failure: "nonzero_exit",
      error_message: "droid exec exited with code 1",
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).toContain("--- raw stdout tail ---");
    expect(r.content[0]?.text).toContain(
      "this is a non-stream-json text dump",
    );
  });

  it("does NOT include raw stdout tail when events were parsed", () => {
    const result = makeResult({
      ok: false,
      exit_code: 1,
      stdout: "stream contents",
      parsed: {
        text: "",
        events: [{ type: "system", subtype: "init" }],
        errors: [],
      },
      failure: "nonzero_exit",
      error_message: "droid exec exited with code 1",
    });
    const r = execResultToToolResponse(result);
    expect(r.content[0]?.text).not.toContain("--- raw stdout tail ---");
  });
});
