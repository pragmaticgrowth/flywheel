/**
 * CWD resolution. Tool param wins over process.cwd(). Relative paths are
 * resolved against process.cwd(). Always returns an absolute path.
 */
export declare function resolveCwd(toolParam?: string): string;
