# Epic 66: AI/Agent Service Classification & Architecture Documentation

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P1 - High
**Estimated LOE:** ~2-3 days (1 developer)
**Dependencies:** None
**Blocks:** Epic 67, Epic 68, Epic 69

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that every developer, operator, and AI agent working on HomeIQ has a single source of truth classifying which of the 51 services use LLMs, which are true autonomous agents, which run ML inference, and which are pure data/rule-based — eliminating confusion caused by misleading service names like 'proactive-agent-service' and 'ai-pattern-service' that contain 'AI' or 'agent' but are not actually agents.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Create a living architecture document that classifies all 51 HomeIQ services into four tiers (True Agent, LLM-Powered Wrapper, ML Inference, Non-AI) with evidence-based rationale, and establish an ADR explaining why the platform intentionally limits true agent behavior to a single service.

**Tech Stack:** homeiq, Python >=3.11

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

The project has 51 deployed services, many with 'AI' or 'agent' in their names, but only 1 true agent. This causes confusion during onboarding, architecture reviews, and when planning AI improvements. No single document answers 'which services actually use LLMs?' — that knowledge is scattered across model inventories, service-groups docs, and tribal knowledge. Additionally, there is no recorded architectural decision explaining why only ha-ai-agent-service is a true agent.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] A docs/architecture/ai-agent-classification.md exists classifying all 51 services into 4 tiers with evidence
- [ ] An ADR (docs/architecture/adr-single-agent-architecture.md) explains the intentional single-agent design
- [ ] The classification doc is cross-referenced from service-groups.md and TECH_STACK.md
- [ ] Each service entry includes: tier label and LLM/model/framework used (if any) and agent pattern evidence (if any)
- [ ] The document includes a visual summary table and a decision tree for classifying new services
- [ ] health-dashboard shows AI tier badges on the service inventory page

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 66.1 -- Service Classification Audit & Tier Document

**Points:** 3

Create docs/architecture/ai-agent-classification.md with 4-tier classification (True Agent, LLM Wrapper, ML Inference, Non-AI) for all 51 services. Include evidence table with columns: Service, Domain, Port, Tier, LLM/Model, Agent Loop, Tool Use, Key File.

**Tasks:**
- [ ] Implement service classification audit & tier document
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Service Classification Audit & Tier Document is implemented, tests pass, and documentation is updated.

---

### 66.2 -- Architecture Decision Record — Single Agent Design

**Points:** 2

Write ADR documenting why HomeIQ intentionally limits true agent behavior to ha-ai-agent-service. Cover: context (cost, latency, testability, predictability), decision, consequences, and conditions under which the decision should be revisited.

**Tasks:**
- [ ] Implement architecture decision record — single agent design
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Architecture Decision Record — Single Agent Design is implemented, tests pass, and documentation is updated.

---

### 66.3 -- New Service Classification Decision Tree

**Points:** 1

Add a decision tree flowchart (Mermaid) to the classification doc that helps developers classify new services: Does it call an LLM? → Does it iterate on LLM output? → Does it invoke tools autonomously? → Assign tier.

**Tasks:**
- [ ] Implement new service classification decision tree
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** New Service Classification Decision Tree is implemented, tests pass, and documentation is updated.

---

### 66.4 -- Cross-Reference Integration

**Points:** 1

Update service-groups.md, TECH_STACK.md, and LLM_ML_MODELS_02222026.md to link to the new classification doc. Add AI tier column to existing service tables where applicable.

**Tasks:**
- [ ] Implement cross-reference integration
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Cross-Reference Integration is implemented, tests pass, and documentation is updated.

---

### 66.5 -- Health Dashboard AI Tier Badges

**Points:** 2

Add AI tier badges (True Agent, LLM, ML, Non-AI) to the service inventory cards in health-dashboard. Source tier data from a static JSON manifest generated from the classification doc.

**Tasks:**
- [ ] Implement health dashboard ai tier badges
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Health Dashboard AI Tier Badges is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Classification tiers: True Agent (iterative LLM + tool use)
- LLM Wrapper (single-shot LLM calls)
- ML Inference (trained models without LLMs)
- Non-AI (pure data/rules)
- Evidence must reference specific source files (e.g. chat_endpoints.py:151 for agent loop)
- Mermaid decision tree for new service classification
- Static JSON manifest for health-dashboard badges avoids runtime dependency

**Project Structure:** 0 packages, 0 modules, 0 public APIs

### Expert Recommendations

- **Security Expert** (72%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (66%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Renaming existing services to match their actual tier
- Changing any service behavior — this is documentation only
- Evaluating whether services should be upgraded to higher tiers (covered in Epics 67-69)

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 6 acceptance criteria met | 0/6 | 6/6 | Checklist review |
| All 5 stories completed | 0/5 | 5/5 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 66.1: Service Classification Audit & Tier Document
2. Story 66.2: Architecture Decision Record — Single Agent Design
3. Story 66.3: New Service Classification Decision Tree
4. Story 66.4: Cross-Reference Integration
5. Story 66.5: Health Dashboard AI Tier Badges

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| No risks identified | - | - | Consider adding risks during planning |

**Expert-Identified Risks:**

- **Security Expert**: *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| Files will be determined during story refinement | - | - |

<!-- docsmcp:end:files-affected -->
