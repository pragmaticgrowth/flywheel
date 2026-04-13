/**
 * Meta tools — surface droid's catalog of models and profiles.
 * Read-only, filesystem-based, no provider dispatch needed.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { listModels } from "../droid/models.js";
import { listProfiles } from "../droid/profiles.js";
import { resolveCwd } from "../utils/cwd.js";
import {
  createJsonResponse,
  createUnexpectedErrorResponse,
  type McpToolResponse,
} from "../utils/errors.js";

export function registerMetaTools(server: McpServer): void {
  server.registerTool(
    "do_list_models",
    {
      description:
        "List custom (BYOK) models from ~/.factory/settings.json. Returns canonical id, short alias, display name, and provider.",
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
    "do_list_profiles",
    {
      description:
        "List droid agent profiles from ~/.factory/droids/*.md (global) and <cwd>/.factory/droids/*.md (project-local). Project profiles shadow global ones.",
      inputSchema: {
        cwd: z.string().optional().describe("Working directory for project-local profiles."),
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
}
