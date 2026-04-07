---
name: file-writer
description: Write content to files
---

# File Writer Worker

## When to Use This Skill

Features that need to create or write files with specific content.

## Required Skills

None required for simple file writing.

## Work Procedure

1. Create the target directory if it doesn't exist: `mkdir -p /tmp/mcp-droid-mismatch`
2. Write the content to the specified file using `echo "content" > /path/to/file`
3. Verify the file was written correctly using `cat /path/to/file`
4. Confirm the content matches expected value

## Example Handoff

```json
{
  "salientSummary": "Created /tmp/mcp-droid-mismatch/step1.txt with content 'hello'",
  "whatWasImplemented": "File step1.txt created with 'hello' content",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "mkdir -p /tmp/mcp-droid-mismatch",
        "exitCode": 0,
        "observation": "Directory created"
      },
      {
        "command": "echo 'hello' > /tmp/mcp-droid-mismatch/step1.txt",
        "exitCode": 0,
        "observation": "File written"
      },
      {
        "command": "cat /tmp/mcp-droid-mismatch/step1.txt",
        "exitCode": 0,
        "observation": "hello"
      }
    ],
    "interactiveChecks": []
  },
  "tests": { "added": [] },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Directory cannot be created
- File write fails
- Content verification fails
