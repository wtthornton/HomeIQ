---
name: tapps-memory
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Manage shared project memory for cross-session knowledge persistence.
  20 actions: save, search, consolidate, federation, and more.
allowed-tools: mcp__tapps-mcp__tapps_memory mcp__tapps-mcp__tapps_session_notes
argument-hint: "[action] [key]"
---

Manage shared project memory using TappsMCP (20 actions):

**Core CRUD:** save, save_bulk, get, list, delete
**Search:** search (ranked BM25 with composite scoring)
**Intelligence:** reinforce (reset decay), gc (archive stale), contradictions (detect stale claims), reseed
**Consolidation:** consolidate (merge related entries with provenance), unconsolidate (undo)
**Import/export:** import (JSON), export (JSON or Markdown)
**Federation:** federate_register, federate_publish, federate_subscribe, federate_sync, federate_search, federate_status

Steps:
1. Determine the action from the list above
2. For saves, classify tier (architectural/pattern/procedural/context) and scope (project/branch/session/shared)
3. Call `mcp__tapps-mcp__tapps_memory` with the action and parameters
4. Display results with confidence scores, tiers, and composite relevance scores
5. For consolidation, use `dry_run=True` first to preview merged entries
6. For federation, register the project first, then publish shared-scope entries
