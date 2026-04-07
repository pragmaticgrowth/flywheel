/**
 * CWD resolution. Tool param wins over process.cwd(). Relative paths are
 * resolved against process.cwd(). Always returns an absolute path.
 */

import { isAbsolute, resolve } from "node:path";

export function resolveCwd(toolParam?: string): string {
  if (toolParam !== undefined && toolParam !== "") {
    return isAbsolute(toolParam) ? toolParam : resolve(process.cwd(), toolParam);
  }
  return process.cwd();
}
