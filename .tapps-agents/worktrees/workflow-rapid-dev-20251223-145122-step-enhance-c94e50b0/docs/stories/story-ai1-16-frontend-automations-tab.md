# Story AI1.16: Frontend - Current Automations Tab

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.16  
**Priority:** Medium  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.15 (Patterns tab)

---

## User Story

**As a** user  
**I want** to view existing HA automations and AI-deployed ones  
**so that** I can manage my automations

---

## Acceptance Criteria

1. ✅ Displays user-created + AI-deployed automations
2. ✅ Badges distinguish source (👤 User / 🤖 AI)
3. ✅ Search by automation name functional
4. ✅ Filter by source and status
5. ✅ Detail modal shows automation YAML
6. ✅ Can remove AI-deployed automations
7. ✅ Shows execution count and success rate
8. ✅ "View in HA" opens HA UI in new tab

---

## Technical Implementation Notes

**Reference:** health-dashboard/src/components/tabs/DevicesTab.tsx  
**Pattern:** Search + filter + list view  
**Components:** AutomationsTab, AutomationListItem, AutomationDetailModal

**API Calls:** GET HA /api/config/automation/config, DELETE /api/deploy/{id}

**Estimated Effort:** 10-12 hours

---

**Story Status:** Not Started  
**Created:** 2025-10-15

