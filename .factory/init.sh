#!/bin/bash
# Idempotent environment setup for the file-writing mission

# Clean up any previous run artifacts
rm -rf /tmp/mcp-droid-test-xyz

# Ensure parent directory exists
mkdir -p /tmp

echo "Environment ready."
