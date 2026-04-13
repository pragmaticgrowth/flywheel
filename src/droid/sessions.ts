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
 * sessions created via `droid exec` (the automation path mcp-do itself
 * uses), so the index misses many real on-disk sessions — including every
 * session under ~/.factory/sessions/-Users-serkan-mcp-do/. The
 * authoritative cwd lives inside each session's .jsonl file as the `cwd`
 * field on the first `session_start` event. Use `readSessionMetaFromJsonl`
 * to extract it when you need ground truth for search results.
 */

import { createReadStream } from "node:fs";
import { readdir, readFile, stat } from "node:fs/promises";
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
  /**
   * When true, walk ~/.factory/sessions/<dir>/*.jsonl and read each
   * file's first line for authoritative cwd/title. Slower (one stat +
   * one streaming read per session, parallelized), but COMPLETE — picks
   * up sessions that droid's own indexer skips (e.g. anything created
   * via `droid exec` from automation, including mcp-do itself).
   * Default: false (use sessions-index.json only, fast but incomplete).
   */
  scan_disk?: boolean;
  index_path?: string; // override for tests
  sessions_dir?: string; // override for tests
}

export async function listSessions(
  opts: ListSessionsOptions = {},
): Promise<SessionEntry[]> {
  // When scan_disk is on AND a cwd filter applies, narrow the disk walk
  // to just the one encoded directory. The encoding /Users/serkan/nt-dev →
  // -Users-serkan-nt-dev is one-way deterministic, so we can compute the
  // target dir up front. Cuts I/O ~85% in the typical filtered case (one
  // dir of ~100 files instead of 7 dirs of ~200 files).
  const narrowToCwd = opts.scan_disk && !opts.all && opts.cwd !== undefined
    ? opts.cwd
    : undefined;

  const collected: SessionEntry[] = opts.scan_disk
    ? await listSessionsFromDisk(opts.sessions_dir, narrowToCwd)
    : await listSessionsFromIndex(
        opts.index_path ?? join(homedir(), ".factory", "sessions-index.json"),
      );

  let filtered = collected;
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
 * Encode an absolute cwd into the directory name droid uses on disk:
 *   /Users/serkan/nt-dev → -Users-serkan-nt-dev
 * The encoding is one-way and lossy in theory (a literal `-` in a path
 * segment is indistinguishable from a `/`), so callers should still verify
 * the returned sessions' cwd field against the exact target.
 */
export function encodeCwdToSessionsDir(absCwd: string): string {
  return absCwd.replace(/^\//, "-").replace(/\//g, "-");
}

async function listSessionsFromIndex(indexPath: string): Promise<SessionEntry[]> {
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
  return (parsed.entries ?? []).map(normalize);
}

/**
 * Walk session directories under ~/.factory/sessions/, list their .jsonl
 * files, and read each file's first session_start line to get the
 * authoritative cwd + title. Mtime comes from `stat`. All file reads run
 * in parallel.
 *
 * Cost: O(N) file opens where N is total session count. ~200 sessions on
 * a typical machine = roughly 200-400ms. Acceptable for an opt-in path
 * that callers explicitly request.
 *
 * If `narrowToCwd` is provided, only walks the single encoded directory
 * for that cwd (e.g. /Users/serkan/nt-dev → -Users-serkan-nt-dev). This
 * cuts I/O ~85% in the typical filtered case.
 */
async function listSessionsFromDisk(
  sessionsDir?: string,
  narrowToCwd?: string,
): Promise<SessionEntry[]> {
  const root = sessionsDir ?? join(homedir(), ".factory", "sessions");
  let dirs: string[];
  if (narrowToCwd !== undefined) {
    // Skip the readdir entirely — go straight to the one encoded dir.
    // If it doesn't exist on disk, the inner stat() will fall through
    // to an empty result and the function returns [].
    dirs = [encodeCwdToSessionsDir(narrowToCwd)];
  } else {
    try {
      dirs = await readdir(root);
    } catch {
      return [];
    }
  }

  const allFiles: Array<{ jsonlPath: string }> = [];
  await Promise.all(
    dirs.map(async (dir) => {
      const dirPath = join(root, dir);
      try {
        const st = await stat(dirPath);
        if (!st.isDirectory()) return;
      } catch {
        return;
      }
      let entries: string[] = [];
      try {
        entries = await readdir(dirPath);
      } catch {
        return;
      }
      for (const entry of entries) {
        if (entry.endsWith(".jsonl")) {
          allFiles.push({ jsonlPath: join(dirPath, entry) });
        }
      }
    }),
  );

  const sessions = await Promise.all(
    allFiles.map(async ({ jsonlPath }): Promise<SessionEntry | null> => {
      const [meta, st] = await Promise.all([
        readSessionMetaFromJsonl(jsonlPath),
        stat(jsonlPath).catch(() => null),
      ]);
      if (!meta.session_id) return null;
      return {
        session_id: meta.session_id,
        mtime: st ? st.mtimeMs : 0,
        title: meta.title ?? "New Session",
        cwd: meta.cwd ?? "",
        messages_count: 0, // not available without parsing the whole file
      };
    }),
  );

  return sessions.filter((s): s is SessionEntry => s !== null);
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
