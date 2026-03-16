---
name: tapps-engagement
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Change the TappsMCP enforcement intensity (high, medium, or low).
  Controls which quality tools are mandatory vs optional.
allowed-tools: mcp__tapps-mcp__tapps_set_engagement_level
argument-hint: "[high|medium|low]"
disable-model-invocation: true
---

Set the TappsMCP LLM engagement level:

1. Call `mcp__tapps-mcp__tapps_set_engagement_level` with the desired level
2. **high** - All quality tools are mandatory; checklist enforces strict compliance
3. **medium** - Balanced enforcement; core tools required, advanced tools recommended
4. **low** - Optional guidance; quality tools are suggestions, not requirements
5. Confirm the level was saved to `.tapps-mcp.yaml`
6. If `content_return: true`, write `.tapps-mcp.yaml` from `file_manifest` using the Write tool
