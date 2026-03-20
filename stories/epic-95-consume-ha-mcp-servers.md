# Epic 95: Consume HA MCP Servers

**Priority:** P1 Foundational — Modernization (demoted from P0: current client works)
**Effort:** 1–2 weeks (7 stories, 28 points)
**Sprint:** 43–44
**Depends on:** None
**Origin:** Sapphire Review — 2026 Research Recommendation #1

## Problem Statement

HomeIQ has a custom `HomeAssistantClient` (250+ lines, aiohttp + websockets) that manually implements HA REST API and WebSocket API calls for:
- Area registry (WebSocket)
- Entity registry (WebSocket)
- Device registry (WebSocket)
- Service listing (REST)
- State fetching (REST)
- Helpers listing (REST + WebSocket fallback)
- Scenes listing (REST)

This client must be maintained every time HA changes its API. The HA ecosystem is standardizing on MCP (Model Context Protocol) — HA 2025.2+ has native MCP support, and mature third-party MCP servers (`ha-mcp`, `hass-mcp`) already expose all these capabilities as standardized MCP tools.

Additionally, HomeIQ has 10 data-collector services (weather-api, calendar-service, air-quality, etc.) that each implement custom API clients. Some of these could be replaced by off-the-shelf MCP servers.

**Benefits of consuming MCP:**
1. Upstream improvements for free — new HA features, entity types, API changes handled by MCP server maintainers
2. Standardized protocol — same client code works with any MCP server
3. Reduced maintenance — delete custom client code, adopt maintained open-source
4. Composability — easily add new MCP servers for additional capabilities

## Approach

Phased adoption:
1. Add MCP client library to `ha-ai-agent-service`
2. Create an `MCPHAClient` that wraps MCP tool calls with the same interface as `HomeAssistantClient`
3. Run both clients in parallel (shadow mode) to verify parity
4. Switch over once parity is confirmed
5. Audit data-collector services for MCP server replacements

---

## Story 95.1: MCP Client Infrastructure

**Points:** 3 | **Type:** Feature
**Goal:** Add MCP client capability to `ha-ai-agent-service`

### Tasks

- [ ] **95.1.1** Add `mcp` Python SDK to `requirements.txt`: `mcp>=1.0.0`
- [ ] **95.1.2** Create `src/clients/mcp_client.py` — generic MCP client wrapper:
  ```python
  class MCPClient:
      """Generic MCP client for connecting to MCP servers."""

      def __init__(self, server_url: str, transport: str = "sse"):
          ...

      async def connect(self) -> None:
          """Establish connection to MCP server."""
          ...

      async def call_tool(self, name: str, arguments: dict) -> Any:
          """Call an MCP tool and return the result."""
          ...

      async def list_tools(self) -> list[dict]:
          """List available tools on the server."""
          ...

      async def close(self) -> None:
          """Close connection."""
          ...
  ```
- [ ] **95.1.3** Add MCP server configuration to `Settings`:
  ```python
  ha_mcp_server_url: str = "http://localhost:8500"  # or stdio transport
  ha_mcp_transport: str = "sse"  # sse or stdio
  use_mcp_client: bool = False   # Feature flag
  ```
- [ ] **95.1.4** Add health check: verify MCP server connectivity at startup
- [ ] **95.1.5** Add unit tests for MCPClient (mock MCP server)

### Acceptance Criteria

- [ ] `MCPClient` connects to an MCP server via SSE transport
- [ ] `call_tool()` sends requests and returns parsed results
- [ ] Health check logs MCP server version and available tools
- [ ] Feature flag `use_mcp_client` defaults to `False`

---

## Story 95.2: Evaluate & Select HA MCP Server

**Points:** 2 | **Type:** Research
**Goal:** Choose the best HA MCP server for HomeIQ's needs

### Tasks

- [ ] **95.2.1** Evaluate `ha-mcp` (aids2/ha-mcp):
  - Tools provided (entity control, state queries, service calls, area/device registry)
  - Transport support (stdio, SSE)
  - Docker deployment options
  - Active maintenance and community
- [ ] **95.2.2** Evaluate `hass-mcp` and `HA_MCP`:
  - Same criteria as above
  - Compare tool coverage against HomeIQ's `HomeAssistantClient` methods
- [ ] **95.2.3** Evaluate HA's native MCP integration (2025.2+):
  - Built-in vs third-party
  - Available tools and coverage
