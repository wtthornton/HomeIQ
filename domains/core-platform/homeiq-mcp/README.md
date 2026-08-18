# homeiq-mcp

The `homeiq` MCP server (epic TAP-5282): one typed, read-only tool surface over
HomeIQ's observed Home Assistant data, for AgentForge genes and the HA
integration.

- **Contract:** `docs/mcp/homeiq-mcp-tools.schema.json` (normative) +
  `docs/mcp/homeiq-mcp-tool-catalogue.md`. `list_tools` serves those schemas
  verbatim; TAP-5297 contract tests pin them.
- **Transport:** streamable-HTTP at `/mcp` (JSON responses, stateless) and
  stdio (`HOMEIQ_MCP_TRANSPORT=stdio`). `/health` reports readiness plus every
  backing's status; 503 when data-api is unreachable.
- **Auth:** `Authorization: Bearer <token>` on `/mcp`. `HOMEIQ_MCP_READ_TOKENS`
  → read scope; `HOMEIQ_MCP_WRITE_TOKENS` → read + mutate. Mutating tools (none
  in v1) additionally need the per-tool grant `HOMEIQ_MCP_ALLOW_WRITES`.
- **Errors:** every tool failure is MCP tool-error content with a `code` from
  `backing_unavailable | invalid_input | not_found | truncated_upstream |
  contract_violation` — never an upstream traceback.
- **Budgets:** responses are truncated to each tool's `max_response_bytes` with
  `truncated: true` + `hint` naming the parameter to narrow.

## Configuration

| Variable | Required | Meaning |
|---|---|---|
| `HOMEIQ_MCP_READ_TOKENS` | http | comma-separated read tokens |
| `HOMEIQ_MCP_WRITE_TOKENS` | no | comma-separated read+mutate tokens (must not overlap read) |
| `HOMEIQ_MCP_ALLOW_WRITES` | no | comma-separated mutating tool names granted (v1: none) |
| `DATA_API_URL`, `API_KEY` | yes | data-api base URL and its bearer key |
| `PATTERN_SERVICE_URL` | no | ai-pattern-service base URL (patterns/synergies tools) |
| `DEVICE_INTELLIGENCE_URL` | no | device-intelligence-service base URL (health/failure tools) |
| `HOMEIQ_MCP_ALLOWED_HOSTS` | no | extra `Host` values accepted (DNS-rebinding guard); `homeiq-mcp` + localhost always allowed |
| `HOMEIQ_MCP_TRANSPORT` | no | `http` (default) or `stdio` |
| `HOMEIQ_MCP_PORT` | no | default 8050 |

The server refuses to start (exit 2, names the missing variables) on incomplete config.

## Run tests

```bash
cd domains/core-platform/homeiq-mcp
../../../.venv/bin/python -m pytest -q
```
