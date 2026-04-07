#!/usr/bin/env bash
# Comprehensive stdio smoke test — exercises every tool that previously
# failed, every tool with a latent fix, plus a real droid exec round-trip.
#
# What it covers (in addition to smoke-stdio-readonly.sh):
#   - droid_list_tools           (the original Zod structuredContent failure)
#   - droid_session_search       (latent same-bug fix)
#   - droid_mission_status       (with a real mission_id from the list)
#   - droid_mission_progress     (with the same mission_id)
#   - droid_exec                 (real MiniMax round-trip — costs a few cents)
#
# Each tools/call is given its own request id so we can correlate response
# to call. Failures are summarized at the end with their full content[0].text.
#
# Usage: bash scripts/smoke-stdio-full.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f dist/index.js ]; then
  echo "dist/index.js missing — run npm run build first" >&2
  exit 1
fi

# Pull a real mission uuid for the status/progress tests. Fall back to a
# placeholder if no missions exist (tests will gracefully report not_found).
MISSION_UUID=$(ls -1 ~/.factory/missions 2>/dev/null | head -1 || true)
if [ -z "$MISSION_UUID" ]; then MISSION_UUID="00000000-0000-0000-0000-000000000000"; fi

OUTPUT=$(
  (
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke-full","version":"0"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
    # Read-only and cheap (no droid spawn)
    printf '%s\n' '{"jsonrpc":"2.0","id":20,"method":"tools/call","params":{"name":"droid_list_models","arguments":{}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":21,"method":"tools/call","params":{"name":"droid_list_profiles","arguments":{}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":22,"method":"tools/call","params":{"name":"droid_session_list","arguments":{"all":true,"limit":3}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":23,"method":"tools/call","params":{"name":"droid_mission_list","arguments":{"all":true,"limit":3}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":24,"method":"tools/call","params":{"name":"droid_mission_status","arguments":{"mission_id":"'"$MISSION_UUID"'","progress_limit":3}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":25,"method":"tools/call","params":{"name":"droid_mission_progress","arguments":{"mission_id":"'"$MISSION_UUID"'","limit":2}}}'
    # Read-only but spawns droid
    printf '%s\n' '{"jsonrpc":"2.0","id":26,"method":"tools/call","params":{"name":"droid_list_tools","arguments":{"model":"custom:glm-5-turbo"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":27,"method":"tools/call","params":{"name":"droid_session_search","arguments":{"query":"droid","cwd":"/Users/serkan","limit_sessions":2,"limit_hits":1}}}'
    # Real exec — cheapest model + tiny prompt
    printf '%s\n' '{"jsonrpc":"2.0","id":28,"method":"tools/call","params":{"name":"droid_exec","arguments":{"prompt":"reply with exactly: ok","model":"custom:MiniMax-M2.7","auto":"high"}}}'
    sleep 90
  ) | node dist/index.js
)

echo "$OUTPUT" | node -e '
const lines = require("fs").readFileSync("/dev/stdin", "utf8").trim().split("\n");
const labels = {
  20: "list_models", 21: "list_profiles", 22: "session_list",
  23: "mission_list", 24: "mission_status", 25: "mission_progress",
  26: "list_tools", 27: "session_search", 28: "exec_real",
};
const results = {};
for (const line of lines) {
  let msg;
  try { msg = JSON.parse(line); } catch { continue; }
  if (msg.id === undefined || labels[msg.id] === undefined) continue;
  const label = labels[msg.id];
  if (msg.error) {
    results[label] = { kind: "rpc_error", text: JSON.stringify(msg.error) };
    continue;
  }
  if (msg.result && msg.result.isError) {
    results[label] = { kind: "tool_error", text: msg.result.content[0].text };
    continue;
  }
  const sc = msg.result && msg.result.structuredContent;
  if (!sc) {
    results[label] = { kind: "ok_no_struct", text: "(no structuredContent)" };
    continue;
  }
  // Render a compact summary per tool
  let summary = "";
  if (sc.count !== undefined) summary += "count=" + sc.count;
  if (Array.isArray(sc.tools)) summary += " first_tool=" + JSON.stringify(sc.tools[0] && (sc.tools[0].name || sc.tools[0].id || sc.tools[0])).slice(0, 60);
  if (Array.isArray(sc.hits)) summary += " first_hit_keys=" + JSON.stringify(Object.keys(sc.hits[0] || {})).slice(0, 80);
  if (Array.isArray(sc.models)) summary += " first_model=" + (sc.models[0] && sc.models[0].id);
  if (Array.isArray(sc.profiles)) summary += " first_profile=" + (sc.profiles[0] && sc.profiles[0].name);
  if (Array.isArray(sc.sessions)) summary += " first_cwd=" + (sc.sessions[0] && sc.sessions[0].cwd);
  if (Array.isArray(sc.missions)) summary += " first_mission=" + (sc.missions[0] && (sc.missions[0].mission_id + "/" + sc.missions[0].state));
  if (sc.events !== undefined) summary += " events_len=" + (Array.isArray(sc.events) ? sc.events.length : "?");
  if (sc.recent_events !== undefined) summary += " recent_events_len=" + (Array.isArray(sc.recent_events) ? sc.recent_events.length : "?");
  if (sc.text !== undefined) summary += " text=" + JSON.stringify((sc.text || "").slice(0, 30));
  if (sc.session_id !== undefined) summary += " sid=" + sc.session_id;
  if (sc.usage && sc.usage.input_tokens) summary += " in_tok=" + sc.usage.input_tokens;
  results[label] = { kind: "ok", text: summary.trim() || "(empty)" };
}
const order = Object.values(labels);
let pass = 0, fail = 0;
console.log("=== smoke-stdio-full results ===");
for (const label of order) {
  const r = results[label];
  if (!r) {
    console.log("[" + label + "] MISSING (no response)");
    fail++;
    continue;
  }
  const tag = r.kind === "ok" ? "OK" : r.kind === "ok_no_struct" ? "OK*" : r.kind === "tool_error" ? "TOOL_ERR" : "RPC_ERR";
  console.log("[" + label + "] " + tag + " — " + r.text.slice(0, 280));
  if (r.kind === "ok" || r.kind === "ok_no_struct") pass++; else fail++;
}
console.log("===");
console.log("PASS=" + pass + " FAIL=" + fail + " TOTAL=" + order.length);
process.exit(fail === 0 ? 0 : 1);
'
