# HomeIQ Architecture — index

Entry point to the architecture documentation. Detailed documents live in
[docs/architecture/](architecture/).

## Decision records

1. [ADR: Single Agent Architecture](architecture/adr-single-agent-architecture.md) — one true agent service (`ha-ai-agent-service`); everything else is single-shot LLM use.
2. [ADR: Goal-Loop Operator Pattern](architecture/adr-goal-loop-operator-pattern.md) — how long-running agent sessions operate on the live home: goal loop, readiness gates, background watchers, registry-verified claims (TAP-5990; proven 2026-08-11/12).

## Subsystem references

1. [Domain structure](architecture/domain-structure.md) — the domain/compose layout.
2. [Event flow](architecture/event-flow-architecture.md) — ingestion → enrichment → storage.
3. [AI/agent service classification](architecture/ai-agent-classification.md) — T1 vs T2 LLM use.
4. [Database schema](architecture/database-schema.md) · [InfluxDB schema](architecture/influxdb-schema.md)
5. [ML pipeline](architecture/ml-pipeline.md)
6. [HA init agent design](ha-init-agent-design.md) — founding design; current operational reference is [operations/init-gateway.md](operations/init-gateway.md).
7. [Quick reference](architecture/README_ARCHITECTURE_QUICK_REF.md)
