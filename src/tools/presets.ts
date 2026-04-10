/**
 * Specialized preset tools — one per droid profile in ~/.factory/droids/.
 * Each preset is a thin wrapper over spawnDroidExec that hardcodes
 * `--append-system-prompt-file` + a sensible default model + (optionally)
 * a default autonomy level.
 *
 * Users can override model, auto, reasoning_effort, session_id, tags,
 * timeout_ms, and cwd at call time — everything else (the system prompt
 * file, the tool name, the description) is fixed at registration.
 *
 * If the profile file is missing on disk, the preset returns an isError
 * response immediately — no silent fallback (spec §6.2).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawnDroidExec } from "../droid/exec.js";
import type { AutoLevel } from "../droid/flags.js";
import { PresetInputShape, type PresetInput } from "../schemas/preset.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createUnexpectedErrorResponse,
  execResultToToolResponse,
  type McpToolResponse,
} from "../utils/errors.js";

interface PresetSpec {
  name: string;
  description: string;
  profile_file: string;
  default_model: string;
  default_auto?: AutoLevel;
}

const DROIDS_DIR = join(homedir(), ".factory", "droids");

const PRESETS: PresetSpec[] = [
  {
    name: "droid_research",
    description:
      "Deep web research via droid's deep-researcher profile — parallel search across web, Reddit, HN, X, news, plus Context7 docs lookup. Self-evaluates findings and re-triggers on gaps. Default model: custom:glm-5-turbo (best quality + tool calling). Default --auto high.",
    profile_file: join(DROIDS_DIR, "deep-researcher.md"),
    default_model: "custom:glm-5-turbo",
    default_auto: "high",
  },
  {
    name: "droid_research_fast",
    description:
      "Cheap/fast web research via the deep-researcher profile, backed by MiniMax M2.7. Use for simple lookups where speed matters more than tool-calling depth. For quality research use droid_research (GLM-5-Turbo).",
    profile_file: join(DROIDS_DIR, "deep-researcher.md"),
    default_model: "custom:MiniMax-M2.7",
    default_auto: "high",
  },
  {
    name: "droid_review_code",
    description:
      "Structured code review via the code-reviewer profile. Read-only — does not modify files. Returns categorized feedback (bugs, security, design, style).",
    profile_file: join(DROIDS_DIR, "code-reviewer.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_explore_code",
    description:
      "Codebase navigation and feature lookup via the code-explorer profile. Read-only. Use for 'where is feature X implemented?' and 'how does subsystem Y work?' questions.",
    profile_file: join(DROIDS_DIR, "code-explorer.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_architect",
    description:
      "High-level architecture analysis via the code-architect profile. Uses GLM-5.1 (slowest but deepest analysis). Read-only.",
    profile_file: join(DROIDS_DIR, "code-architect.md"),
    default_model: "custom:glm-5.1",
  },
  {
    name: "droid_simplify",
    description:
      "Refactor toward simpler code via the code-simplifier profile. Default --auto low (can edit files).",
    profile_file: join(DROIDS_DIR, "code-simplifier.md"),
    default_model: "custom:glm-5-turbo",
    default_auto: "low",
  },
  {
    name: "droid_silent_failure_scan",
    description:
      "Scan for silent error swallows (empty catches, ignored promises, .catch(() => {})) via the silent-failure-hunter profile. Read-only.",
    profile_file: join(DROIDS_DIR, "silent-failure-hunter.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_pr_test_analyzer",
    description:
      "Analyze PR test coverage via the pr-test-analyzer profile. Checks whether new code has corresponding tests.",
    profile_file: join(DROIDS_DIR, "pr-test-analyzer.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_type_design_analyzer",
    description:
      "Review TypeScript type design via the type-design-analyzer profile. Flags 'any' leaks, overly-permissive unions, missing discriminators.",
    profile_file: join(DROIDS_DIR, "type-design-analyzer.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_scrutiny_review",
    description:
      "Detailed feature review via the scrutiny-feature-reviewer profile. Deep-dive on a single feature, not a broad review.",
    profile_file: join(DROIDS_DIR, "scrutiny-feature-reviewer.md"),
    default_model: "custom:glm-5-turbo",
  },
  {
    name: "droid_user_testing_validator",
    description:
      "Validate user-facing flows via the user-testing-flow-validator profile. Checks that the flow behaves as users would expect.",
    profile_file: join(DROIDS_DIR, "user-testing-flow-validator.md"),
    default_model: "custom:glm-5-turbo",
  },
];

async function profileExists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

function makePresetHandler(spec: PresetSpec) {
  return async (input: PresetInput): Promise<McpToolResponse> => {
    try {
      if (!(await profileExists(spec.profile_file))) {
        return createErrorResponse(
          `profile not found at ${spec.profile_file} — expected ${spec.name} to have a system prompt file available`,
        );
      }

      const result = await spawnDroidExec(
        {
          prompt: input.prompt,
          model: input.model ?? spec.default_model,
          auto: input.auto ?? spec.default_auto,
          reasoning_effort: input.reasoning_effort,
          session_id: input.session_id,
          tags: input.tags,
          system_prompt_file: spec.profile_file,
        },
        {
          cwd: resolveCwd(input.cwd),
          timeout_ms: input.timeout_ms,
        },
      );

      return execResultToToolResponse(result);
    } catch (err) {
      return createUnexpectedErrorResponse(err);
    }
  };
}

export function registerPresetTools(server: McpServer): void {
  for (const spec of PRESETS) {
    server.registerTool(
      spec.name,
      {
        description: spec.description,
        inputSchema: PresetInputShape,
      },
      makePresetHandler(spec),
    );
  }
}
