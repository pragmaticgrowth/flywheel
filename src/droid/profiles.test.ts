/**
 * Unit tests for the profiles module: front-matter parser + profile
 * directory walking with project-shadows-global semantics.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { listProfiles, parseFrontMatter } from "./profiles.js";

let tmpRoot: string;

beforeEach(async () => {
  tmpRoot = await mkdtemp(join(tmpdir(), "mcp-droid-profiles-test-"));
});

afterEach(async () => {
  await rm(tmpRoot, { recursive: true, force: true });
});

async function writeProfile(
  dir: string,
  fileName: string,
  frontMatter: Record<string, string | string[]>,
  body = "# Profile body",
): Promise<void> {
  await mkdir(dir, { recursive: true });
  const fmLines = Object.entries(frontMatter).map(([k, v]) => {
    if (Array.isArray(v)) return `${k}: ${JSON.stringify(v)}`;
    return `${k}: "${v}"`;
  });
  const content = `---\n${fmLines.join("\n")}\n---\n\n${body}\n`;
  await writeFile(join(dir, fileName), content);
}

describe("parseFrontMatter", () => {
  it("returns empty data and the original body when there's no front-matter block", () => {
    const result = parseFrontMatter("# Just a heading\n\nbody");
    expect(result.data).toEqual({});
    expect(result.body).toBe("# Just a heading\n\nbody");
  });

  it("parses scalar values", () => {
    const result = parseFrontMatter(
      `---\nname: hello\nmodel: inherit\n---\n\nbody\n`,
    );
    expect(result.data).toEqual({ name: "hello", model: "inherit" });
    expect(result.body).toBe("body\n");
  });

  it("strips double-quoted values", () => {
    const result = parseFrontMatter(
      `---\ndescription: "a long quoted description"\n---\n\nbody\n`,
    );
    expect(result.data.description).toBe("a long quoted description");
  });

  it("strips single-quoted values", () => {
    const result = parseFrontMatter(
      `---\nname: 'single quoted'\n---\n\nbody\n`,
    );
    expect(result.data.name).toBe("single quoted");
  });

  it("parses single-line JSON arrays", () => {
    const result = parseFrontMatter(
      `---\ntools: ["Read", "Grep", "Glob"]\n---\n\nbody\n`,
    );
    expect(result.data.tools).toEqual(["Read", "Grep", "Glob"]);
  });

  it("falls back to string when JSON array is malformed", () => {
    const result = parseFrontMatter(
      `---\ntools: [Read, no quotes]\n---\n\nbody\n`,
    );
    expect(result.data.tools).toBe("[Read, no quotes]");
  });

  it("ignores blank lines and # comments inside front-matter", () => {
    const result = parseFrontMatter(
      `---\n# this is a comment\nname: hello\n\nmodel: inherit\n---\n\nbody\n`,
    );
    expect(result.data).toEqual({ name: "hello", model: "inherit" });
  });

  it("ignores lines without a colon", () => {
    const result = parseFrontMatter(
      `---\nname: hello\nthis-is-not-a-key-value\n---\n\nbody\n`,
    );
    expect(result.data).toEqual({ name: "hello" });
  });
});

describe("listProfiles", () => {
  it("returns an empty array when neither global nor project dirs exist", async () => {
    const result = await listProfiles({
      global_dir: join(tmpRoot, "no-global"),
      cwd: join(tmpRoot, "no-cwd"),
    });
    expect(result).toEqual([]);
  });

  it("loads profiles from the global dir only when no cwd given", async () => {
    const globalDir = join(tmpRoot, "global");
    await writeProfile(globalDir, "researcher.md", {
      name: "deep-researcher",
      description: "research stuff",
      model: "inherit",
      tools: ["Read", "Grep"],
    });
    const result = await listProfiles({ global_dir: globalDir });
    expect(result).toHaveLength(1);
    expect(result[0]?.name).toBe("deep-researcher");
    expect(result[0]?.scope).toBe("global");
    expect(result[0]?.description).toBe("research stuff");
    expect(result[0]?.model).toBe("inherit");
    expect(result[0]?.tools).toEqual(["Read", "Grep"]);
  });

  it("loads project profiles from <cwd>/.factory/droids/", async () => {
    const globalDir = join(tmpRoot, "global");
    await mkdir(globalDir, { recursive: true });
    const projectDir = join(tmpRoot, "project");
    await writeProfile(join(projectDir, ".factory", "droids"), "local.md", {
      name: "local-thing",
      description: "project-only",
    });
    const result = await listProfiles({
      global_dir: globalDir,
      cwd: projectDir,
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.scope).toBe("project");
    expect(result[0]?.name).toBe("local-thing");
  });

  it("project profiles SHADOW global profiles with the same name", async () => {
    const globalDir = join(tmpRoot, "global");
    const projectDir = join(tmpRoot, "project");
    await writeProfile(globalDir, "researcher.md", {
      name: "deep-researcher",
      description: "global version",
    });
    await writeProfile(
      join(projectDir, ".factory", "droids"),
      "researcher.md",
      {
        name: "deep-researcher",
        description: "project override",
      },
    );
    const result = await listProfiles({
      global_dir: globalDir,
      cwd: projectDir,
    });
    expect(result).toHaveLength(1);
    expect(result[0]?.scope).toBe("project");
    expect(result[0]?.description).toBe("project override");
  });

  it("global and project profiles with different names both appear", async () => {
    const globalDir = join(tmpRoot, "global");
    const projectDir = join(tmpRoot, "project");
    await writeProfile(globalDir, "g.md", { name: "global-only" });
    await writeProfile(join(projectDir, ".factory", "droids"), "p.md", {
      name: "project-only",
    });
    const result = await listProfiles({
      global_dir: globalDir,
      cwd: projectDir,
    });
    expect(result.map((p) => p.name).sort()).toEqual([
      "global-only",
      "project-only",
    ]);
  });

  it("sorts results alphabetically by name", async () => {
    const globalDir = join(tmpRoot, "global");
    await writeProfile(globalDir, "c.md", { name: "charlie" });
    await writeProfile(globalDir, "a.md", { name: "alpha" });
    await writeProfile(globalDir, "b.md", { name: "bravo" });
    const result = await listProfiles({ global_dir: globalDir });
    expect(result.map((p) => p.name)).toEqual(["alpha", "bravo", "charlie"]);
  });

  it("derives the name from the filename when front-matter has no name field", async () => {
    const globalDir = join(tmpRoot, "global");
    await writeProfile(globalDir, "fallback-name.md", {
      description: "no name field",
    });
    const result = await listProfiles({ global_dir: globalDir });
    expect(result[0]?.name).toBe("fallback-name");
  });

  it("ignores non-.md files in the droids dir", async () => {
    const globalDir = join(tmpRoot, "global");
    await mkdir(globalDir, { recursive: true });
    await writeFile(join(globalDir, "README.txt"), "not a profile");
    await writeFile(join(globalDir, ".DS_Store"), "binary");
    await writeProfile(globalDir, "real.md", { name: "real-profile" });
    const result = await listProfiles({ global_dir: globalDir });
    expect(result).toHaveLength(1);
    expect(result[0]?.name).toBe("real-profile");
  });

  it("preserves raw_front_matter on the profile object", async () => {
    const globalDir = join(tmpRoot, "global");
    await writeProfile(globalDir, "x.md", {
      name: "x",
      custom_key: "custom-value",
    });
    const result = await listProfiles({ global_dir: globalDir });
    expect(result[0]?.raw_front_matter?.custom_key).toBe("custom-value");
  });
});
