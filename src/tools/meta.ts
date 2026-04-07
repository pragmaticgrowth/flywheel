/**
 * Meta tools — surface droid's catalog of models, profiles, and tools
 * without running an actual completion. All three are read-only and very
 * cheap (filesystem reads + at most one --list-tools spawn).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { spawnDroidExec } from "../droid/exec.js";
import { listModels } from "../droid/models.js";
import { listProfiles } from "../droid/profiles.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createErrorResponse,
  createJsonResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerMetaTools(server: McpServer): void {
  server.registerTool(
    "droid_list_models",
    {
      description:
        "List every model droid can use: built-ins (claude-opus-4-6, gpt-5.4, glm-5, ...) plus custom models from ~/.factory/settings.json customModels[]. Custom models include their short alias when one is known (e.g. custom:BYOK-GLM-5-Turbo-33 → custom:glm-5-turbo).",
      inputSchema: {},
    },
    async (): Promise<McpToolResponse> => {
      try {
        const models = await listModels();
        return createJsonResponse({ count: models.length, models });
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_list_profiles",
    {
      description:
        "List droid agent profiles from ~/.factory/droids/*.md (global) and <cwd>/.factory/droids/*.md (project-local override). Project-local profiles shadow global ones with the same name. Each profile is a markdown file with a YAML front-matter block (name, description, model, tools).",
      inputSchema: {
        cwd: z
          .string()
          .optional()
          .describe(
            "Working directory to scan for project-local profiles. Defaults to the MCP server's cwd.",
          ),
      },
    },
    async ({ cwd }): Promise<McpToolResponse> => {
      try {
        const resolved = resolveCwd(cwd);
        const profiles = await listProfiles({ cwd: resolved });
        return createJsonResponse({ count: profiles.length, profiles });
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );

  server.registerTool(
    "droid_list_tools",
    {
      description:
        "Run `droid exec --list-tools` for the given (or default) model and return the parsed tool catalog. Useful for discovering what tools a model has access to before launching a session.",
      inputSchema: {
        model: z
          .string()
          .optional()
          .describe(
            "Model id. Defaults to droid's session default (custom:VP-Opus-4.6-1M-xHigh-44).",
          ),
        cwd: z.string().optional(),
      },
    },
    async ({ model, cwd }): Promise<McpToolResponse> => {
      try {
        const result = await spawnDroidExec(
          {
            model,
            list_tools: true,
            output_format: "json",
          },
          { cwd: resolveCwd(cwd) },
        );

        if (!result.ok) {
          return createErrorResponse(
            `droid exec --list-tools failed: ${result.error_message ?? result.stderr.trim() ?? "unknown error"}`,
          );
        }

        // --list-tools writes plain JSON to stdout (not stream-json), so the
        // parsed shape will be empty. Try JSON.parse on the raw stdout.
        let payload: unknown = null;
        try {
          payload = JSON.parse(result.stdout);
        } catch {
          payload = { raw_stdout: result.stdout };
        }
        return createJsonResponse(payload);
      } catch (err) {
        return createUnexpectedErrorResponse(err);
      }
    },
  );
}
