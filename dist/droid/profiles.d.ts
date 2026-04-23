/**
 * Read droid profile files from `~/.factory/droids/*.md` (global) and
 * `<cwd>/.factory/droids/*.md` (project-local override). Project-local
 * profiles SHADOW global ones with the same name (matching how droid
 * actually resolves them).
 *
 * Each profile is a markdown file with a YAML front-matter block:
 *
 *   ---
 *   name: deep-researcher
 *   description: "..."
 *   model: inherit
 *   tools: ["Read", "Grep", ...]
 *   ---
 *
 *   # Deep Researcher
 *   ...
 *
 * The parser is intentionally lightweight — no full YAML library — because
 * droid's front-matter is a small, predictable subset.
 */
export interface ProfileInfo {
    name: string;
    scope: "global" | "project";
    path: string;
    description?: string;
    model?: string;
    tools?: string[];
    /** Anything else parsed out of the front-matter that we don't have a typed slot for. */
    raw_front_matter?: Record<string, unknown>;
}
/**
 * Parse a tiny YAML-ish front-matter block. Supports:
 *   - key: scalar
 *   - key: "quoted scalar"
 *   - key: ["a", "b", "c"]   (single-line JSON array)
 *
 * Anything fancier becomes a raw string in raw_front_matter.
 */
export declare function parseFrontMatter(source: string): {
    data: Record<string, unknown>;
    body: string;
};
export interface ListProfilesOptions {
    cwd?: string;
    /** Override the global droids directory (for tests). */
    global_dir?: string;
}
export declare function listProfiles(opts?: ListProfilesOptions): Promise<ProfileInfo[]>;
