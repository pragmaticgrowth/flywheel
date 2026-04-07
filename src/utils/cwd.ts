/**
 * CWD resolution (spec §8). Tool param wins over process.cwd(). Relative
 * paths are resolved against process.cwd(). Always returns an absolute path.
 */

import { isAbsolute, resolve } from "node:path";

export function resolveCwd(toolParam?: string): string {
  if (toolParam !== undefined && toolParam !== "") {
    return isAbsolute(toolParam) ? toolParam : resolve(process.cwd(), toolParam);
  }
  return process.cwd();
}

/**
 * The encoded session-directory key used at
 * `~/.factory/sessions/<encoded-cwd>/`. Note: filtering by cwd in
 * sessions-index.json does NOT need this — the index stores raw absolute
 * paths. Only used when walking the on-disk sessions directory directly.
 */
export function encodeCwdToSessionsKey(absCwd: string): string {
  return absCwd.replace(/^\//, "-").replace(/\//g, "-");
}
