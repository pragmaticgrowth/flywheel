/**
 * Minimal config state management for mcp-do hook scripts.
 * Reads/writes a small JSON config file for plugin-wide settings
 * like the stop review gate toggle.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";

const PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA";
const FALLBACK_CONFIG_DIR = path.join(os.homedir(), ".config", "mcp-do");
const STATE_FILE_NAME = "state.json";

function defaultState() {
  return {
    config: {
      stopReviewGate: false,
    },
  };
}

function resolveStateDir() {
  const pluginDataDir = process.env[PLUGIN_DATA_ENV];
  if (pluginDataDir) {
    return path.join(pluginDataDir, "state");
  }
  return FALLBACK_CONFIG_DIR;
}

function resolveStateFile() {
  return path.join(resolveStateDir(), STATE_FILE_NAME);
}

function ensureStateDir() {
  fs.mkdirSync(resolveStateDir(), { recursive: true });
}

export function loadState() {
  const stateFile = resolveStateFile();
  try {
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    const defaults = defaultState();
    return {
      ...defaults,
      ...parsed,
      config: {
        ...defaults.config,
        ...(parsed.config ?? {}),
      },
    };
  } catch {
    return defaultState();
  }
}

export function saveState(state) {
  ensureStateDir();
  const stateFile = resolveStateFile();
  fs.writeFileSync(
    stateFile,
    `${JSON.stringify(state, null, 2)}\n`,
    "utf8",
  );
}

export function getConfig() {
  return loadState().config;
}

export function setConfig(key, value) {
  const state = loadState();
  state.config = {
    ...state.config,
    [key]: value,
  };
  saveState(state);
  return state.config;
}
