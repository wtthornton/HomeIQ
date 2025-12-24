# Story AI1.17: Frontend - Insights Dashboard Tab

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.17  
**Priority:** Medium  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.16 (Automations tab)

---

## User Story

**As a** user  
**I want** to see system status and AI service health  
**so that** I know everything is working correctly

---

## Acceptance Criteria

1. ✅ Shows last analysis timestamp and duration
2. ✅ Displays suggestion stats (generated/approved/deployed/rejected)
3. ✅ Shows API cost this month vs budget ($10)
4. ✅ System status cards (green/yellow/red for Data API, MQTT, LLM API)
5. ✅ Acceptance rate chart (approved vs rejected over time)
6. ✅ Pattern detection trends (last 7 days)
7. ✅ Service health indicators
8. ✅ Auto-refresh every 30 seconds (optional toggle)

---

## Technical Implementation Notes

**Reference:** health-dashboard/src/components/tabs/OverviewTab.tsx  
**Pattern:** Hero card + system status cards  
**Components:** InsightsTab, SystemStatusHero, MetricCard

**Reuse:** CoreSystemCard, PerformanceSparkline from health-dashboard

**Estimated Effort:** 10-12 hours

---

**Story Status:** Not Started  
**Created:** 2025-10-15

