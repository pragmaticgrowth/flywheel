#!/bin/bash
# setup-check.sh — verify droid + opencode installations
# Outputs JSON for /do:setup to parse

set -euo pipefail

check_binary() {
  local name="$1"
  local path
  path=$(which "$name" 2>/dev/null || echo "")
  if [ -n "$path" ]; then
    echo "{\"found\": true, \"path\": \"$path\"}"
  else
    echo "{\"found\": false, \"path\": null}"
  fi
}

check_config() {
  local config_path="$HOME/.config/mcp-do/config.json"
  if [ -f "$config_path" ]; then
    local provider
    provider=$(grep -o '"default_provider"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_path" 2>/dev/null | head -1 | sed 's/.*: *"\([^"]*\)"/\1/')
    echo "{\"found\": true, \"path\": \"$config_path\", \"default_provider\": \"${provider:-droid}\"}"
  else
    echo "{\"found\": false, \"path\": \"$config_path\", \"default_provider\": null}"
  fi
}

check_opencode_agents() {
  local agents_dir="$HOME/.config/opencode/agents"
  local found=0
  local total=3
  for agent in research.md review.md droid-explore.md; do
    [ -f "$agents_dir/$agent" ] && found=$((found + 1))
  done
  echo "{\"synced\": $found, \"total\": $total, \"path\": \"$agents_dir\"}"
}

echo "{"
echo "  \"droid\": $(check_binary droid),"
echo "  \"opencode\": $(check_binary opencode),"
echo "  \"config\": $(check_config),"
echo "  \"opencode_agents\": $(check_opencode_agents)"
echo "}"
