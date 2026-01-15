# HomeIQ PRD: REST / Webhook / API-Driven Automations (Strict, Boring, Scalable)

**Status:** Draft v1  
**Last updated:** 2026-01-15  
**Owner:** HomeIQ Platform  
**Audience:** Engineering, SRE/DevOps, Security, Product  
**Target HA compatibility:** Home Assistant Core (2025+) REST + WebSocket APIs, optional webhook triggers

---

## 1. Executive summary

HomeIQ will transition from generating Home Assistant automation YAML to an **API-driven automation engine**.

- **HomeIQ is the source of truth**: intent, policy, validation, rollout, audit, observability.
- **Home Assistant (HA) is the runtime**: device abstraction + service execution + state/event source.
- **Strict hybrid boundary** keeps HA “dumb”: minimal static configuration only; no per-device/generated YAML.

This reduces brittleness across heterogeneous device graphs, enables typed validation against live capabilities, and supports production-grade rollout patterns (versioning, canary, rollback).

---

## 2. Problem statement

The current YAML creation/validation path is not scalable for HomeIQ because:

1. **Heterogeneous device/service surface**: entities, services, fields, and attributes differ by integration, firmware, configuration.
2. **Validation is reactive**: issues are often discovered only at HA load/runtime.
3. **YAML is not a contract**: limited typing, poor simulation, and fragile generation by LLMs.
4. **Maintenance scales poorly**: per-device/per-integration exceptions grow unbounded.

We need a strategy where HomeIQ can **discover**, **validate**, and **execute** automations using HA’s supported APIs:
- REST API (`/api/...`) for commands and snapshots
- WebSocket API (`/api/websocket`) for real-time event/state streams
- Optional webhook triggers (`/api/webhook/<id>`) for tightly controlled inbound triggers (treated as secrets)

---

## 3. Goals / Non-goals

### Goals (v1)
- Eliminate **generated per-device YAML** as the primary automation mechanism.
- Introduce **HomeIQ Automation Spec** (typed) as the single source of truth.
- Build a **capability graph** per home from HA metadata and live state.
- Provide **static + live preflight validation** before deployment and before execution.
- Execute via HA **REST service calls** and observe via **WebSocket** subscriptions.
- Add production features: **versioning, canary, rollback, kill switch, audit logs, metrics/tracing**.
- Maintain a **strict hybrid boundary** to control complexity.

### Non-goals (v1)
- Replacing HA as the integration/device platform.
- Building a new visual rules editor (may come later).
- Requiring AppDaemon everywhere as the core mechanism.
- Supporting arbitrary third-party automation engines without boundaries.

---

## 4. Users & scenarios

### Personas
- **HomeIQ Power user / builder**: wants robust, debuggable, scalable automation.
- **Installer / MSP**: wants repeatable deployments across many homes.
- **Home occupant**: wants reliability, safety, and “why did this happen?” explanations.

### Must-support scenarios (v1)
- Lighting scenes based on occupancy + time/daylight
- HVAC adjustments with comfort/quiet-hours constraints
- Safety workflows: leak → valve off → notify → confirm
- Manual override: user action pauses automation for N minutes
- Energy-aware throttling (load shedding) based on policy inputs

---

## 5. Product requirements

### 5.1 Single Source of Truth (SSOT)
- All automations exist as **HomeIQ Automation Specs** (typed, versioned).
- HA contains only minimal static configuration to connect and expose devices.
- Each home has an **active spec set** with semantic versioning and history.

### 5.2 Strict hybrid boundary (“Correct Hybrid”)
**Allowed in HA**
- Standard HA integrations and entity configuration
- A dedicated HomeIQ user and token for API access
- Optional: small number of *static* webhook-trigger automations for inbound triggers (plumbing only)

**Not allowed in HA**
- Generated automation YAML per home/device
- Per-integration branching logic
- Business logic distributed across helpers/scripts/templating
- Multiple competing automation systems (unless explicitly isolated and optional)

### 5.3 Capability Graph & Validation
HomeIQ Edge must build and maintain:
- Entities: `entity_id`, domain, device class, supported features, area/device mapping
- Services: domain/service definitions + schema/fields (as exposed by HA)
- Devices/areas relationships
- Health metadata: availability, recent state, last_updated

