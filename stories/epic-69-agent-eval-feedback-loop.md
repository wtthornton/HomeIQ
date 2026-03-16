# Epic 69: Agent Evaluation — Adaptive Model Routing & Feedback Loop

<!-- docsmcp:start:metadata -->
**Status:** Proposed
**Priority:** P2 - Medium
**Estimated LOE:** ~2 weeks (1 developer)
**Dependencies:** Epic 66 (classification), Agent Evaluation epics (complete: foundation, built-in evaluators, agent configs, observability)

<!-- docsmcp:end:metadata -->

---

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

We are doing this so that the 4 epics of agent evaluation infrastructure (evaluation framework, built-in evaluators, agent-specific configs, observability) start earning their keep by feeding evaluation scores back into runtime decisions — enabling adaptive model selection, surfacing eval degradation as operational alerts, and creating a closed loop where poor agent performance triggers automatic investigation rather than silently degrading user experience.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:goal -->
## Goal

Close the feedback loop between the agent evaluation framework and runtime behavior by implementing adaptive model routing (route requests to gpt-5.2-codex vs gpt-5-mini based on eval scores and request complexity), eval-driven alerting in the health dashboard, and automated eval regression investigation.

**Tech Stack:** homeiq, Python >=3.11

<!-- docsmcp:end:goal -->

<!-- docsmcp:start:motivation -->
## Motivation

HomeIQ has a sophisticated agent evaluation framework (13 evaluators, SessionTracer, LLMJudge, InfluxDB score storage, health-dashboard tab) built across 4 completed epics. However, evaluation results currently sit in dashboards without influencing runtime behavior. The system uses static model assignments (gpt-5.2-codex for ha-ai-agent, gpt-5-mini for planning/query) regardless of eval performance. When agent quality degrades, there is no automated response — someone has to notice the dashboard and investigate manually. This epic turns passive observability into active quality management.

<!-- docsmcp:end:motivation -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Request complexity classifier routes complex queries to gpt-5.2-codex and simple queries to gpt-5-mini based on configurable rules
- [ ] Model routing decisions are logged and correlated with subsequent eval scores
- [ ] Eval score degradation (>10% drop over 24h rolling window) triggers automated alert in health-dashboard
- [ ] Alert includes: affected agent and evaluation dimension and score trend and sample failing traces
- [ ] Cost savings tracked: monthly spend reduction from routing simple queries to cheaper model
- [ ] Routing rules can be overridden per-agent via admin-api configuration
- [ ] Fallback: if routing logic fails the system uses the default (expensive) model — never degrades to cheaper model on error

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:stories -->
## Stories

### 69.1 -- Request Complexity Classifier

**Points:** 3

Build a lightweight classifier that scores incoming requests on complexity (low/medium/high) based on: token count, entity count, tool count hint (does the request likely need multiple tools?), conversation depth. Use rule-based heuristics first (no ML). Route: low→gpt-5-mini, medium→gpt-5-mini with fallback, high→gpt-5.2-codex. Add to ha-ai-agent-service request pipeline before OpenAI call.

**Tasks:**
- [ ] Implement request complexity classifier
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Request Complexity Classifier is implemented, tests pass, and documentation is updated.

---

### 69.2 -- Adaptive Model Router

**Points:** 3

Implement a ModelRouter that selects the OpenAI model per-request based on complexity classification and recent eval scores. If gpt-5-mini eval scores for a request category drop below threshold (configurable, default 70/100), auto-upgrade that category to gpt-5.2-codex. Store routing decisions in InfluxDB for correlation analysis. Expose current routing table via GET /api/model-routing.

**Tasks:**
- [ ] Implement adaptive model router
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Adaptive Model Router is implemented, tests pass, and documentation is updated.

---

### 69.3 -- Eval-Routing Correlation Analysis

**Points:** 2

Build a correlation pipeline that joins routing decisions with evaluation outcomes. Track: eval score by model, eval score by complexity tier, cost per successful interaction. Surface in health-dashboard Agent Evaluation tab as a model comparison chart. Identify if gpt-5-mini is underperforming on specific request categories.

**Tasks:**
- [ ] Implement eval-routing correlation analysis
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Eval-Routing Correlation Analysis is implemented, tests pass, and documentation is updated.

---

### 69.4 -- Eval Degradation Alerting

**Points:** 2

Add automated alerting when agent eval scores degrade. Trigger: rolling 24h average drops >10% vs 7-day baseline, or any eval dimension drops below floor (50/100). Alert payload: agent name, dimension, current vs baseline score, sample trace IDs. Route to health-dashboard notification panel and optional webhook (Slack/email).

