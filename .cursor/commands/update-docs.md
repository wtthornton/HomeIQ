# Update Docs (Simple Mode)

## Overview

Sync documentation with code: @simple-mode *update-docs [path]. Uses @documenter and project doc scripts.

## Steps

1. If the user gave a path (e.g. src/api/), use it; otherwise use project root or ask.
2. Run: @simple-mode *update-docs [path]
3. Execute: @documenter *document or *document-api; sync README or docs/ if project scripts exist. Report updated files.
