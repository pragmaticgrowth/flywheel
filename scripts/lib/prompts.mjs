/**
 * Prompt template loading and interpolation for mcp-do hook scripts.
 */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

/**
 * Load a prompt template from the prompts/ directory.
 * @param {string} rootDir - Plugin root directory
 * @param {string} name - Template name (without .md extension)
 * @returns {string} Template content
 */
export function loadPromptTemplate(rootDir, name) {
  const templatePath = path.join(rootDir, "prompts", `${name}.md`);
  return fs.readFileSync(templatePath, "utf8");
}

/**
 * Replace {{KEY}} placeholders in a template with provided values.
 * @param {string} template - Template string with {{KEY}} placeholders
 * @param {Record<string, string>} variables - Key-value pairs for interpolation
 * @returns {string} Interpolated template
 */
export function interpolateTemplate(template, variables) {
  let result = template;
  for (const [key, value] of Object.entries(variables)) {
    result = result.replaceAll(`{{${key}}}`, value ?? "");
  }
  const remaining = result.match(/\{\{[A-Z_]+\}\}/g);
  if (remaining) {
    process.stderr.write(
      `Warning: unreplaced template vars: ${remaining.join(", ")}\n`,
    );
  }
  return result;
}
