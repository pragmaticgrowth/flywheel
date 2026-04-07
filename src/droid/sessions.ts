/**
 * Read the droid sessions index at `~/.factory/sessions-index.json`.
 *
 * Verified shape (planning session, 142 entries in the live file):
 *   { version: 1, entries: SessionEntry[] }
 *
 * The entry `cwd` field is the RAW absolute path — no encoding needed for
 * cwd filtering. `mtime` is unix milliseconds.
 */

import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export interface SessionEntry {
  session_id: string;
  mtime: number;
  settings_mtime?: number;
  title: string;
  cwd: string;
  messages_count: number;
}

interface RawSessionIndexEntry {
  sessionId: string;
  mtime: number;
  settingsMtime?: number;
  title?: string;
  cwd?: string;
  messagesCount?: number;
}

interface RawSessionIndex {
  version?: number;
  entries?: RawSessionIndexEntry[];
}

function normalize(raw: RawSessionIndexEntry): SessionEntry {
  return {
    session_id: raw.sessionId,
    mtime: raw.mtime,
    settings_mtime: raw.settingsMtime,
    title: raw.title ?? "New Session",
    cwd: raw.cwd ?? "",
    messages_count: raw.messagesCount ?? 0,
  };
}

export interface ListSessionsOptions {
  cwd?: string;
  all?: boolean;
  limit?: number;
  search?: string;
  index_path?: string; // override for tests
}

export async function listSessions(
  opts: ListSessionsOptions = {},
): Promise<SessionEntry[]> {
  const indexPath =
    opts.index_path ?? join(homedir(), ".factory", "sessions-index.json");

  let raw: string;
  try {
    raw = await readFile(indexPath, "utf8");
  } catch {
    return [];
  }

  let parsed: RawSessionIndex;
  try {
    parsed = JSON.parse(raw) as RawSessionIndex;
  } catch {
    return [];
  }

  const all = (parsed.entries ?? []).map(normalize);

  let filtered = all;
  if (!opts.all && opts.cwd !== undefined) {
    filtered = filtered.filter((e) => e.cwd === opts.cwd);
  }
  if (opts.search !== undefined && opts.search !== "") {
    const needle = opts.search.toLowerCase();
    filtered = filtered.filter((e) => e.title.toLowerCase().includes(needle));
  }

  filtered.sort((a, b) => b.mtime - a.mtime);

  const limit = opts.limit ?? 50;
  return filtered.slice(0, limit);
}
