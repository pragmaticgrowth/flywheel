---
name: file-writer
description: Write text content to files
---

# File Writer

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features that write simple text content to files.

## Required Skills

None required for this simple file writing task.

## Work Procedure

1. Read the feature description to determine:
   - Which file to create
   - What content to write

2. Write the content to the file using the Create tool with exact content.

3. Verify the file was created correctly by reading it back.

4. Report completion with the verification results.

## Example Handoff

```json
{
  "salientSummary": "Created step1.txt with content 'alpha', verified via cat command.",
  "whatWasImplemented": "File step1.txt created with exact content 'alpha'",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "cat step1.txt",
        "exitCode": 0,
        "observation": "Output: alpha"
      }
    ],
    "interactiveChecks": []
  },
  "tests": { "added": [] },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- File write operation fails
- Content verification fails
- Any unexpected errors occur
