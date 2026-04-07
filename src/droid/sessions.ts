/**
 * Read the droid sessions index at `~/.factory/sessions-index.json`.
 *
 * Verified shape (planning session, 142 entries in the live file):
 *   { version: 1, entries: SessionEntry[] }
 *
 * The entry `cwd` field is the RAW absolute path — no encoding needed for
 * cwd filtering. `mtime` is unix milliseconds.
 *
 * IMPORTANT: sessions-index.json is INCOMPLETE. Verified: droid skips
 * sessions created via `droid exec` (the automation path mcp-droid itself
 * uses), so the index misses many real on-disk sessions — including every
 * session under ~/.factory/sessions/-Users-serkan-mcp-droid/. The
 * authoritative cwd lives inside each session's .jsonl file as the `cwd`
 * field on the first `session_start` event. Use `readSessionMetaFromJsonl`
 * to extract it when you need ground truth for search results.
 */

import { createReadStream } from "node:fs";
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";

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

/**
 * Authoritative metadata for a session, read directly from its .jsonl file.
 * Every session starts with a `{"type":"session_start", "cwd": "...", ...}`
 * line. This is the ground-truth source for cwd — unlike sessions-index.json
 * which is incomplete (see header comment).
 */
export interface SessionMetaFromJsonl {
  session_id?: string;
  cwd?: string;
  title?: string;
  owner?: string;
}

/**
 * Read only the first non-empty line of a session .jsonl and parse the
 * `session_start` event. Uses a streaming readline so we don't slurp a
 * multi-megabyte session file into memory just to grab ~200 bytes at the
 * top. Returns `undefined` fields if the file is missing, malformed, or
 * doesn't begin with a session_start event.
 */
export async function readSessionMetaFromJsonl(
  jsonlPath: string,
): Promise<SessionMetaFromJsonl> {
  return new Promise<SessionMetaFromJsonl>((resolve) => {
    const stream = createReadStream(jsonlPath, { encoding: "utf8" });
    const rl = createInterface({ input: stream, crlfDelay: Infinity });
    let resolved = false;

    const done = (meta: SessionMetaFromJsonl): void => {
      if (resolved) return;
      resolved = true;
      rl.close();
      stream.destroy();
      resolve(meta);
    };

    rl.on("line", (line: string) => {
      if (line.trim() === "") return;
      try {
        const parsed = JSON.parse(line) as {
          type?: unknown;
          id?: unknown;
          cwd?: unknown;
          title?: unknown;
          sessionTitle?: unknown;
          owner?: unknown;
        };
        if (parsed.type !== "session_start") {
          // First non-empty line wasn't a session_start — bail early.
          // We don't walk further; this shape is the documented contract.
          done({});
          return;
        }
        done({
          session_id: typeof parsed.id === "string" ? parsed.id : undefined,
          cwd: typeof parsed.cwd === "string" ? parsed.cwd : undefined,
          title:
            typeof parsed.title === "string"
              ? parsed.title
              : typeof parsed.sessionTitle === "string"
                ? parsed.sessionTitle
                : undefined,
          owner: typeof parsed.owner === "string" ? parsed.owner : undefined,
        });
      } catch {
        done({});
      }
    });

    rl.on("error", () => done({}));
    rl.on("close", () => done({}));
    stream.on("error", () => done({}));
  });
}
