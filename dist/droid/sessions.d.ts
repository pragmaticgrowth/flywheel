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
export interface SessionEntry {
    session_id: string;
    mtime: number;
    settings_mtime?: number;
    title: string;
    cwd: string;
    messages_count: number;
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
    index_path?: string;
    sessions_dir?: string;
}
export declare function listSessions(opts?: ListSessionsOptions): Promise<SessionEntry[]>;
/**
 * Encode an absolute cwd into the directory name droid uses on disk:
 *   /Users/serkan/nt-dev → -Users-serkan-nt-dev
 * The encoding is one-way and lossy in theory (a literal `-` in a path
 * segment is indistinguishable from a `/`), so callers should still verify
 * the returned sessions' cwd field against the exact target.
 */
export declare function encodeCwdToSessionsDir(absCwd: string): string;
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
export declare function readSessionMetaFromJsonl(jsonlPath: string): Promise<SessionMetaFromJsonl>;
