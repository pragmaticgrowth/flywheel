import { describe, expect, it } from "vitest";
import { buildDroidExecArgs, DroidFlagsError } from "./flags.js";

describe("buildDroidExecArgs", () => {
  describe("trivial cases", () => {
    it("returns an empty array for an empty input", () => {
      expect(buildDroidExecArgs({})).toEqual([]);
    });

    it("appends a bare prompt as the last positional", () => {
      expect(buildDroidExecArgs({ prompt: "hello world" })).toEqual([
        "hello world",
      ]);
    });
  });

  describe("prompt source", () => {
    it("maps prompt_file to --file with no positional", () => {
      expect(buildDroidExecArgs({ prompt_file: "/tmp/p.txt" })).toEqual([
        "--file",
        "/tmp/p.txt",
      ]);
    });

    it("throws if both prompt and prompt_file are set", () => {
      expect(() =>
        buildDroidExecArgs({ prompt: "hi", prompt_file: "/tmp/p.txt" }),
      ).toThrow(DroidFlagsError);
    });
  });

  describe("model + reasoning", () => {
    it("maps model to --model", () => {
      expect(buildDroidExecArgs({ model: "custom:glm-5-turbo" })).toEqual([
        "--model",
        "custom:glm-5-turbo",
      ]);
    });

    it("maps reasoning_effort to --reasoning-effort", () => {
      expect(buildDroidExecArgs({ reasoning_effort: "high" })).toEqual([
        "--reasoning-effort",
        "high",
      ]);
    });
  });

  describe("autonomy", () => {
    it("maps auto: low to --auto low", () => {
      expect(buildDroidExecArgs({ auto: "low" })).toEqual(["--auto", "low"]);
    });

    it("maps allow_unsafe to --skip-permissions-unsafe", () => {
      expect(buildDroidExecArgs({ allow_unsafe: true })).toEqual([
        "--skip-permissions-unsafe",
      ]);
    });

    it("does NOT emit --skip-permissions-unsafe when allow_unsafe is false", () => {
      expect(buildDroidExecArgs({ allow_unsafe: false })).toEqual([]);
    });

    it("throws when auto and allow_unsafe are both set", () => {
      expect(() =>
        buildDroidExecArgs({ auto: "high", allow_unsafe: true }),
      ).toThrow(DroidFlagsError);
    });
  });

  describe("output format", () => {
    it("maps output_format to --output-format", () => {
      expect(buildDroidExecArgs({ output_format: "stream-json" })).toEqual([
        "--output-format",
        "stream-json",
      ]);
    });

    it("maps input_format to --input-format", () => {
      expect(buildDroidExecArgs({ input_format: "stream-json" })).toEqual([
        "--input-format",
        "stream-json",
      ]);
    });
  });

  describe("sessions", () => {
    it("maps session_id to --session-id", () => {
      expect(buildDroidExecArgs({ session_id: "abc-123" })).toEqual([
        "--session-id",
        "abc-123",
      ]);
    });

    it("maps fork_session_id to --fork", () => {
      expect(buildDroidExecArgs({ fork_session_id: "abc-123" })).toEqual([
        "--fork",
        "abc-123",
      ]);
    });
  });

  describe("cwd and worktree", () => {
    it("maps cwd to --cwd", () => {
      expect(buildDroidExecArgs({ cwd: "/Users/serkan/nt-dev" })).toEqual([
        "--cwd",
        "/Users/serkan/nt-dev",
      ]);
    });

    it("maps worktree: true to bare --worktree", () => {
      expect(buildDroidExecArgs({ worktree: true })).toEqual(["--worktree"]);
    });

    it("maps worktree: 'feature-x' to --worktree feature-x", () => {
      expect(buildDroidExecArgs({ worktree: "feature-x" })).toEqual([
        "--worktree",
        "feature-x",
      ]);
    });

    it("does NOT emit --worktree when worktree is false", () => {
      expect(buildDroidExecArgs({ worktree: false })).toEqual([]);
    });

    it("maps worktree_dir to --worktree-dir", () => {
      expect(buildDroidExecArgs({ worktree_dir: "/tmp/wt" })).toEqual([
        "--worktree-dir",
        "/tmp/wt",
      ]);
    });
  });

  describe("tool controls", () => {
    it("joins enabled_tools with commas", () => {
      expect(
        buildDroidExecArgs({ enabled_tools: ["ApplyPatch", "Read"] }),
      ).toEqual(["--enabled-tools", "ApplyPatch,Read"]);
    });

    it("joins disabled_tools with commas", () => {
      expect(
        buildDroidExecArgs({ disabled_tools: ["execute-cli"] }),
      ).toEqual(["--disabled-tools", "execute-cli"]);
    });

    it("omits enabled/disabled_tools when array is empty", () => {
      expect(
        buildDroidExecArgs({ enabled_tools: [], disabled_tools: [] }),
      ).toEqual([]);
    });

    it("maps list_tools to --list-tools", () => {
      expect(buildDroidExecArgs({ list_tools: true })).toEqual(["--list-tools"]);
    });
  });

  describe("tags", () => {
    it("emits a bare string tag as --tag <name>", () => {
      expect(buildDroidExecArgs({ tags: ["code-review"] })).toEqual([
        "--tag",
        "code-review",
      ]);
    });

    it("emits an object tag as --tag <json>", () => {
      expect(
        buildDroidExecArgs({
          tags: [{ name: "code-review", metadata: { prUrl: "x" } }],
        }),
      ).toEqual(["--tag", '{"name":"code-review","metadata":{"prUrl":"x"}}']);
    });

    it("repeats --tag for every entry", () => {
      expect(
        buildDroidExecArgs({
          tags: ["a", { name: "b" }, "c"],
        }),
      ).toEqual([
        "--tag",
        "a",
        "--tag",
        '{"name":"b"}',
        "--tag",
        "c",
      ]);
    });

    it("maps log_group_id to --log-group-id", () => {
      expect(buildDroidExecArgs({ log_group_id: "grp-1" })).toEqual([
        "--log-group-id",
        "grp-1",
      ]);
    });
  });

  describe("mission", () => {
    it("emits --mission when auto: high is present", () => {
      expect(buildDroidExecArgs({ mission: true, auto: "high" })).toEqual([
        "--auto",
        "high",
        "--mission",
      ]);
    });

    it("emits --mission when allow_unsafe is present", () => {
      expect(
        buildDroidExecArgs({ mission: true, allow_unsafe: true }),
      ).toEqual(["--skip-permissions-unsafe", "--mission"]);
    });

    it("throws when mission is set without auto: high or allow_unsafe", () => {
      expect(() => buildDroidExecArgs({ mission: true })).toThrow(
        DroidFlagsError,
      );
      expect(() =>
        buildDroidExecArgs({ mission: true, auto: "low" }),
      ).toThrow(DroidFlagsError);
    });
  });

  describe("system prompt", () => {
    it("maps system_prompt to --append-system-prompt", () => {
      expect(buildDroidExecArgs({ system_prompt: "extra" })).toEqual([
        "--append-system-prompt",
        "extra",
      ]);
    });

    it("maps system_prompt_file to --append-system-prompt-file", () => {
      expect(
        buildDroidExecArgs({
          system_prompt_file: "/Users/serkan/.factory/droids/deep-researcher.md",
        }),
      ).toEqual([
        "--append-system-prompt-file",
        "/Users/serkan/.factory/droids/deep-researcher.md",
      ]);
    });
  });

  describe("spec mode", () => {
    it("maps use_spec to --use-spec", () => {
      expect(buildDroidExecArgs({ use_spec: true })).toEqual(["--use-spec"]);
    });

    it("maps spec_model to --spec-model", () => {
      expect(buildDroidExecArgs({ spec_model: "custom:glm-5.1" })).toEqual([
        "--spec-model",
        "custom:glm-5.1",
      ]);
    });

    it("maps spec_reasoning_effort to --spec-reasoning-effort", () => {
      expect(buildDroidExecArgs({ spec_reasoning_effort: "high" })).toEqual([
        "--spec-reasoning-effort",
        "high",
      ]);
    });
  });

  describe("settings file", () => {
    it("maps settings_file to --settings", () => {
      expect(buildDroidExecArgs({ settings_file: "/tmp/s.json" })).toEqual([
        "--settings",
        "/tmp/s.json",
      ]);
    });
  });

  describe("composite", () => {
    it("places the prompt last after all options", () => {
      const args = buildDroidExecArgs({
        prompt: "refactor",
        model: "custom:glm-5-turbo",
        auto: "low",
        output_format: "stream-json",
        cwd: "/Users/serkan/nt-dev",
      });
      expect(args).toEqual([
        "--model",
        "custom:glm-5-turbo",
        "--auto",
        "low",
        "--output-format",
        "stream-json",
        "--cwd",
        "/Users/serkan/nt-dev",
        "refactor",
      ]);
    });

    it("handles a realistic research preset invocation", () => {
      const args = buildDroidExecArgs({
        prompt: "what is the meaning of life",
        model: "custom:glm-5-turbo",
        auto: "high",
        output_format: "stream-json",
        system_prompt_file:
          "/Users/serkan/.factory/droids/deep-researcher.md",
        tags: ["research"],
      });
      expect(args).toContain("--model");
      expect(args).toContain("custom:glm-5-turbo");
      expect(args).toContain("--auto");
      expect(args).toContain("high");
      expect(args).toContain("--append-system-prompt-file");
      expect(args).toContain("/Users/serkan/.factory/droids/deep-researcher.md");
      expect(args).toContain("--tag");
      expect(args).toContain("research");
      // prompt must be last
      expect(args[args.length - 1]).toBe("what is the meaning of life");
    });
  });
});
