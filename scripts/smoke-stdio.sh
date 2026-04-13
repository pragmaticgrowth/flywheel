#!/usr/bin/env bash
# Manual stdio smoke test for the built MCP server.
# Pipes a sequence of JSON-RPC messages into `node dist/index.js` and prints
# whatever the server writes back. Used to verify tools/list returns the
# registered tools and tools/call round-trips correctly without needing a
# real MCP client.
#
# Usage: bash scripts/smoke-stdio.sh

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f dist/index.js ]; then
  echo "dist/index.js missing — run npm run build first" >&2
  exit 1
fi

(
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
  printf '%s\n' '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"do_exec","arguments":{"prompt":"reply with exactly: hi","model":"custom:glm-5-turbo"}}}'
  # Keep stdin open long enough for droid to finish.
  sleep 60
) | node dist/index.js
