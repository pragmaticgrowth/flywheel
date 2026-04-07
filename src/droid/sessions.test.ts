/**
 * Unit tests for the sessions module: index reading, on-disk walk,
 * jsonl first-line parsing, cwd encoding.
 *
 * Uses temp directories so we don't depend on the real ~/.factory/.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  encodeCwdToSessionsDir,
  listSessions,
  readSessionMetaFromJsonl,
} from "./sessions.js";

let tmpRoot: string;
let tmpIndex: string;
let tmpSessionsDir: string;

beforeEach(async () => {
  tmpRoot = await mkdtemp(join(tmpdir(), "mcp-droid-sessions-test-"));
  tmpIndex = join(tmpRoot, "sessions-index.json");
  tmpSessionsDir = join(tmpRoot, "sessions");
  await mkdir(tmpSessionsDir, { recursive: true });
});

afterEach(async () => {
  await rm(tmpRoot, { recursive: true, force: true });
});

async function writeIndex(
  entries: Array<{
    sessionId: string;
    mtime: number;
    title?: string;
    cwd?: string;
    messagesCount?: number;
  }>,
): Promise<void> {
  await writeFile(
    tmpIndex,
    JSON.stringify({ version: 1, entries }),
  );
}

async function writeSessionFile(
  encodedDir: string,
  sessionId: string,
  meta: { cwd?: string; title?: string; owner?: string } = {},
): Promise<string> {
  const dir = join(tmpSessionsDir, encodedDir);
  await mkdir(dir, { recursive: true });
  const path = join(dir, `${sessionId}.jsonl`);
  const sessionStart = {
    type: "session_start",
    id: sessionId,
    cwd: meta.cwd,
    title: meta.title,
    owner: meta.owner,
    version: 2,
  };
  const lines = [
    JSON.stringify(sessionStart),
    JSON.stringify({ type: "message", role: "user", text: "hello" }),
  ];
  await writeFile(path, lines.join("\n"));
  return path;
}

describe("encodeCwdToSessionsDir", () => {
  it("encodes a leading slash and inner slashes as dashes", () => {
    expect(encodeCwdToSessionsDir("/Users/serkan/nt-dev")).toBe(
      "-Users-serkan-nt-dev",
    );
  });

  it("encodes a single-segment path", () => {
    expect(encodeCwdToSessionsDir("/Users")).toBe("-Users");
  });

  it("preserves dashes within segments (lossy but deterministic)", () => {
    // /Users/serkan/mcp-droid → -Users-serkan-mcp-droid
    // (the dash in "mcp-droid" is preserved as-is)
    expect(encodeCwdToSessionsDir("/Users/serkan/mcp-droid")).toBe(
      "-Users-serkan-mcp-droid",
    );
  });
});

describe("listSessions — index path (default)", () => {
  it("returns an empty array when the index file does not exist", async () => {
    const result = await listSessions({ index_path: join(tmpRoot, "missing.json") });
    expect(result).toEqual([]);
  });

  it("returns an empty array when the index is malformed JSON", async () => {
    await writeFile(tmpIndex, "not json {{");
    const result = await listSessions({ index_path: tmpIndex });
    expect(result).toEqual([]);
  });

  it("normalizes raw entries (snake_case + defaults)", async () => {
    await writeIndex([
      {
        sessionId: "s1",
        mtime: 100,
        title: "First",
        cwd: "/Users/serkan/nt-dev",
        messagesCount: 5,
      },
    ]);
    const result = await listSessions({ index_path: tmpIndex, all: true });
    expect(result[0]).toEqual({
      session_id: "s1",
      mtime: 100,
      settings_mtime: undefined,
      title: "First",
      cwd: "/Users/serkan/nt-dev",
      messages_count: 5,
    });
  });

  it("filters by exact cwd when not all=true", async () => {
    await writeIndex([
      { sessionId: "s1", mtime: 100, cwd: "/Users/serkan/nt-dev" },
      { sessionId: "s2", mtime: 200, cwd: "/Users/serkan/hetzner" },
    ]);
    const result = await listSessions({
      index_path: tmpIndex,
      cwd: "/Users/serkan/nt-dev",
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe("s1");
  });

  it("returns all sessions when all=true", async () => {
    await writeIndex([
      { sessionId: "s1", mtime: 100, cwd: "/x" },
      { sessionId: "s2", mtime: 200, cwd: "/y" },
    ]);
    const result = await listSessions({ index_path: tmpIndex, all: true });
    expect(result).toHaveLength(2);
  });

  it("filters by case-insensitive title substring", async () => {
    await writeIndex([
      { sessionId: "s1", mtime: 100, title: "Refactor auth", cwd: "/x" },
      { sessionId: "s2", mtime: 200, title: "Document API", cwd: "/x" },
      { sessionId: "s3", mtime: 300, title: "REFACTOR DB", cwd: "/x" },
    ]);
    const result = await listSessions({
      index_path: tmpIndex,
      all: true,
      search: "refactor",
    });
    expect(result.map((s) => s.session_id)).toEqual(["s3", "s1"]);
  });

  it("sorts by mtime descending", async () => {
    await writeIndex([
      { sessionId: "old", mtime: 100, cwd: "/x" },
      { sessionId: "new", mtime: 999, cwd: "/x" },
      { sessionId: "mid", mtime: 500, cwd: "/x" },
    ]);
    const result = await listSessions({ index_path: tmpIndex, all: true });
    expect(result.map((s) => s.session_id)).toEqual(["new", "mid", "old"]);
  });

  it("respects the limit option", async () => {
    await writeIndex([
      { sessionId: "s1", mtime: 100, cwd: "/x" },
      { sessionId: "s2", mtime: 200, cwd: "/x" },
      { sessionId: "s3", mtime: 300, cwd: "/x" },
    ]);
    const result = await listSessions({
      index_path: tmpIndex,
      all: true,
      limit: 2,
    });
    expect(result).toHaveLength(2);
  });

  it("returns empty title default when raw title is missing", async () => {
    await writeIndex([{ sessionId: "s1", mtime: 100 }]);
    const result = await listSessions({ index_path: tmpIndex, all: true });
    expect(result[0]?.title).toBe("New Session");
  });
});

describe("listSessions — disk walk path (scan_disk=true)", () => {
  it("returns an empty array when the sessions root does not exist", async () => {
    const result = await listSessions({
      sessions_dir: join(tmpRoot, "nope"),
      scan_disk: true,
      all: true,
    });
    expect(result).toEqual([]);
  });

  it("walks every encoded directory when no cwd filter is given", async () => {
    await writeSessionFile("-Users-serkan", "s1", {
      cwd: "/Users/serkan",
      title: "A",
    });
    await writeSessionFile("-Users-serkan-nt-dev", "s2", {
      cwd: "/Users/serkan/nt-dev",
      title: "B",
    });
    await writeSessionFile("-Users-serkan-mcp-droid", "s3", {
      cwd: "/Users/serkan/mcp-droid",
      title: "C",
    });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      all: true,
    });
    expect(result).toHaveLength(3);
    expect(new Set(result.map((s) => s.cwd))).toEqual(
      new Set([
        "/Users/serkan",
        "/Users/serkan/nt-dev",
        "/Users/serkan/mcp-droid",
      ]),
    );
  });

  it("narrows the walk to one directory when cwd is provided and !all", async () => {
    await writeSessionFile("-Users-serkan", "s1", { cwd: "/Users/serkan" });
    await writeSessionFile("-Users-serkan-nt-dev", "s2", {
      cwd: "/Users/serkan/nt-dev",
    });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      cwd: "/Users/serkan/nt-dev",
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe("s2");
    expect(result[0]?.cwd).toBe("/Users/serkan/nt-dev");
  });

  it("returns empty when narrowed cwd encodes to a non-existent directory", async () => {
    await writeSessionFile("-Users-serkan", "s1", { cwd: "/Users/serkan" });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      cwd: "/Users/serkan/never-existed",
    });
    expect(result).toEqual([]);
  });

  it("skips files (not directories) and directories without .jsonl files", async () => {
    await writeFile(join(tmpSessionsDir, "stray.txt"), "not a dir");
    await mkdir(join(tmpSessionsDir, "empty-dir"));
    await writeSessionFile("-Users-serkan", "s1", { cwd: "/Users/serkan" });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      all: true,
    });
    expect(result).toHaveLength(1);
  });

  it("skips .jsonl files whose first line isn't a session_start event", async () => {
    const dir = join(tmpSessionsDir, "-Users-serkan");
    await mkdir(dir, { recursive: true });
    await writeFile(
      join(dir, "broken.jsonl"),
      JSON.stringify({ type: "message", text: "no session_start here" }),
    );
    await writeSessionFile("-Users-serkan", "ok", { cwd: "/Users/serkan" });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      all: true,
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe("ok");
  });

  it("uses file mtime for the SessionEntry mtime", async () => {
    const path = await writeSessionFile("-Users-serkan", "s1", {
      cwd: "/Users/serkan",
    });
    const result = await listSessions({
      sessions_dir: tmpSessionsDir,
      scan_disk: true,
      all: true,
    });
    expect(result[0]?.mtime).toBeGreaterThan(0);
    // Sanity: mtime should be roughly "now" (within 60s of test start).
    const ageMs = Date.now() - result[0]!.mtime;
    expect(ageMs).toBeLessThan(60_000);
    // Path is unused beyond writing, but we want the side effect.
    expect(path).toContain("s1.jsonl");
  });
});

describe("readSessionMetaFromJsonl", () => {
  it("returns empty object when the file does not exist", async () => {
    const result = await readSessionMetaFromJsonl(
      join(tmpRoot, "missing.jsonl"),
    );
    expect(result).toEqual({});
  });

  it("extracts session_id, cwd, title, owner from a valid first line", async () => {
    const path = await writeSessionFile("-x", "session-uuid", {
      cwd: "/Users/serkan",
      title: "Hello",
      owner: "serkan",
    });
    const result = await readSessionMetaFromJsonl(path);
    expect(result.session_id).toBe("session-uuid");
    expect(result.cwd).toBe("/Users/serkan");
    expect(result.title).toBe("Hello");
    expect(result.owner).toBe("serkan");
  });

  it("falls back to sessionTitle when title is missing", async () => {
    const dir = join(tmpSessionsDir, "-x");
    await mkdir(dir, { recursive: true });
    const path = join(dir, "s1.jsonl");
    await writeFile(
      path,
      JSON.stringify({
        type: "session_start",
        id: "s1",
        sessionTitle: "From sessionTitle",
        cwd: "/x",
      }),
    );
    const result = await readSessionMetaFromJsonl(path);
    expect(result.title).toBe("From sessionTitle");
  });

  it("returns empty object when first non-blank line isn't session_start", async () => {
    const dir = join(tmpSessionsDir, "-x");
    await mkdir(dir, { recursive: true });
    const path = join(dir, "s1.jsonl");
    await writeFile(
      path,
      JSON.stringify({ type: "message", text: "wrong shape" }),
    );
    const result = await readSessionMetaFromJsonl(path);
    expect(result).toEqual({});
  });

  it("returns empty object when first line is invalid JSON", async () => {
    const dir = join(tmpSessionsDir, "-x");
    await mkdir(dir, { recursive: true });
    const path = join(dir, "s1.jsonl");
    await writeFile(path, "not valid json {{ \n");
    const result = await readSessionMetaFromJsonl(path);
    expect(result).toEqual({});
  });

  it("skips leading blank lines and finds the session_start", async () => {
    const dir = join(tmpSessionsDir, "-x");
    await mkdir(dir, { recursive: true });
    const path = join(dir, "s1.jsonl");
    await writeFile(
      path,
      "\n\n" +
        JSON.stringify({ type: "session_start", id: "s1", cwd: "/x" }) +
        "\n",
    );
    const result = await readSessionMetaFromJsonl(path);
    expect(result.session_id).toBe("s1");
  });
});
