#!/usr/bin/env bash
# Smoke test that lists every tool exposed by the built MCP server.
# Pipes initialize + tools/list and prints each tool name on its own line.
#
# Usage: bash scripts/smoke-stdio-list.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f dist/index.js ]; then
  echo "dist/index.js missing — run npm run build first" >&2
  exit 1
fi

OUTPUT=$(
  (
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
    printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
    sleep 0.5
  ) | node dist/index.js
)

echo "$OUTPUT" | node -e '
const lines = require("fs").readFileSync("/dev/stdin", "utf8").trim().split("\n");
for (const line of lines) {
  try {
    const msg = JSON.parse(line);
    if (msg.id === 2 && msg.result && msg.result.tools) {
      console.log("=== " + msg.result.tools.length + " tools registered ===");
      for (const t of msg.result.tools) console.log("  - " + t.name);
      process.exit(0);
    }
  } catch (e) {}
}
console.error("no tools/list response found");
process.exit(1);
'
