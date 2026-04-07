/**
 * Unit tests for resolveCwd: tool param wins over process.cwd, relative
 * paths get resolved against process.cwd, undefined/empty fall through.
 */

import { describe, expect, it } from "vitest";
import { resolveCwd } from "./cwd.js";
import { isAbsolute } from "node:path";

describe("resolveCwd", () => {
  it("returns process.cwd() when tool param is undefined", () => {
    expect(resolveCwd(undefined)).toBe(process.cwd());
  });

  it("returns process.cwd() when tool param is the empty string", () => {
    expect(resolveCwd("")).toBe(process.cwd());
  });

  it("returns the tool param as-is when it's already absolute", () => {
    expect(resolveCwd("/Users/serkan/nt-dev")).toBe("/Users/serkan/nt-dev");
  });

  it("preserves a deeply nested absolute path", () => {
    expect(resolveCwd("/a/b/c/d/e/f")).toBe("/a/b/c/d/e/f");
  });

  it("resolves a relative path against process.cwd()", () => {
    const result = resolveCwd("subdir");
    expect(isAbsolute(result)).toBe(true);
    expect(result.endsWith("/subdir")).toBe(true);
    expect(result.startsWith(process.cwd())).toBe(true);
  });

  it("resolves a relative path with .. segments", () => {
    const result = resolveCwd("../sibling");
    expect(isAbsolute(result)).toBe(true);
    // Sanity: doesn't contain ".." in the resolved form.
    expect(result.includes("..")).toBe(false);
  });

  it("resolves '.' to process.cwd()", () => {
    expect(resolveCwd(".")).toBe(process.cwd());
  });
});
