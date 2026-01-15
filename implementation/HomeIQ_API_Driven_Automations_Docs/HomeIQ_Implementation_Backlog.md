# HomeIQ Implementation Backlog: API-Driven Automations (v1)

**Last updated:** 2026-01-15

This backlog is organized to deliver value quickly while preserving the strict hybrid boundary.

---

## Epic A — HA Adapter (REST + WebSocket)

### A1. REST client (must)
- Auth header support (Bearer token)
- Request/response logging with secret redaction
- Timeout + retry (transient only)

### A2. WebSocket client (must)
- Connect + authenticate
- Resubscribe on reconnect
- Heartbeat/ping + jittered backoff
- Metrics: disconnect count, reconnect latency

### A3. HA instance identity (should)
- Collect HA version and instance ID (where available)
- Record in capability graph metadata

---

## Epic B — Capability Graph (v1)

### B1. Entity inventory (must)
- Boot: GET /api/states
- Normalize: domain, device_class, supported_features, availability
- Build entity->area/device maps (when available via metadata)

### B2. Service inventory (must)
- Discover service availability and fields per domain/service
- Cache with TTL and reconcile changes on HA restart

### B3. Incremental updates (must)
- Subscribe to `state_changed` via WS
- Update cache + derived signals (occupancy, daylight, etc.)

### B4. Drift detection (should)
- Detect removed entities/services and invalidate affected specs

---

## Epic C — Automation Spec + Registry

### C1. Schema (must)
- JSON Schema + validation library
- Semver enforcement

### C2. Registry (must)
- Store specs by home
- Track deployed versions and history
- Immutable artifact storage (hash-based)

### C3. CLI/tools (should)
- Lint + validate locally
- Render execution plan (dry run)

---

## Epic D — Validator + Planner

### D1. Target resolution (must)
- Resolve area/device_class selectors to concrete entities
- Produce plan with resolved targets

### D2. Service compatibility (must)
- Service exists, required fields present
- Supported feature checks for key domains (light, climate, lock)

### D3. Policy gates (must)
- Risk levels + quiet hours
- Manual override TTLs
- Confirmation workflow hooks (high risk)

### D4. Live preflight (should)
- Check availability/online before execution (optional per risk)

---

## Epic E — Executor

### E1. Deterministic execution (must)
- Idempotency keys
- Sequential execution default
- Bounded parallelism option

### E2. Retry + breaker (must)
- Exponential backoff for transient
- Circuit breaker per HA instance

### E3. Confirmation (should)
- Observe expected state change via WS
- Timeout behavior per risk class

---

## Epic F — Observability + Explainability

### F1. Structured logs (must)
- Correlation IDs across trigger/plan/execute/confirm

### F2. Metrics (must)
- action success/failure
- latency
- WS health
- breaker trips

### F3. Explainability (“Why”) (should)
- Store decision factors and selected targets
- User-facing explanation templates

---

## Epic G — Rollout + Safety

### G1. Canary rollout (should)
- staged deploys by home cohort
- health gate checks

### G2. Rollback (should)
- last-known-good pointer
- auto-rollback on error budget breach

### G3. Kill switch (must)
- global pause for non-safety automations

---

## Epic H — Security

### H1. Secrets management (must)
- Encrypt tokens at rest
- Redact in logs

### H2. Webhook hardening (optional)
- HMAC signing, nonce, timestamp, replay protection
- Rate limiting rules

---

## Definition of Done (v1)
- Execute at least 10 real automations in a live home with no generated YAML.
- All executions fully traced and explainable.
- Strict hybrid boundary documented and enforced in reviews.
