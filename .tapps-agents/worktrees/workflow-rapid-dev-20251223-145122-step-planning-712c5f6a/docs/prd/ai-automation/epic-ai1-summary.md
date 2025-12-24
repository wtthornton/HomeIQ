# Epic AI-1: AI Automation Suggestion System - Story Summary

**Epic ID:** Epic-AI-1  
**Epic Goal:** Enable users to discover and deploy Home Assistant automations based on AI-detected patterns and natural language requests, with safety validation and simple rollback  
**Phase:** Phase 1 MVP (Simplified for Single Home)  
**Timeline:** 4-5 weeks  
**Total Effort:** 173-201 hours

---

## Story List

| Story | Title | Effort | Priority | Dependencies |
|-------|-------|--------|----------|--------------|
| **AI1.1** | MQTT Connection Configuration | 2-3h | Critical | None |
| **AI1.2** | AI Service Backend Foundation | 6-8h | Critical | AI1.1 |
| **AI1.3** | Data API Integration | 8-10h | Critical | AI1.2 |
| **AI1.4** | Pattern Detection - Time-of-Day | 10-12h | High | AI1.3 |
| **AI1.5** | Pattern Detection - Co-Occurrence | 8-10h | High | AI1.4 |
| **AI1.6** | Pattern Detection - Anomaly | 8-10h | High | AI1.5 |
| **AI1.7** | LLM Integration - OpenAI | 8-10h | Critical | AI1.6 |
| **AI1.8** | Suggestion Generation Pipeline | 10-12h | Critical | AI1.7 |
| **AI1.9** | Daily Batch Scheduler | 6-8h | Critical | AI1.8 |
| **AI1.10** | REST API - Suggestion Management | 8-10h | High | AI1.9 |
| **AI1.11** | REST API - Home Assistant Integration | 10-12h | Critical | AI1.10 |
| **AI1.12** | MQTT Event Publishing | 6-8h | Medium | AI1.11 |
| **AI1.13** | Frontend - Project Setup | 8-10h | High | None |
| **AI1.14** | Frontend - Suggestions Tab | 12-14h | Critical | AI1.13, AI1.10 |
| **AI1.15** | Frontend - Patterns Tab | 10-12h | Medium | AI1.14 |
| **AI1.16** | Frontend - Automations Tab | 10-12h | Medium | AI1.15 |
| **AI1.17** | Frontend - Insights Tab | 10-12h | Medium | AI1.16 |
| **AI1.18** | E2E Testing & Documentation | 12-14h | High | AI1.17 |
| **AI1.19** | Safety Validation Engine | 8-10h | Critical | AI1.11 |
| **AI1.20** | Simple Rollback (Simplified) | 2-3h | High | AI1.11, AI1.19 |
| **AI1.21** | Natural Language Request Generation | 10-12h | High | AI1.7, AI1.8 |
| **AI1.22** | Simple Dashboard Integration (Simplified) | 2-3h | Critical | AI1.10, AI1.19, AI1.20 |
| **AI1.23** | Frontend Data Display and UX Fixes | 6-8h | High | AI1.14, AI1.15, AI1.16, AI1.17 |

**Total Stories:** 23  
**Total Effort:** 179-209 hours (Simplified for single-home use case)

**Note:** AI1.20 and AI1.22 simplified to reduce complexity for single-home deployment. AI1.21 kept full version as it provides highest value.

---

## Critical Path

```
Backend Critical Path:
AI1.1 → AI1.2 → AI1.3 → AI1.4 → AI1.7 → AI1.8 → AI1.9 → AI1.10 → AI1.11

Frontend Critical Path:
AI1.13 → AI1.14

Integration Point: AI1.10 (API) enables AI1.14 (Frontend)
```

**Timeline:** 5-7 weeks for sequential execution, 4-5 weeks with parallel backend/frontend work

---

## Sequencing Strategy

### Week 1: Foundation (30-39 hours)
- **AI1.1:** MQTT Connection Configuration (2-3h) *uses existing HA broker*
- **AI1.2:** Backend Foundation (6-8h)
- **AI1.3:** Data API Integration (8-10h)
- **AI1.4:** Time-of-Day Patterns (10-12h)
- **AI1.13:** Frontend Setup (8-10h) *parallel*

**Deliverable:** Backend foundation + pattern detection started

### Week 2: Pattern Detection + LLM (42-52 hours)
- **AI1.5:** Co-Occurrence Patterns (8-10h)
- **AI1.6:** Anomaly Detection (8-10h)
- **AI1.7:** OpenAI Integration (8-10h)
- **AI1.8:** Suggestion Pipeline (10-12h)
- **AI1.9:** Batch Scheduler (6-8h)

**Deliverable:** End-to-end pattern detection → suggestions working

### Week 3: API + Frontend Core (44-56 hours)
- **AI1.10:** Suggestion Management API (8-10h)
- **AI1.11:** HA Integration API (10-12h)
- **AI1.12:** MQTT Publishing (6-8h)
- **AI1.14:** Suggestions Tab (12-14h) *parallel after AI1.10*
- **AI1.15:** Patterns Tab (10-12h)