- [ ] **95.2.4** Create comparison matrix:
  ```
  | Feature              | ha-mcp | hass-mcp | HA Native | HomeIQ Needs |
  |----------------------|--------|----------|-----------|--------------|
  | Area registry        |   ?    |    ?     |     ?     |     ✅       |
  | Entity registry      |   ?    |    ?     |     ?     |     ✅       |
  | Device registry      |   ?    |    ?     |     ?     |     ✅       |
  | State fetching       |   ?    |    ?     |     ?     |     ✅       |
  | Service listing      |   ?    |    ?     |     ?     |     ✅       |
  | Service calling      |   ?    |    ?     |     ?     |     ✅       |
  | Automation CRUD      |   ?    |    ?     |     ?     |     ✅       |
  | Helpers/scenes       |   ?    |    ?     |     ?     |     ✅       |
  | Docker support       |   ?    |    ?     |     ?     |     ✅       |
  | SSE transport        |   ?    |    ?     |     ?     |     ✅       |
  ```
- [ ] **95.2.5** Write decision doc: `docs/adr/ADR-MCP-SERVER-SELECTION.md`

### Acceptance Criteria

- [ ] Comparison matrix is complete with actual tested coverage
- [ ] Selected MCP server covers ≥90% of `HomeAssistantClient` methods
- [ ] Decision document records rationale and any gap-fill needed

---

## Story 95.3: Implement MCPHAClient Adapter

**Points:** 5 | **Type:** Feature
**Goal:** `MCPHAClient` wraps MCP tool calls with the same interface as `HomeAssistantClient`

### Tasks

- [ ] **95.3.1** Create `src/clients/mcp_ha_client.py`:
  ```python
  class MCPHAClient:
      """
      Home Assistant client via MCP protocol.
      Drop-in replacement for HomeAssistantClient.
      """

      def __init__(self, mcp_client: MCPClient):
          self.mcp = mcp_client

      async def get_area_registry(self) -> list[dict[str, Any]]:
          """Fetch areas via MCP tool call."""
          result = await self.mcp.call_tool("get_areas", {})
          return self._normalize_areas(result)

      async def get_states(self) -> list[dict[str, Any]]:
          ...

      async def get_services(self) -> dict[str, Any]:
          ...

      async def get_entity_registry(self) -> list[dict[str, Any]]:
          ...

      async def get_device_registry(self) -> list[dict[str, Any]]:
          ...

      async def get_helpers(self) -> list[dict[str, Any]]:
          ...

      async def get_scenes(self) -> list[dict[str, Any]]:
          ...
  ```
- [ ] **95.3.2** Add normalization methods to convert MCP tool output format to match `HomeAssistantClient` return format (data shape compatibility)
- [ ] **95.3.3** Implement all 7 methods that `EnhancedContextBuilder` and other services call on `HomeAssistantClient`
- [ ] **95.3.4** Add protocol/ABC `HAClientProtocol` that both `HomeAssistantClient` and `MCPHAClient` implement (type safety)
- [ ] **95.3.5** Add unit tests comparing `MCPHAClient` output shape against `HomeAssistantClient` output shape

### Acceptance Criteria

- [ ] `MCPHAClient` implements all methods `HomeAssistantClient` has
- [ ] Return types match (same dict structure, same key names)
- [ ] Both clients implement `HAClientProtocol` ABC

---

## Story 95.4: Shadow Mode — Run Both Clients in Parallel

**Points:** 5 | **Type:** Testing
**Goal:** Run MCP client alongside direct client to verify output parity before switching

### Tasks

- [ ] **95.4.1** Create `src/clients/ha_client_shadow.py`:
  ```python
  class ShadowHAClient:
      """Runs both HA clients and compares results."""

      def __init__(self, primary: HomeAssistantClient, shadow: MCPHAClient):
          ...

      async def get_area_registry(self) -> list[dict]:
          primary_result = await self.primary.get_area_registry()
          try:
              shadow_result = await self.shadow.get_area_registry()
              self._compare("get_area_registry", primary_result, shadow_result)
          except Exception as e:
              logger.warning(f"MCP shadow failed: {e}")
          return primary_result  # Always return primary
  ```
- [ ] **95.4.2** `_compare()` logs diff summary: missing keys, extra keys, value mismatches (structured log, not noisy)
- [ ] **95.4.3** Add shadow mode activation: `use_mcp_client: "shadow"` (vs `False` or `True`)
- [ ] **95.4.4** Wire into `EnhancedContextBuilder` — when shadow mode, use `ShadowHAClient`
- [ ] **95.4.5** Add metrics: track parity percentage per method over time
- [ ] **95.4.6** Run shadow mode against live HA instance, collect parity report

### Acceptance Criteria

- [ ] Shadow mode runs without affecting primary response
- [ ] Comparison logs show per-method parity percentage
- [ ] No performance degradation (shadow calls are fire-and-forget or have short timeout)
- [ ] Parity report shows ≥95% match before proceeding to switchover

---

## Story 95.5: Switch to MCP Client

