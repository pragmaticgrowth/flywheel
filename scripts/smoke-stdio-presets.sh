#!/usr/bin/env bash
# Exercise every specialized preset wrapper end-to-end. Each preset is a
# thin wrapper over spawnDroidExec with a fixed --append-system-prompt-file
# and a default model — high confidence they share the same machinery, but
# until each one is actually invoked through MCP we haven't verified its
# registration / argv / response shape are correct.
#
# Cost: 11 calls × ~5s × MiniMax (cheap) ≈ 55 s and a few cents.
#
# Each preset is asked to reply with exactly one keyword so the smoke can
# assert text-equality. If a preset is misregistered, missing its profile
# file, or routes the prompt wrong, the assertion will fail.
#
# Usage: bash scripts/smoke-stdio-presets.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f dist/index.js ]; then
  echo "dist/index.js missing — run npm run build first" >&2
  exit 1
fi

OUTPUT=$(
  (
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke-presets","version":"0"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'

    # Each preset gets its own keyword and id. Using MiniMax for everything
    # — even the architect preset which normally defaults to glm-5.1 — to
    # keep cost minimal during smoke.
    printf '%s\n' '{"jsonrpc":"2.0","id":40,"method":"tools/call","params":{"name":"do_research","arguments":{"prompt":"reply with exactly: RESEARCH_OK and stop","model":"custom:MiniMax-M2.7","auto":"high"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":41,"method":"tools/call","params":{"name":"droid_research_fast","arguments":{"prompt":"reply with exactly: RESEARCH_FAST_OK and stop"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"droid_review_code","arguments":{"prompt":"reply with exactly: REVIEW_CODE_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":43,"method":"tools/call","params":{"name":"droid_explore_code","arguments":{"prompt":"reply with exactly: EXPLORE_CODE_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":44,"method":"tools/call","params":{"name":"do_architect","arguments":{"prompt":"reply with exactly: ARCHITECT_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":45,"method":"tools/call","params":{"name":"droid_simplify","arguments":{"prompt":"reply with exactly: SIMPLIFY_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":46,"method":"tools/call","params":{"name":"droid_silent_failure_scan","arguments":{"prompt":"reply with exactly: SILENT_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":47,"method":"tools/call","params":{"name":"droid_pr_test_analyzer","arguments":{"prompt":"reply with exactly: PR_TEST_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":48,"method":"tools/call","params":{"name":"droid_type_design_analyzer","arguments":{"prompt":"reply with exactly: TYPE_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":49,"method":"tools/call","params":{"name":"droid_scrutiny_review","arguments":{"prompt":"reply with exactly: SCRUTINY_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","id":50,"method":"tools/call","params":{"name":"droid_user_testing_validator","arguments":{"prompt":"reply with exactly: UTV_OK and stop","model":"custom:MiniMax-M2.7"}}}'
    sleep 180
  ) | node dist/index.js
)

echo "$OUTPUT" | node -e '
const lines = require("fs").readFileSync("/dev/stdin","utf8").trim().split("\n");
const expectations = {
  40: { name: "do_research",                expect: "RESEARCH_OK" },
  41: { name: "droid_research_fast",           expect: "RESEARCH_FAST_OK" },
  42: { name: "droid_review_code",             expect: "REVIEW_CODE_OK" },
  43: { name: "droid_explore_code",            expect: "EXPLORE_CODE_OK" },
  44: { name: "do_architect",               expect: "ARCHITECT_OK" },
  45: { name: "droid_simplify",                expect: "SIMPLIFY_OK" },
  46: { name: "droid_silent_failure_scan",     expect: "SILENT_OK" },
  47: { name: "droid_pr_test_analyzer",        expect: "PR_TEST_OK" },
  48: { name: "droid_type_design_analyzer",    expect: "TYPE_OK" },
  49: { name: "droid_scrutiny_review",         expect: "SCRUTINY_OK" },
  50: { name: "droid_user_testing_validator",  expect: "UTV_OK" },
};
const results = {};
for (const line of lines) {
  let m;
  try { m = JSON.parse(line); } catch { continue; }
  if (m.id === undefined || expectations[m.id] === undefined) continue;
  const exp = expectations[m.id];
  if (m.error) {
    results[m.id] = { kind: "rpc_error", text: JSON.stringify(m.error).slice(0,300) };
    continue;
  }
  if (m.result?.isError) {
    results[m.id] = { kind: "tool_error", text: (m.result.content[0].text||"").slice(0,300) };
    continue;
  }
  const sc = m.result?.structuredContent || {};
  const text = (sc.text || "").trim();
  const sid = sc.session_id;
  const has = text.includes(exp.expect);
  results[m.id] = {
    kind: has ? "ok" : "wrong_text",
    text: "got=" + JSON.stringify(text.slice(0,80)) + " sid=" + (sid||"none"),
  };
}
let pass = 0, fail = 0;
console.log("=== smoke-stdio-presets results ===");
for (const id of Object.keys(expectations).map(Number).sort((a,b)=>a-b)) {
  const exp = expectations[id];
  const r = results[id];
  if (!r) {
    console.log(`[${exp.name}] MISSING (no response)`);
    fail++;
    continue;
  }
  const tag = r.kind === "ok" ? "OK" : r.kind === "wrong_text" ? "WRONG" : r.kind === "tool_error" ? "TOOL_ERR" : "RPC_ERR";
  console.log(`[${exp.name}] ${tag} — ${r.text}`);
  if (r.kind === "ok") pass++; else fail++;
}
console.log("===");
console.log("PASS=" + pass + " FAIL=" + fail + " TOTAL=" + Object.keys(expectations).length);
process.exit(fail === 0 ? 0 : 1);
'