**Tasks:**
- [ ] Implement eval degradation alerting
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Eval Degradation Alerting is implemented, tests pass, and documentation is updated.

---

### 69.5 -- Automated Regression Investigation

**Points:** 3

When an eval alert fires, automatically collect investigation context: 5 lowest-scoring traces from the alert window, common patterns in failing traces (shared entities, similar intents, same error types), model/routing changes in the alert window. Package as an investigation report accessible from the alert in health-dashboard.

**Tasks:**
- [ ] Implement automated regression investigation
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Automated Regression Investigation is implemented, tests pass, and documentation is updated.

---

### 69.6 -- Cost Tracking & Reporting

**Points:** 2

Track OpenAI API costs per model per agent per day. Compare: baseline cost (all requests to expensive model) vs adaptive cost (routed). Surface monthly savings estimate in health-dashboard. Alert if cost spikes unexpectedly (>50% above 7-day average).

**Tasks:**
- [ ] Implement cost tracking & reporting
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Cost Tracking & Reporting is implemented, tests pass, and documentation is updated.

---

### 69.7 -- Admin Configuration & Safety

**Points:** 1

Expose routing configuration via admin-api: per-agent model overrides, complexity thresholds, eval score floors, alert thresholds. Include a 'lock to model' option that disables adaptive routing for a specific agent (useful during incidents). All config changes logged in audit trail.

**Tasks:**
- [ ] Implement admin configuration & safety
- [ ] Write unit tests
- [ ] Update documentation

**Definition of Done:** Admin Configuration & Safety is implemented, tests pass, and documentation is updated.

---

<!-- docsmcp:end:stories -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Agent eval infrastructure is complete: SessionTracer middleware and 13 evaluators and InfluxDB storage and health-dashboard tab
- ha-ai-agent-service OpenAI client is in domains/automation-core/ha-ai-agent-service/src/services/openai_client.py
- Current model config in src/config.py — model selection is currently static
- InfluxDB already stores eval scores — add routing decisions to same bucket for correlation
- gpt-5.2-codex costs ~3x gpt-5-mini — routing simple queries saves significant monthly spend
- health-dashboard at domains/core-platform/health-dashboard already has Agent Evaluation tab from completed epic

**Project Structure:** 0 packages, 0 modules, 0 public APIs

### Expert Recommendations

- **Security Expert** (71%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (64%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:non-goals -->
## Out of Scope / Future Considerations

- Training a custom model — this is about routing between existing OpenAI models
- Replacing the evaluation framework — building on top of completed eval epics
- Real-time model switching mid-conversation — routing is per-request at conversation start
- Automated model fine-tuning based on eval scores

<!-- docsmcp:end:non-goals -->

<!-- docsmcp:start:success-metrics -->
## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| All 7 acceptance criteria met | 0/7 | 7/7 | Checklist review |
| All 7 stories completed | 0/7 | 7/7 | Sprint board |

<!-- docsmcp:end:success-metrics -->

<!-- docsmcp:start:implementation-order -->
## Implementation Order

1. Story 69.1: Request Complexity Classifier
2. Story 69.2: Adaptive Model Router
3. Story 69.3: Eval-Routing Correlation Analysis
4. Story 69.4: Eval Degradation Alerting
5. Story 69.5: Automated Regression Investigation
6. Story 69.6: Cost Tracking & Reporting
7. Story 69.7: Admin Configuration & Safety

<!-- docsmcp:end:implementation-order -->

<!-- docsmcp:start:risk-assessment -->
## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Routing simple queries to cheaper model could degrade user experience if classifier is wrong — mitigated by conservative classification and eval-score-based auto-upgrade | Medium | Medium | Warning: Mitigation required - no automated recommendation available |
| Eval score correlation may have confounding variables (time of day and user behavior) — mitigated by per-category tracking | Medium | Medium | Warning: Mitigation required - no automated recommendation available |
| Cost tracking requires OpenAI usage API access — may need API key with billing scope | Medium | Medium | Warning: Mitigation required - no automated recommendation available |

**Expert-Identified Risks:**

- **Security Expert**: *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*

<!-- docsmcp:end:risk-assessment -->

<!-- docsmcp:start:files-affected -->
## Files Affected

| File | Story | Action |
|---|---|---|
| Files will be determined during story refinement | - | - |

<!-- docsmcp:end:files-affected -->