**Points:** 3 | **Type:** Feature
**Goal:** `use_mcp_client: true` makes `MCPHAClient` the primary HA communication layer

### Tasks

- [ ] **95.5.1** Update client factory in service initialization:
  ```python
  if settings.use_mcp_client == "true":
      ha_client = MCPHAClient(mcp_client)
  elif settings.use_mcp_client == "shadow":
      ha_client = ShadowHAClient(direct_client, MCPHAClient(mcp_client))
  else:
      ha_client = HomeAssistantClient(...)
  ```
- [ ] **95.5.2** Update `EnhancedContextBuilder`, `ha_tools.py`, and any other consumers to accept `HAClientProtocol` (not concrete class)
- [ ] **95.5.3** Keep `HomeAssistantClient` as fallback — if MCP server is unreachable, fall back to direct client (circuit breaker pattern)
- [ ] **95.5.4** Update health check: report MCP server status
- [ ] **95.5.5** Add integration tests: full context build using MCP client produces valid entity context

### Acceptance Criteria

- [ ] `use_mcp_client: true` → all HA calls go through MCP
- [ ] MCP server down → automatic fallback to direct client with warning
- [ ] Full automation creation pipeline works end-to-end with MCP client

---

## Story 95.6: Deploy MCP Server in Docker Stack

**Points:** 5 | **Type:** Infrastructure
**Goal:** Selected HA MCP server runs as a container in HomeIQ's Docker stack

### Tasks

- [ ] **95.6.1** Add MCP server to `domains/automation-core/compose.yml`:
  ```yaml
  ha-mcp-server:
    image: <selected-mcp-server-image>
    environment:
      - HOME_ASSISTANT_URL=${HOME_ASSISTANT_URL}
      - HOME_ASSISTANT_TOKEN=${HOME_ASSISTANT_TOKEN}
    ports:
      - "8500:8500"
    networks:
      - homeiq-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8500/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
  ```
- [ ] **95.6.2** If no Docker image exists, create a minimal Dockerfile wrapping the MCP server
- [ ] **95.6.3** Update `start-stack.sh` and `domain.sh` to include MCP server in automation-core domain
- [ ] **95.6.4** Add MCP server health check to health-dashboard
- [ ] **95.6.5** Document port assignment in TECH_STACK.md (port 8500 or next available)
- [ ] **95.6.6** Add MCP server to `.github/workflows/test-live-ai.yml` Docker stack

### Acceptance Criteria

- [ ] MCP server starts with `domain.sh start automation-core`
- [ ] MCP server is healthy and responds to tool calls
- [ ] ha-ai-agent-service can reach MCP server on internal Docker network
- [ ] Health dashboard shows MCP server status

---

## Story 95.7: Audit Data Collectors for MCP Replacement

**Points:** 5 | **Type:** Research
**Goal:** Identify which data-collector services could be replaced by MCP servers

### Tasks

- [ ] **95.7.1** Inventory current data-collector services and their API sources:
  ```
  | Service               | External API           | MCP Server Available? | Replace? |
  |-----------------------|------------------------|----------------------|----------|
  | weather-api           | OpenWeatherMap / NWS   |        ?             |    ?     |
  | calendar-service      | Google Calendar API    |        ?             |    ?     |
  | air-quality           | AirNow / PurpleAir     |        ?             |    ?     |
  | carbon-intensity      | WattTime / Electricitymap |     ?             |    ?     |
  | electricity-pricing   | Octopus / utility APIs |        ?             |    ?     |
  | sports-api            | ESPN / TheSportsDB     |        ?             |    ?     |
  | smart-meter-service   | Smart meter local API  |        ?             |    ?     |
  ```
- [ ] **95.7.2** Search MCP server registries and GitHub for matching MCP servers
- [ ] **95.7.3** Evaluate each candidate: data coverage, reliability, maintenance status
- [ ] **95.7.4** Write recommendation doc: which services to replace, which to keep, migration plan
- [ ] **95.7.5** File follow-up epics for approved replacements

### Acceptance Criteria

- [ ] Complete inventory with MCP server availability for each data collector
- [ ] Recommendation doc with clear keep/replace/evaluate verdict per service
- [ ] Follow-up epics filed for any approved MCP replacements

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| MCP server doesn't cover all HA APIs | Shadow mode verifies parity before switch; gap-fill methods in MCPHAClient |
| MCP server maintenance abandoned | Keep `HomeAssistantClient` as fallback; circuit breaker auto-switches |
| MCP protocol version changes | Pin `mcp` SDK version; MCP spec is stable (1.0+) |
| Added latency (MCP → HA vs direct → HA) | Benchmark in shadow mode; MCP server runs on same Docker network |
| Data format mismatches | Normalization layer in `MCPHAClient` handles format translation |
