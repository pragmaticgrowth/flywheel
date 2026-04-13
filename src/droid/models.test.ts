/**
 * Unit tests for the models module: settings.json customModels[] reader
 * with alias enrichment.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { CUSTOM_MODEL_ALIASES, listModels } from "./models.js";

let tmpDir: string;
let tmpSettings: string;

beforeEach(async () => {
  tmpDir = await mkdtemp(join(tmpdir(), "mcp-do-models-test-"));
  tmpSettings = join(tmpDir, "settings.json");
});

afterEach(async () => {
  await rm(tmpDir, { recursive: true, force: true });
});

async function writeSettings(custom: Array<Record<string, unknown>>): Promise<void> {
  await writeFile(
    tmpSettings,
    JSON.stringify({ customModels: custom }),
  );
}

describe("CUSTOM_MODEL_ALIASES", () => {
  it("includes the four BYOK aliases verified at planning time", () => {
    expect(CUSTOM_MODEL_ALIASES["custom:BYOK-GLM-5-Turbo-33"]).toBe(
      "custom:glm-5-turbo",
    );
    expect(CUSTOM_MODEL_ALIASES["custom:BYOK-MiniMax-M2.7-30"]).toBe(
      "custom:MiniMax-M2.7",
    );
    expect(CUSTOM_MODEL_ALIASES["custom:BYOK-GLM-5.1-31"]).toBe(
      "custom:glm-5.1",
    );
    expect(CUSTOM_MODEL_ALIASES["custom:BYOK-GLM-5-32"]).toBe("custom:glm-5");
  });
});

describe("listModels", () => {
  it("returns an empty array when settings.json does not exist", async () => {
    const result = await listModels({
      settings_path: join(tmpDir, "missing.json"),
    });
    expect(result).toEqual([]);
  });

  it("returns an empty array when settings.json is malformed", async () => {
    await writeFile(tmpSettings, "not json {{");
    const result = await listModels({ settings_path: tmpSettings });
    expect(result).toEqual([]);
  });

  it("returns an empty array when customModels is missing", async () => {
    await writeFile(tmpSettings, JSON.stringify({ otherSetting: 1 }));
    const result = await listModels({ settings_path: tmpSettings });
    expect(result).toEqual([]);
  });

  it("maps a single custom model to its ModelInfo shape", async () => {
    await writeSettings([
      {
        id: "custom:BYOK-GLM-5-Turbo-33",
        model: "glm-5-turbo",
        displayName: "BYOK: GLM-5-Turbo",
        provider: "anthropic",
        baseUrl: "https://api.example.com",
      },
    ]);
    const result = await listModels({ settings_path: tmpSettings });
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: "custom:BYOK-GLM-5-Turbo-33",
      display_name: "BYOK: GLM-5-Turbo",
      alias: "custom:glm-5-turbo",
      provider: "anthropic",
      base_url: "https://api.example.com",
    });
  });

  it("omits the alias field when no alias is known", async () => {
    await writeSettings([
      {
        id: "custom:Some-Other-Model-99",
        displayName: "Other",
        provider: "openai",
      },
    ]);
    const result = await listModels({ settings_path: tmpSettings });
    expect(result[0]).not.toHaveProperty("alias");
    expect(result[0]?.id).toBe("custom:Some-Other-Model-99");
  });

  it("omits provider and base_url when missing from the source", async () => {
    await writeSettings([
      { id: "custom:Bare-1", displayName: "Bare" },
    ]);
    const result = await listModels({ settings_path: tmpSettings });
    expect(result[0]).toEqual({
      id: "custom:Bare-1",
      display_name: "Bare",
    });
  });

  it("preserves order from the customModels array", async () => {
    await writeSettings([
      { id: "custom:A-1", displayName: "A" },
      { id: "custom:B-2", displayName: "B" },
      { id: "custom:C-3", displayName: "C" },
    ]);
    const result = await listModels({ settings_path: tmpSettings });
    expect(result.map((m) => m.id)).toEqual([
      "custom:A-1",
      "custom:B-2",
      "custom:C-3",
    ]);
  });

  it("returns BYOK aliases for all four known canonical ids", async () => {
    await writeSettings([
      { id: "custom:BYOK-GLM-5-Turbo-33", displayName: "X" },
      { id: "custom:BYOK-GLM-5.1-31", displayName: "X" },
      { id: "custom:BYOK-GLM-5-32", displayName: "X" },
      { id: "custom:BYOK-MiniMax-M2.7-30", displayName: "X" },
    ]);
    const result = await listModels({ settings_path: tmpSettings });
    expect(result.map((m) => m.alias)).toEqual([
      "custom:glm-5-turbo",
      "custom:glm-5.1",
      "custom:glm-5",
      "custom:MiniMax-M2.7",
    ]);
  });
});
