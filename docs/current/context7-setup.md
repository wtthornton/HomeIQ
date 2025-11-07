# Context7 Integration Checklist

> **Last updated:** November 7, 2025  
> **Purpose:** Ensure this repo always follows Context7 MCP best practices so coding agents automatically pull fresh library docs.

## 1. MCP Server Configuration

Context7 must be available to every agent session. We ship a ready-to-edit MCP config at `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "YOUR_CONTEXT7_API_KEY"
      }
    }
  }
}
```

**Action items**

1. Generate an API key in the Context7 console.  
2. Replace `YOUR_CONTEXT7_API_KEY` in `.cursor/mcp.json`, or set it at runtime (e.g. `export CONTEXT7_API_KEY=...` and let your editor inject it).  
3. Restart the editor/agent so the new connection is picked up.

## 2. Auto-Invoke Rule

Copy the recommended rule from the Context7 README into your active agent ruleset (e.g. `.cursor/rules/context7.mdc`):

```
Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. Use resolve-library-id followed by get-library-docs
without waiting for the user to ask.
```

This keeps agents from skipping the MCP lookup.

## 3. Library Mapping

Add a `context7.json` to new libraries so Context7 knows how to crawl them. Minimum example:

```json
{
  "$schema": "https://context7.com/schema/context7.json",
  "projectTitle": "AI Automation Service",
  "description": "LLM-driven Home Assistant automations",
  "folders": ["docs", "services"],
  "excludeFolders": ["implementation", "tmp"],
  "rules": [
    "Use direct InfluxDB writes for event storage",
    "Never reference enrichment-pipeline (deprecated in Epic 31)"
  ]
}
```

Commit this alongside new docs so Context7 stays in sync.

## 4. Local Development (Optional)

If you need an offline copy or want to test new documentation before publishing:

```bash
npx -y @upstash/context7-mcp --api-key "$CONTEXT7_API_KEY"
```

Point your MCP config to the local process (`command` + `args` variant from the upstream README).

## 5. CI Safety Check

Add a lightweight CI job that fails when `.cursor/mcp.json` is missing an API key placeholder or when `context7.json` is absent for libraries flagged in the docs. This prevents regressions.

---

Keeping these items current guarantees the agents always have access to fresh Context7 documentation and follow auto-invocation rules by default. Update this checklist whenever Context7 best practices change.

