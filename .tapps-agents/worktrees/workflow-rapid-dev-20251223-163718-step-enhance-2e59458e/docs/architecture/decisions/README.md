# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting key architectural decisions made in the HomeIQ project.

---

## What are ADRs?

ADRs are documents that capture important architectural decisions along with their context and consequences. They help:

- **Document decisions** for future reference
- **Understand rationale** behind architectural choices
- **Track alternatives** considered
- **Guide future decisions** based on past choices

---

## ADR Format

Each ADR follows this structure:

1. **Status:** Accepted / Proposed / Deprecated
2. **Date:** When the decision was made
3. **Context:** The situation that led to the decision
4. **Decision:** What was decided
5. **Rationale:** Why this decision was made
6. **Consequences:** Positive, negative, and neutral outcomes
7. **Alternatives:** Other options considered
8. **Related Decisions:** Links to other ADRs

---

## Current ADRs

### ADR 001: Hybrid Orchestration Pattern
**Status:** Accepted  
**Date:** January 2025  
**Summary:** Use hybrid pattern (direct calls + orchestrator) for AI services

[View ADR 001](001-hybrid-orchestration-pattern.md)

---

### ADR 002: Hybrid Database Architecture
**Status:** Accepted  
**Date:** January 2025 (Epic 22)  
**Summary:** Use InfluxDB for time-series + SQLite for metadata

[View ADR 002](002-hybrid-database-architecture.md)

---

### ADR 003: Epic 31 Architecture Simplification
**Status:** Accepted  
**Date:** October 2025 (Epic 31)  
**Summary:** Deprecate enrichment-pipeline, move normalization inline

[View ADR 003](003-epic-31-architecture-simplification.md)

---

### ADR 004: RAG Embedded Architecture
**Status:** Accepted  
**Date:** January 2025  
**Summary:** Keep RAG embedded in ai-automation-service (not microservice)

[View ADR 004](004-rag-embedded-architecture.md)

---

## Creating New ADRs

When making a significant architectural decision:

1. **Create new ADR file:** `docs/architecture/decisions/XXX-decision-name.md`
2. **Use template:** Follow the format of existing ADRs
3. **Number sequentially:** Use next available number
4. **Link from README:** Add entry to this file
5. **Update related ADRs:** Link to/from related decisions

---

## ADR Template

```markdown
# ADR XXX: Decision Title

**Status:** Proposed / Accepted / Deprecated  
**Date:** YYYY-MM-DD  
**Context:** Brief context  
**Deciders:** Who made the decision

---

## Context

[Describe the situation that led to this decision]

---

## Decision

[State the decision clearly]

---

## Rationale

[Explain why this decision was made]

---

## Consequences

### Positive
- [Positive outcomes]

### Negative
- [Negative outcomes]

### Neutral
- [Neutral outcomes]

---

## Alternatives Considered

- [Option 1]: [Why rejected]
- [Option 2]: [Why rejected]

---

## Related Decisions

- [Link to related ADRs]

---

**Last Updated:** YYYY-MM-DD
```

---

## Status Definitions

- **Proposed:** Decision is under consideration
- **Accepted:** Decision has been made and implemented
- **Deprecated:** Decision has been superseded or reversed

---

**Last Updated:** December 3, 2025

