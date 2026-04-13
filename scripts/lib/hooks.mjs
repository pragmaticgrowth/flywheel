/**
 * Shared hook I/O primitives for mcp-do hook scripts.
 * Claude Code hooks communicate via stdin (JSON input) and
 * stdout (JSON decision output) with stderr for logging.
 */

import fs from "node:fs";
import process from "node:process";

/**
 * Read and parse the JSON hook input from stdin.
 * Returns an empty object if stdin is empty or unparseable.
 */
export function readHookInput() {
  try {
    const raw = fs.readFileSync(0, "utf8").trim();
    if (!raw) {
      return {};
    }
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

/**
 * Emit a hook decision to stdout (e.g., { decision: "block", reason: "..." }).
 * @param {Record<string, unknown>} payload
 */
export function emitDecision(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

/**
 * Log a note to stderr (visible to the user but doesn't affect the hook decision).
 * @param {string | null | undefined} message
 */
export function logNote(message) {
  if (!message) {
    return;
  }
  process.stderr.write(`${message}\n`);
}
