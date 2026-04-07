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
        "List custom (BYOK) models from ~/.factory/settings.json customModels[]. Each entry includes its canonical id (e.g. custom:BYOK-GLM-5-Turbo-33), a short alias when known (custom:glm-5-turbo), display name, and provider. Factory's built-in models are intentionally NOT listed — use only custom models.",
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
        "Run `droid exec --list-tools` for a custom model and return the parsed tool catalog. Useful for discovering what tools a model has access to before launching a session. Defaults to custom:glm-5-turbo when no model is specified.",
      inputSchema: {
        model: z
          .string()
          .optional()
          .describe(
            "Custom model id. Defaults to custom:glm-5-turbo. Use only custom: models — factory built-ins are off-limits.",
          ),
        cwd: z.string().optional(),
      },
    },
    async ({ model, cwd }): Promise<McpToolResponse> => {
      try {
        const result = await spawnDroidExec(
          {
            model: model ?? "custom:glm-5-turbo",
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
