#!/usr/bin/env node

/**
 * Session lifecycle hook for mcp-do.
 *
 * SessionStart: Sets DO_SESSION_ID env var via CLAUDE_ENV_FILE
 *               so other hook scripts can track which session they belong to.
 *
 * SessionEnd:   No-op — droid processes don't persist beyond their exec call.
 *
 * Adapted from codex-plugin-cc's session-lifecycle-hook.mjs.
 */

import fs from "node:fs";
import process from "node:process";

import { readHookInput } from "./lib/hooks.mjs";

const SESSION_ID_ENV = "DO_SESSION_ID";

function shellEscape(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}

function appendEnvVar(name, value) {
  if (!process.env.CLAUDE_ENV_FILE || value == null || value === "") {
    return;
  }
  fs.appendFileSync(
    process.env.CLAUDE_ENV_FILE,
    `export ${name}=${shellEscape(value)}\n`,
    "utf8",
  );
}

function handleSessionStart(input) {
  appendEnvVar(SESSION_ID_ENV, input.session_id);
}

function main() {
  const input = readHookInput();
  const eventName = process.argv[2] ?? input.hook_event_name ?? "";

  if (eventName === "SessionStart") {
    handleSessionStart(input);
  }
  // SessionEnd: no-op — droid processes don't persist beyond their exec call
}

try {
  main();
} catch (error) {
  // Fail open — env var setup is not worth blocking the session for
  process.stderr.write(
    `${error instanceof Error ? error.message : String(error)}\n`,
  );
}
