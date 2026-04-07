# Bash Worker Skill

Execute bash commands for file operations and system tasks.

## Procedure

1. **Read mission context** — read `mission.md` and `AGENTS.md` from the mission directory
2. **Verify preconditions** — check that any preconditions for this feature are met
3. **Execute commands** — run the bash commands to fulfill the feature's expected behavior
4. **Verify results** — run verification steps to confirm success
5. **Commit work** — git commit with descriptive message

## Bash Command Patterns

### File Writing
```bash
mkdir -p /path/to/dir
echo -n "content" > /path/to/file  # -n suppresses trailing newline
cat /path/to/file                  # verify content
wc -c /path/to/file                # verify byte count
```

### Timestamp Verification
```bash
stat -c %Y /path/to/file           # get modify timestamp
```

### Content Integrity
```bash
md5sum /path/to/file              # verify content hash
```

## Handoff Fields

On completion, report:
- `successState`: "success" or "failure"
- `filesModified`: array of files created/modified
- `verificationResults`: output of verification commands
