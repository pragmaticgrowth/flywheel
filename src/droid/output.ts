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

const ERROR_PATTERN = /error|failed|failure/i;

function isErrorEvent(event: DroidEvent): boolean {
  if (typeof event.type === "string" && ERROR_PATTERN.test(event.type)) {
    return true;
  }
  if (typeof event.subtype === "string" && ERROR_PATTERN.test(event.subtype)) {
    return true;
  }
  return false;
}

export function parseStreamJson(stdout: string): ParsedStreamJson {
  const result: ParsedStreamJson = {
    text: "",
    events: [],
    errors: [],
  };

  const assistantMessages: string[] = [];
  let completionFinalText: string | undefined;

  for (const rawLine of stdout.split("\n")) {
    const line = rawLine.trim();
    if (line === "") continue;

    let event: DroidEvent;
    try {
      event = JSON.parse(line) as DroidEvent;
    } catch {
      // Malformed line — skip silently. droid's stream-json should never
      // emit this, but we don't want a single bad byte to crash the parser.
      continue;
    }

    result.events.push(event);

    if (isErrorEvent(event)) {
      result.errors.push(event);
      // Continue parsing — don't early-return. We still want usage + text
      // captured when available, and the caller decides what to do with
      // the combination.
    }

    // system.init → capture session_id, model, cwd
    if (event.type === "system" && event.subtype === "init") {
      if (typeof event.session_id === "string") {
        result.session_id = event.session_id;
      }
      if (typeof event.model === "string") {
        result.model = event.model;
      }
      if (typeof event.cwd === "string") {
        result.cwd = event.cwd;
      }
      continue;
    }

    // assistant message → fallback text source
    if (
      event.type === "message" &&
      event.role === "assistant" &&
      typeof event.text === "string"
    ) {
      assistantMessages.push(event.text);
      continue;
    }

    // completion → canonical final text + usage + timing
    if (event.type === "completion") {
      if (typeof event.finalText === "string") {
        completionFinalText = event.finalText;
      }
      if (typeof event.numTurns === "number") {
        result.num_turns = event.numTurns;
      }
      if (typeof event.durationMs === "number") {
        result.duration_ms = event.durationMs;
      }
      if (event.usage && typeof event.usage === "object") {
        result.usage = event.usage as DroidUsage;
      }
      // completion also carries session_id — use it as a fallback if init
      // was missing (e.g. truncated stream)
      if (!result.session_id && typeof event.session_id === "string") {
        result.session_id = event.session_id;
      }
      continue;
    }
  }

  // Prefer completion.finalText; fall back to concatenated assistant messages.
  result.text =
    completionFinalText !== undefined
      ? completionFinalText
      : assistantMessages.join("");

  return result;
}
