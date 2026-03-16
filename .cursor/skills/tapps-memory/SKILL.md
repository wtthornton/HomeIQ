---
name: tapps-memory
description: >-
  Manage shared project memory for cross-session knowledge persistence.
  20 actions: save, search, consolidate, federation, and more.
mcp_tools:
  - tapps_memory
  - tapps_session_notes
---

Manage shared project memory using TappsMCP (20 actions):

**Core CRUD:** save, save_bulk, get, list, delete
**Search:** search (ranked BM25 with composite scoring)
**Intelligence:** reinforce, gc, contradictions, reseed
**Consolidation:** consolidate (merge related entries), unconsolidate (undo)
**Import/export:** import (JSON), export (JSON or Markdown)
**Federation:** federate_register, federate_publish, federate_subscribe, federate_sync, federate_search, federate_status

Steps:
1. Determine the action from the list above
2. For saves, classify tier (architectural/pattern/procedural/context) and scope (project/branch/session/shared)
3. Call `tapps_memory` with the action and parameters
4. Display results with confidence scores and composite relevance scores
