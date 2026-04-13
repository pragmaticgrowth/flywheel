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
import { readdir, readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, join } from "node:path";
const FRONT_MATTER_RE = /^---\s*\n([\s\S]*?)\n---\s*\n/;
/**
 * Parse a tiny YAML-ish front-matter block. Supports:
 *   - key: scalar
 *   - key: "quoted scalar"
 *   - key: ["a", "b", "c"]   (single-line JSON array)
 *
 * Anything fancier becomes a raw string in raw_front_matter.
 */
export function parseFrontMatter(source) {
    const match = FRONT_MATTER_RE.exec(source);
    if (!match)
        return { data: {}, body: source };
    const body = source.slice(match[0].length);
    const data = {};
    const lines = match[1]?.split("\n") ?? [];
    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (line === "" || line.startsWith("#"))
            continue;
        const colonIdx = line.indexOf(":");
        if (colonIdx === -1)
            continue;
        const key = line.slice(0, colonIdx).trim();
        let value = line.slice(colonIdx + 1).trim();
        // Strip surrounding quotes
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
        }
        // JSON array? (single-line)
        if (value.startsWith("[") && value.endsWith("]")) {
            try {
                data[key] = JSON.parse(value);
                continue;
            }
            catch {
                // fall through to string
            }
        }
        data[key] = value;
    }
    return { data, body };
}
async function readProfileFile(path, scope) {
    try {
        const source = await readFile(path, "utf8");
        const { data } = parseFrontMatter(source);
        const name = typeof data.name === "string" ? data.name : basename(path, ".md");
        const profile = {
            name,
            scope,
            path,
            raw_front_matter: data,
        };
        if (typeof data.description === "string")
            profile.description = data.description;
        if (typeof data.model === "string")
            profile.model = data.model;
        if (Array.isArray(data.tools))
            profile.tools = data.tools.filter((t) => typeof t === "string");
        return profile;
    }
    catch {
        return null;
    }
}
async function readDroidsDir(dir, scope) {
    let entries;
    try {
        entries = await readdir(dir);
    }
    catch {
        return [];
    }
    const mdFiles = entries.filter((e) => e.endsWith(".md"));
    const profiles = await Promise.all(mdFiles.map((entry) => readProfileFile(join(dir, entry), scope)));
    return profiles.filter((p) => p !== null);
}
export async function listProfiles(opts = {}) {
    const globalDir = opts.global_dir ?? join(homedir(), ".factory", "droids");
    const projectDir = opts.cwd ? join(opts.cwd, ".factory", "droids") : null;
    const [globals, projects] = await Promise.all([
        readDroidsDir(globalDir, "global"),
        projectDir ? readDroidsDir(projectDir, "project") : Promise.resolve([]),
    ]);
    // Project profiles SHADOW global ones with the same name.
    const byName = new Map();
    for (const p of globals)
        byName.set(p.name, p);
    for (const p of projects)
        byName.set(p.name, p);
    return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name));
}
//# sourceMappingURL=profiles.js.map