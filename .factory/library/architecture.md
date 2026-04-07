# Architecture

This mission is a simple sequential file writer.

## Components

- 3 files to create: step1.txt, step2.txt, step3.txt
- Each file contains simple text content
- No external services or dependencies

## Data Flow

1. Worker writes content to file using Create tool
2. Worker verifies file content using Read tool
3. Handoff reports verification results
