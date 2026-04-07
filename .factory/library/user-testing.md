## Validation Concurrency

- terminal: max 1 concurrent validator (shared working directory files; assertions mutate/read the same global file set, so run serially).

## Flow Validator Guidance: terminal

- Assigned surface: terminal verification in /Users/serkan/mcp-droid.
- Stay within the repo working directory and only inspect step1.txt, step2.txt, and step3.txt.
- Do not modify files during validation; read-only checks only.
- Because all assertions share the same files and directory, validators for this surface must run serially.
