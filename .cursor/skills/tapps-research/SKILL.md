---
name: tapps-research
description: >-
  Look up library documentation and run open-ended / latest web research
  for the technologies used in this project. Use when writing code that uses
  an external library, when you need API reference, or when the question is
  time-sensitive / not covered by Context7 docs.
mcp_tools:
  - tapps_research
  - tapps_lookup_docs
---

Research using TappsMCP's unified front door (ADR-0030):

1. Prefer `tapps_research`:
   - Library/API: pass `library=` (and optional `topic=`) or `route="docs"`
   - Open-ended / latest: pass `query=` (auto-routes to brain `web_research`)
   - Single URL scrape: pass `url=` (brain `research_fetch`)
2. For a known library name only, `tapps_lookup_docs` is fine (doc-only).
3. If the brain path returns `degraded=true` / `success=false`, report the structured error — do not invent Exa/Firecrawl keys locally.
4. Synthesize findings into a clear, actionable answer with code examples when docs content is present.
5. Suggest follow-up lookups if additional coverage is needed
