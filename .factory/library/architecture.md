# Architecture

Simple sequential file-writing mission. Each step writes one file to a shared directory.

## Components

- **Target directory**: `/tmp/mcp-droid-test-xyz/` — created by step 1
- **Files**: step1.txt ("hello"), step2.txt ("world"), step3.txt ("done")
- **Sequencing**: Each step depends on the previous step's preconditions

## Data Flow

1. Step 1 creates directory + step1.txt
2. Step 2 writes step2.txt
3. Step 3 writes step3.txt

## Invariants

- Each file contains exactly the specified string (no trailing newline)
- Timestamps reflect sequential ordering
- All files readable after creation
