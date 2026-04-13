/**
 * droid_spec — wrap `droid exec --use-spec [...]`. Spec mode is droid's
 * structured planning workflow that produces a written spec before execution.
 *
 * NOTE on autonomy: spec mode is stochastic. After the model calls
 * ExitSpecMode to approve the spec, it may try to execute on the approved
 * plan (Create/Edit/Execute tool calls). Without an `auto` level set, those
 * calls are blocked, and depending on how the model recovers, droid can exit
 * nonzero. Pass auto: "low" (default) to let the model write the spec file
 * and perform simple file edits cleanly.
 */
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
export declare function registerSpecTool(server: McpServer): void;
