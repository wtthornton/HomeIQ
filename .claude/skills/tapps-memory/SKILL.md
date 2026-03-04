---
name: tapps-memory
description: >-
  Manage shared project memory for cross-session knowledge persistence.
  Save, retrieve, search, and manage memory entries with tier classification.
allowed-tools: mcp__tapps-mcp__tapps_memory, mcp__tapps-mcp__tapps_session_notes
argument-hint: "[action] [key]"
---

Manage shared project memory using TappsMCP:

1. Determine the action: save, get, list, search, or delete
2. For saves, classify the memory tier (team, project, or session)
3. Call `mcp__tapps-mcp__tapps_memory` with the appropriate action and parameters
4. Display results with confidence scores and metadata
5. Suggest tier promotions for frequently accessed session-level memories
