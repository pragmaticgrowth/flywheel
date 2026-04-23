import { describe, expect, it } from "vitest";
import { buildAuditBody, parseAuditJson, stripAuditJsonBlock } from "./audit.js";

describe("parseAuditJson", () => {
  it("extracts a full audit JSON block", () => {
    const text = `## Verdict
blockers

<audit-json>
{"verdict":"blockers","blockers":["b1","b2"],"concerns":["c1"],"missed_requirements":["m1"],"strengths":["s1"],"next_steps":["n1","n2"]}
</audit-json>`;
    const parsed = parseAuditJson(text);
    expect(parsed.verdict).toBe("blockers");
    expect(parsed.blockers).toEqual(["b1", "b2"]);
    expect(parsed.concerns).toEqual(["c1"]);
    expect(parsed.missed_requirements).toEqual(["m1"]);
    expect(parsed.strengths).toEqual(["s1"]);
    expect(parsed.next_steps).toEqual(["n1", "n2"]);
  });

  it("returns empty arrays and undefined verdict when block missing", () => {
    const parsed = parseAuditJson("no block here");
    expect(parsed.verdict).toBeUndefined();
    expect(parsed.blockers).toEqual([]);
    expect(parsed.concerns).toEqual([]);
    expect(parsed.missed_requirements).toEqual([]);
    expect(parsed.strengths).toEqual([]);
    expect(parsed.next_steps).toEqual([]);
  });

  it("rejects unknown verdict values", () => {
    const text = `<audit-json>{"verdict":"ship-it","blockers":[],"concerns":[],"missed_requirements":[],"strengths":[],"next_steps":[]}</audit-json>`;
    expect(parseAuditJson(text).verdict).toBeUndefined();
  });

  it("accepts all three valid verdict values", () => {
    for (const v of ["pass", "concerns", "blockers"] as const) {
      const text = `<audit-json>{"verdict":"${v}","blockers":[],"concerns":[],"missed_requirements":[],"strengths":[],"next_steps":[]}</audit-json>`;
      expect(parseAuditJson(text).verdict).toBe(v);
    }
  });

  it("filters non-string array entries", () => {
    const text = `<audit-json>{"verdict":"pass","blockers":[1,"ok",null],"concerns":[],"missed_requirements":[],"strengths":[],"next_steps":[]}</audit-json>`;
    expect(parseAuditJson(text).blockers).toEqual(["ok"]);
  });

  it("handles malformed JSON without throwing", () => {
    const text = `<audit-json>{not valid</audit-json>`;
    const parsed = parseAuditJson(text);
    expect(parsed.verdict).toBeUndefined();
    expect(parsed.blockers).toEqual([]);
  });
});

describe("buildAuditBody", () => {
  it("accepts an inline diff", () => {
    const body = buildAuditBody({ context: "spec", diff: "+const x = 1;" });
    expect(body).toContain("# Context");
    expect(body).toContain("spec");
    expect(body).toContain("Inline diff / delivered work:");
    expect(body).toContain("+const x = 1;");
    expect(body).toContain("<audit-json>");
  });

  it("accepts paths only (Codex reads files itself)", () => {
    const body = buildAuditBody({
      context: "spec",
      paths: ["src/auth/middleware.ts", "src/auth/cache.ts"],
    });
    expect(body).toContain("Read the following file(s) or directories");
    expect(body).toContain("- src/auth/middleware.ts");
    expect(body).toContain("- src/auth/cache.ts");
    expect(body).not.toContain("git diff");
  });

  it("accepts base_ref only", () => {
    const body = buildAuditBody({ context: "spec", base_ref: "main" });
    expect(body).toContain("git diff main...HEAD");
    expect(body).not.toContain("--"); // no pathspec when no paths
  });

  it("combines base_ref + paths into a scoped git diff", () => {
    const body = buildAuditBody({
      context: "spec",
      base_ref: "main",
      paths: ["src/auth/", "tests/"],
    });
    expect(body).toContain(`git diff main...HEAD -- "src/auth/" "tests/"`);
  });

  it("combines inline diff with paths", () => {
    const body = buildAuditBody({
      context: "spec",
      diff: "inline snippet",
      paths: ["src/foo.ts"],
    });
    expect(body).toContain("- src/foo.ts");
    expect(body).toContain("Inline diff");
    expect(body).toContain("inline snippet");
  });

  it("throws when no scope provided", () => {
    expect(() => buildAuditBody({ context: "spec" })).toThrow(
      /needs at least one of/,
    );
  });

  it("throws when all scopes empty", () => {
    expect(() =>
      buildAuditBody({ context: "spec", diff: "   ", paths: [] }),
    ).toThrow(/needs at least one of/);
  });
});

describe("stripAuditJsonBlock", () => {
  it("removes the JSON block", () => {
    const text = `## Verdict\npass\n\n<audit-json>{"verdict":"pass","blockers":[],"concerns":[],"missed_requirements":[],"strengths":[],"next_steps":[]}</audit-json>`;
    const stripped = stripAuditJsonBlock(text);
    expect(stripped).toContain("## Verdict");
    expect(stripped).not.toContain("<audit-json>");
    expect(stripped).not.toContain("</audit-json>");
  });
});
