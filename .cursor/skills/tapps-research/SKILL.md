---
name: tapps-research
description: >-
  Research a technical question using domain experts and library documentation.
  Combines expert consultation with docs lookup for comprehensive answers.
mcp_tools:
  - tapps_research
  - tapps_consult_expert
  - tapps_lookup_docs
---

Research a technical question using TappsMCP:

1. Call `tapps_research` with the question to get expert + docs in one call
2. If confidence is below 0.7, call `tapps_lookup_docs` directly for the relevant library
3. If the question spans multiple domains, call `tapps_consult_expert` per domain
4. Synthesize findings into a clear, actionable answer
5. Include confidence scores and suggest follow-up research if needed
