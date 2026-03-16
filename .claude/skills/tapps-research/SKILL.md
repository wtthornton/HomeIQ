---
name: tapps-research
user-invocable: true
description: >-
  Research a technical question using domain experts and library docs.
  Combines expert consultation with docs lookup for comprehensive answers.
allowed-tools: >-
  mcp__tapps-mcp__tapps_research
  mcp__tapps-mcp__tapps_consult_expert
  mcp__tapps-mcp__tapps_lookup_docs
argument-hint: "[question]"
context: fork
model: claude-sonnet-4-6
---

Research a technical question using TappsMCP:

1. Call `mcp__tapps-mcp__tapps_research` with the question for expert + docs
2. If confidence < 0.7, call `mcp__tapps-mcp__tapps_lookup_docs` for the library
3. If multi-domain, call `mcp__tapps-mcp__tapps_consult_expert` per domain
4. Synthesize findings into a clear, actionable answer
5. Include confidence scores and suggest follow-up research if needed