Validation requirements:
- **Schema validation** (spec is well-formed)
- **Target resolution** (capability → concrete entity set)
- **Service compatibility** (service exists, required fields, supported features)
- **Policy checks** (risk gates, time windows, presence requirements)
- **Dry-run plan** (action list with resolved targets and payloads)
- **Live preflight** (optional): entity exists/available now; avoids “ghost entity” failures

### 5.4 Execution engine requirements
- Deterministic executor with:
  - Idempotency keys per action
  - Retry w/ exponential backoff for transient failures
  - Circuit breaker per HA instance
  - Debounce/coalesce bursty triggers (motion storms)
- Ordering:
  - Sequential by default; bounded parallelism for independent actions
- Confirmation:
  - Observe state change confirmation via WebSocket where feasible
- Failure handling:
  - classify transient vs permanent; mark specs invalid on permanent incompatibility
  - optional compensating rollback actions
  - emit structured incident telemetry

### 5.5 Security requirements
- Dedicated HA user for HomeIQ; principle of least privilege.
- Long-lived access tokens stored encrypted; rotation supported.
- Webhooks:
  - Treat webhook IDs as secrets; never log full URLs.
  - Do not use webhooks for high-risk actions without additional safeguards (signed payload + nonce + timestamp).
- Network:
  - default local-only operation; remote optional via hardened exposure.
- Audit:
  - Every action recorded with correlation ID, actor, reason, and spec version.

### 5.6 Observability & explainability
**Metrics**
- action success/failure by home, domain, automation id, version
- decision latency (trigger → execute)
- WS disconnect rates, reconnect success, retries, breaker trips

**Logs/traces**
- Correlation IDs across: trigger → validation → plan → service call → confirmation
- “Why” output:
  - triggers matched
  - conditions/policies applied
  - action plan executed
  - overrides respected

### 5.7 Rollout, versioning, and rollback
- Versioned specs with immutable history.
- Rollout manager supports:
  - Canary by home (and optionally by automation group)
  - Staged rollout with health gates
  - Global kill switch (“pause non-safety automations”)
- Rollback:
  - one-click rollback to last-known-good
  - auto-rollback on error budget breach

---

## 6. Non-functional requirements (NFRs)
- Reliability: graceful degradation when HA offline; queue or drop with policy
- Performance: handle bursty event rates; bounded CPU/mem for edge agent
- Scalability: homes with 1k–10k entities; incremental capability refresh
- Maintainability: strict boundary prevents logic sprawl
- Security: token hygiene, secret management, auditability

---

## 7. Phased delivery plan

### Phase 0 — Foundations
- HA Adapter (REST auth + WebSocket connect)
- Capability Graph v1
- Automation Spec schema + registry (versioning)

### Phase 1 — Validate + Execute (low-risk domains)
- Validation pipeline v1
- Deterministic executor v1 (idempotency/retry/breaker)
- Support: lights, media, climate (no locks/alarms)

### Phase 2 — Observability + Rollout
- Metrics/tracing, “why” explanations
- Canary + rollback + kill switch
- Shadow mode (decide but don’t act)

### Phase 3 — High-risk domains & safety
- Policy gating + confirmations
- Optional signed payloads for webhook triggers
- Support: locks, alarms, shutoff valves with guardrails

---

## 8. Acceptance criteria (v1)
- HomeIQ can build a capability graph from HA and keep it fresh.
- A spec can be validated and executed without generating HA YAML.
- Execution uses REST service calls; telemetry uses WebSocket subscriptions.
- Observability shows end-to-end correlation for each execution.
- Strict hybrid boundary is enforceable and documented.

---

## 9. References (official docs)
- Home Assistant REST API (Developer Docs): https://developers.home-assistant.io/docs/api/rest/
- Home Assistant WebSocket API (Developer Docs): https://developers.home-assistant.io/docs/api/websocket/
- Home Assistant Authentication (user docs): https://www.home-assistant.io/docs/authentication/
- Home Assistant Auth API (Developer Docs): https://developers.home-assistant.io/docs/auth_api/
- Webhook trigger + security notes: https://www.home-assistant.io/docs/automation/trigger/
- API integration overview: https://www.home-assistant.io/integrations/api/
