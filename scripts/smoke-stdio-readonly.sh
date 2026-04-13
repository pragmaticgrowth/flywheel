#!/usr/bin/env bash
# Smoke test that exercises every read-only MCP tool that doesn't require
# spawning a real droid CLI run. Verifies the fs reader → tool layer → MCP
# transport pipeline end-to-end.
#
# Usage: bash scripts/smoke-stdio-readonly.sh

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
    printf '%s\n' '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"do_list_models","arguments":{}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"do_list_profiles","arguments":{}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"droid_session_list","arguments":{"all":true,"limit":3}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"droid_mission_list","arguments":{"all":true,"limit":3}}}'
    sleep 1
  ) | node dist/index.js
)

echo "$OUTPUT" | node -e '
const lines = require("fs").readFileSync("/dev/stdin", "utf8").trim().split("\n");
const labels = { 10: "list_models", 11: "list_profiles", 12: "session_list", 13: "mission_list" };
for (const line of lines) {
  try {
    const msg = JSON.parse(line);
    if (msg.id === undefined || labels[msg.id] === undefined) continue;
    const label = labels[msg.id];
    if (msg.error) {
      console.log("[" + label + "] ERROR: " + JSON.stringify(msg.error));
      continue;
    }
    if (msg.result && msg.result.isError) {
      console.log("[" + label + "] isError: " + msg.result.content[0].text.slice(0, 200));
      continue;
    }
    const sc = msg.result && msg.result.structuredContent;
    if (sc) {
      const summary = {};
      if (sc.count !== undefined) summary.count = sc.count;
      if (Array.isArray(sc.models)) summary.first_model = sc.models[0] && sc.models[0].id;
      if (Array.isArray(sc.profiles)) summary.first_profile = sc.profiles[0] && sc.profiles[0].name;
      if (Array.isArray(sc.sessions)) summary.first_session_cwd = sc.sessions[0] && sc.sessions[0].cwd;
      if (Array.isArray(sc.missions)) summary.first_mission = sc.missions[0] && (sc.missions[0].mission_id + " " + sc.missions[0].state);
      console.log("[" + label + "] OK " + JSON.stringify(summary));
    } else {
      console.log("[" + label + "] OK (no structured content)");
    }
  } catch (e) {}
}
'
