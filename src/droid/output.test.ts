import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { parseStreamJson } from "./output.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_DIR = resolve(__dirname, "../../docs/fixtures");

function loadFixture(name: string): string {
  return readFileSync(resolve(FIXTURE_DIR, name), "utf8");
}

describe("parseStreamJson — success fixture (stream-json-hello.jsonl)", () => {
  const fixture = loadFixture("stream-json-hello.jsonl");
  const parsed = parseStreamJson(fixture);

  it("captures session_id from the init event", () => {
    expect(parsed.session_id).toBe("18b73104-bbc7-4a20-b41b-d70aa8169987");
  });

  it("captures model from the init event", () => {
    expect(parsed.model).toBe("custom:BYOK-MiniMax-M2.7-30");
  });

  it("captures cwd from the init event", () => {
    expect(parsed.cwd).toBe("/Users/serkan/mcp-droid");
  });

  it("uses completion.finalText as the canonical text", () => {
    expect(parsed.text).toBe("hi");
  });

  it("captures usage from the completion event", () => {
    expect(parsed.usage).toEqual({
      input_tokens: 43082,
      output_tokens: 21,
      cache_read_input_tokens: 5728,
      cache_creation_input_tokens: 0,
      thinking_tokens: 18,
    });
  });

  it("captures num_turns and duration_ms from the completion event", () => {
    expect(parsed.num_turns).toBe(1);
    expect(parsed.duration_ms).toBe(11041);
  });

  it("collects every non-blank JSONL line into events[]", () => {
    // 5 non-blank lines in the fixture: init, user message, reasoning,
    // assistant message, completion
    expect(parsed.events).toHaveLength(5);
  });

  it("reports no errors on a successful run", () => {
    expect(parsed.errors).toEqual([]);
  });
});

describe("parseStreamJson — error fixture (stream-json-error.jsonl)", () => {
  // Empirical finding (verified by trying bad-model, bad-file, incompatible
  // flags, bad enabled-tools, etc.): droid does NOT emit stream-json error
  // *events* for pre-launch failures. All the failure modes we tested instead
  // produced exit code ≠ 0 plus plain-text stderr (not JSONL). The captured
  // fixture here is the `2>&1` merged output for a bad-model failure — it
  // contains no valid JSON lines.
  //
  // This means: the parser sees that input, returns an empty-but-valid shape,
  // and the exec.ts layer is responsible for catching the exit-code / stderr
  // failure path. The parser's errors[] detection remains for mid-stream
  // failures if droid ever adds them — covered by the synthesized test below.
  const fixture = loadFixture("stream-json-error.jsonl");
  const parsed = parseStreamJson(fixture);

  it("does not crash on stderr-only text output", () => {
    expect(parsed.text).toBe("");
  });

  it("finds no JSONL events because droid wrote plain stderr text", () => {
    expect(parsed.events).toEqual([]);
  });

  it("reports no stream-level errors (the failure was exit-code based)", () => {
    expect(parsed.errors).toEqual([]);
  });
});

describe("parseStreamJson — synthesized mid-stream errors", () => {
  it("collects events with type matching /error/i into errors[]", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        '{"type":"tool_error","message":"permission denied","session_id":"s"}',
      ].join("\n"),
    );
    expect(parsed.errors).toHaveLength(1);
    expect(parsed.errors[0]?.type).toBe("tool_error");
  });

  it("collects events with subtype matching /failed/i into errors[]", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        '{"type":"tool","subtype":"failed","message":"boom","session_id":"s"}',
      ].join("\n"),
    );
    expect(parsed.errors).toHaveLength(1);
    expect(parsed.errors[0]?.subtype).toBe("failed");
  });

  it("still captures completion text even when an error event is present", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        '{"type":"tool_error","message":"retryable","session_id":"s"}',
        '{"type":"completion","finalText":"eventually worked","numTurns":2,"durationMs":5,"session_id":"s","timestamp":0}',
      ].join("\n"),
    );
    expect(parsed.errors).toHaveLength(1);
    expect(parsed.text).toBe("eventually worked");
  });
});

describe("parseStreamJson — robustness", () => {
  it("ignores blank lines", () => {
    const parsed = parseStreamJson(
      [
        "",
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        "",
        '{"type":"completion","finalText":"hi","numTurns":1,"durationMs":10,"session_id":"s","timestamp":0}',
        "",
      ].join("\n"),
    );
    expect(parsed.session_id).toBe("s");
    expect(parsed.text).toBe("hi");
    expect(parsed.errors).toEqual([]);
  });

  it("falls back to concatenated assistant messages when completion is missing", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        '{"type":"message","role":"user","id":"u1","text":"ping","timestamp":0,"session_id":"s"}',
        '{"type":"message","role":"assistant","id":"a1","text":"pong","timestamp":1,"session_id":"s"}',
        '{"type":"message","role":"assistant","id":"a2","text":" again","timestamp":2,"session_id":"s"}',
      ].join("\n"),
    );
    expect(parsed.text).toBe("pong again");
  });

  it("does NOT fail on unknown event types — it collects them in events[]", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        '{"type":"mystery","foo":"bar","session_id":"s"}',
      ].join("\n"),
    );
    expect(parsed.events).toHaveLength(2);
    expect(parsed.errors).toEqual([]);
  });

  it("skips malformed JSON lines without throwing", () => {
    const parsed = parseStreamJson(
      [
        '{"type":"system","subtype":"init","session_id":"s","model":"m","cwd":"/x","tools":[],"reasoning_effort":"none"}',
        "this is not json",
        '{"type":"completion","finalText":"ok","numTurns":1,"durationMs":1,"session_id":"s","timestamp":0}',
      ].join("\n"),
    );
    expect(parsed.session_id).toBe("s");
    expect(parsed.text).toBe("ok");
  });
});
