---
name: tapps-engagement
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Change the TappsMCP enforcement intensity (high, medium, or low).
  Controls which quality tools are mandatory vs optional. Use when you want
  to switch between strict, balanced, or advisory enforcement modes.
allowed-tools: mcp__nlt-setup__tapps_set_engagement_level
argument-hint: "[high|medium|low]"
disable-model-invocation: true
---
<!-- upgrade-policy: overwrite. tapps_upgrade replaces this file wholesale on every run and local edits are lost (tapps_init leaves an existing copy alone; upgrade does not). Fold the change upstream into the platform template, or pin the whole directory with an upgrade_skip_files token. -->

Set the TappsMCP LLM engagement level:

1. Call `mcp__nlt-setup__tapps_set_engagement_level` with the desired level
2. **high** - All quality tools are mandatory; checklist enforces strict compliance
3. **medium** - Balanced enforcement; core tools required, advanced tools recommended
4. **low** - Optional guidance; quality tools are suggestions, not requirements
5. Confirm the level was saved to `.tapps-mcp.yaml`
6. If `content_return: true`, write `.tapps-mcp.yaml` from `file_manifest` using the Write tool
