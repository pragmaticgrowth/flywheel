#!/usr/bin/env node

/**
 * Stop-time review gate hook for mcp-do.
 *
 * When enabled, this hook runs before Claude stops and spawns a droid review
 * of the previous turn's code changes. If the review finds material issues,
 * the stop is blocked so Claude must fix them first.
 *
 * Adapted from codex-plugin-cc's stop-review-gate-hook.mjs.
 *
 * Fail-open: if droid is unavailable, times out, or returns ambiguous output,
 * the hook exits silently (allows the stop) rather than blocking.
 */

import process from "node:process";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { readHookInput, emitDecision, logNote } from "./lib/hooks.mjs";
import { getConfig } from "./lib/state.mjs";
import { loadPromptTemplate, interpolateTemplate } from "./lib/prompts.mjs";

// Must be less than hooks.json Stop timeout (900s) to ensure fail-open
const STOP_REVIEW_TIMEOUT_MS = 10 * 60 * 1000;
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..");
const MODEL = "custom:YK-GPT-5.4-xHigh-64";

function isDroidAvailable() {
  try {
    const result = spawnSync("droid", ["--version"], {
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "pipe", "pipe"],
    });
    return result.status === 0;
  } catch {
    return false;
  }
}

function buildStopReviewPrompt(input) {
  const lastAssistantMessage = String(
    input.last_assistant_message ?? "",
  ).trim();
  const template = loadPromptTemplate(ROOT_DIR, "stop-review-gate");
  const claudeResponseBlock = lastAssistantMessage
    ? ["Previous Claude response:", lastAssistantMessage].join("\n")
    : "";
  return interpolateTemplate(template, {
    CLAUDE_RESPONSE_BLOCK: claudeResponseBlock,
  });
}

function parseStopReviewOutput(rawOutput) {
  const text = String(rawOutput ?? "").trim();
  if (!text) {
    // Fail open — no output means we can't determine the verdict
    return { ok: true, reason: null };
  }

  const firstLine = text.split(/\r?\n/, 1)[0].trim().toUpperCase();
  if (firstLine.startsWith("ALLOW")) {
    return { ok: true, reason: null };
  }
  if (firstLine.startsWith("BLOCK")) {
    // Extract reason after "BLOCK:" (or just "BLOCK" without colon)
    const originalLine = text.split(/\r?\n/, 1)[0].trim();
    const colonIndex = originalLine.indexOf(":");
    const reason =
      colonIndex >= 0
        ? originalLine.slice(colonIndex + 1).trim()
        : originalLine;
    return {
      ok: false,
      reason: `Stop-time review found issues that need fixes before ending: ${reason || text}`,
    };
  }

  // Fail open — ambiguous output should not block the user
  logNote(
    "Stop-time review returned an unexpected format. Allowing stop.",
  );
  return { ok: true, reason: null };
}

function runStopReview(cwd, input) {
  const prompt = buildStopReviewPrompt(input);
  const result = spawnSync(
    "droid",
    ["exec", "--model", MODEL, "--auto", "high", "--output-format", "text"],
    {
      cwd,
      env: process.env,
      encoding: "utf8",
      timeout: STOP_REVIEW_TIMEOUT_MS,
      input: prompt,
    },
  );

  if (result.error?.code === "ETIMEDOUT") {
    return { ok: true, reason: null };
  }

  if (result.status !== 0) {
    const detail = String(result.stderr || result.stdout || "").trim();
    logNote(
      detail
        ? `Stop-time review failed: ${detail}`
        : "Stop-time review failed.",
    );
    return { ok: true, reason: null };
  }

  return parseStopReviewOutput(result.stdout);
}

function main() {
  const input = readHookInput();
  const cwd =
    input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const config = getConfig();

  if (!config.stopReviewGate) {
    return;
  }

  if (!isDroidAvailable()) {
    logNote(
      "droid is not available for the stop review gate. Run /do:setup to check.",
    );
    return;
  }

  const review = runStopReview(cwd, input);
  if (!review.ok) {
    emitDecision({
      decision: "block",
      reason: review.reason,
    });
  }
}

try {
  main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  // Fail open — don't set exitCode so the stop is not blocked
}