**Deliverable:** Full API + primary frontend tab

### Week 4: Final Frontend + Testing (42-50 hours)
- **AI1.16:** Automations Tab (10-12h)
- **AI1.17:** Insights Tab (10-12h)
- **AI1.18:** E2E Testing & Docs (12-14h)

**Deliverable:** Complete MVP ready for production

---

## Parallel Development Opportunities

**Backend Team:**
- Stories AI1.1-AI1.12 (can work independently)

**Frontend Team:**
- AI1.13 (start immediately)
- AI1.14-AI1.17 (after AI1.10 API ready)

**Timeline Optimization:** 3-4 weeks with 2 developers (1 backend, 1 frontend)

---

## Success Criteria

### Functional Success:
- ✅ Detects patterns from 30 days of HA data
- ✅ Generates 5-10 suggestions weekly
- ✅ Users can approve/reject via UI
- ✅ Approved automations deploy to HA successfully
- ✅ MQTT communication bidirectional

### Performance Success:
- ✅ Daily analysis completes in <10 minutes
- ✅ Memory usage <1GB peak
- ✅ API responses <500ms
- ✅ Frontend loads <2 seconds

### Quality Success:
- ✅ >60% user acceptance rate (approved vs rejected)
- ✅ >95% deployment success rate (valid YAML)
- ✅ >70% code coverage
- ✅ Zero critical bugs

### Cost Success:
- ✅ API costs <$10/month
- ✅ Hardware: Single NUC sufficient
- ✅ No performance impact on existing services

---

## Risk Mitigation

| Risk | Mitigation | Story |
|------|-----------|-------|
| Pattern quality low | Start with high confidence threshold (70%) | AI1.4-1.6 |
| LLM generates invalid YAML | YAML validation before deployment | AI1.11 |
| API costs spike | Track usage, alert at $5 | AI1.7, AI1.8, AI1.21 |
| Memory exceeds 1GB | Sample data, optimize algorithms | AI1.4-1.6 |
| HA API rejects automation | Comprehensive error handling | AI1.11 |
| Dangerous automation deployed | Multi-layer safety validation | AI1.19 |
| Automation misbehaves | Audit trail and rollback capability | AI1.20 |
| User overwhelmed by separate app | Unified dashboard UX | AI1.22 |

---

## Definition of Done (Epic Level)

### All Stories Complete:
- [ ] All 22 stories marked as "Done"
- [ ] All acceptance criteria met
- [ ] All integration verifications passed

### System Functional:
- [ ] Daily analysis runs automatically
- [ ] Suggestions generated and displayed
- [ ] Approve workflow works end-to-end
- [ ] Automations deploy to HA successfully

### Quality Gates:
- [ ] Unit tests: >80% coverage
- [ ] Integration tests: All passing
- [ ] E2E tests: Critical flows passing
- [ ] Performance: All NFRs met

### Documentation:
- [ ] README complete
- [ ] API docs accessible
- [ ] Troubleshooting guide created
- [ ] Architecture documented

### Deployment:
- [ ] Docker Compose configuration complete
- [ ] All services start successfully
- [ ] Resource usage within limits
- [ ] No conflicts with existing services

---

## Post-MVP: Phase 2+ Planning

**Phase 2 (Month 3-4):**
- Weekly patterns (statsmodels)
- Day-of-week awareness
- 10-20 suggestions per week

**Phase 3 (Month 6+):**
- Prophet for seasonal patterns
- Composite patterns
- Local LLM option

See PRD Section 8.3 for details

---

## Story Files

All story files located in: `docs/stories/`

- `story-ai1-1-infrastructure-mqtt-integration.md`
- `story-ai1-2-backend-foundation.md`
- `story-ai1-3-data-api-integration.md`
- `story-ai1-4-pattern-detection-time-of-day.md`
- `story-ai1-5-pattern-detection-co-occurrence.md`
- `story-ai1-6-pattern-detection-anomaly.md`
- `story-ai1-7-llm-integration-openai.md`
- `story-ai1-8-suggestion-generation-pipeline.md`
- `story-ai1-9-daily-batch-scheduler.md`
- `story-ai1-10-rest-api-suggestion-management.md`
- `story-ai1-11-rest-api-ha-integration.md`
- `story-ai1-12-mqtt-event-publishing.md`
- `story-ai1-13-frontend-project-setup.md`
- `story-ai1-14-frontend-suggestions-tab.md`
- `story-ai1-15-frontend-patterns-tab.md`
- `story-ai1-16-frontend-automations-tab.md`
- `story-ai1-17-frontend-insights-tab.md`
- `story-ai1-18-e2e-testing-documentation.md`
- `story-ai1-19-safety-validation-engine.md`
- `story-ai1-20-simple-rollback.md` (simplified)
- `story-ai1-21-natural-language-request-generation.md`
- `story-ai1-22-simple-dashboard-integration.md` (simplified)
- `story-ai1-23-frontend-data-display-fix.md`

---

**Epic Status:** Ready for Development (Enhanced)  
**Created:** 2025-10-15  
**Updated:** 2025-10-18

