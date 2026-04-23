import { describe, expect, it } from "vitest";
import {
  buildDiscussBody,
  parseDiscussJson,
  stripDiscussJsonBlock,
} from "./discuss.js";

describe("parseDiscussJson", () => {
  it("extracts a well-formed JSON block", () => {
    const text = `Some prose.

<discuss-json>
{"objective":"x","risks":["r1","r2"],"blockers":[],"alternatives":["a1"],"missing":[],"verdict":"proceed"}
</discuss-json>`;
    const parsed = parseDiscussJson(text);
    expect(parsed.objective).toBe("x");
    expect(parsed.risks).toEqual(["r1", "r2"]);
    expect(parsed.blockers).toEqual([]);
    expect(parsed.alternatives).toEqual(["a1"]);
    expect(parsed.verdict).toBe("proceed");
  });

  it("returns empty arrays when no JSON block present", () => {
    const parsed = parseDiscussJson("no json here");
    expect(parsed.risks).toEqual([]);
    expect(parsed.verdict).toBeUndefined();
  });

  it("rejects invalid verdict values", () => {
    const text = `<discuss-json>{"verdict":"maybe","risks":[],"blockers":[],"alternatives":[],"missing":[]}</discuss-json>`;
    expect(parseDiscussJson(text).verdict).toBeUndefined();
  });

  it("filters non-string array entries defensively", () => {
    const text = `<discuss-json>{"risks":["ok", 42, null, "also ok"],"blockers":[],"alternatives":[],"missing":[]}</discuss-json>`;
    expect(parseDiscussJson(text).risks).toEqual(["ok", "also ok"]);
  });

  it("handles malformed JSON gracefully", () => {
    const text = `<discuss-json>{not valid json</discuss-json>`;
    const parsed = parseDiscussJson(text);
    expect(parsed.verdict).toBeUndefined();
    expect(parsed.risks).toEqual([]);
  });
});

describe("buildDiscussBody", () => {
  it("returns the prompt + JSON contract when no scope given", () => {
    const body = buildDiscussBody({ prompt: "Is this plan good?" });
    expect(body).toContain("Is this plan good?");
    expect(body).toContain("<discuss-json>");
    expect(body).not.toContain("git diff");
    expect(body).not.toContain("Before responding, read");
  });

  it("adds a file-reading instruction when paths given", () => {
    const body = buildDiscussBody({
      prompt: "thoughts?",
      paths: ["src/auth/middleware.ts"],
    });
    expect(body).toContain("Before responding, read the following file(s)");
    expect(body).toContain("- src/auth/middleware.ts");
    expect(body).not.toContain("git diff");
  });

  it("adds a git-diff instruction when base_ref given", () => {
    const body = buildDiscussBody({
      prompt: "is this diff safe?",
      base_ref: "main",
    });
    expect(body).toContain("git diff main...HEAD");
    expect(body).not.toContain("Before responding, read the following");
  });

  it("combines base_ref + paths into a scoped diff command", () => {
    const body = buildDiscussBody({
      prompt: "critique?",
      base_ref: "main",
      paths: ["src/auth/"],
    });
    expect(body).toContain(`git diff main...HEAD -- "src/auth/"`);
  });

  it("always appends the JSON contract", () => {
    const body = buildDiscussBody({ prompt: "hi" });
    expect(body).toMatch(/<discuss-json>[\s\S]+<\/discuss-json>/);
  });
});

describe("stripDiscussJsonBlock", () => {
  it("removes the JSON block from output", () => {
    const text = `Visible text.

<discuss-json>
{"risks":[]}
</discuss-json>`;
    expect(stripDiscussJsonBlock(text)).toBe("Visible text.");
  });

  it("leaves text unchanged when no block present", () => {
    expect(stripDiscussJsonBlock("just text")).toBe("just text");
  });
});
