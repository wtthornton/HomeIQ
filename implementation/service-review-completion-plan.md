# Service Review Completion Plan

**Date:** 2026-01-16  
**Status:** Main entry points reviewed for 40+ services

## Phase 1: Review Complete ✅

**Completed:** Main entry point (main.py/main.tsx/main.ts) reviews for 40+ services

## Phase 2: Fix Files Below Thresholds ⏳

### Files Requiring Immediate Fixes (Overall < 70 or Maintainability < 7.5)

#### Critical (Overall < 70):
1. `services/activity-recognition/src/data/sensor_loader.py` - 65.8/100 overall, 6.0/10 maintainability
2. `services/ai-automation-service-new/src/main.py` - 62.5/100 overall, 5.09/10 maintainability  
3. `services/ha-ai-agent-service/src/main.py` - 64.95/100 overall, 7.18/10 maintainability

#### Maintainability Issues (< 7.5/10):
1. `services/activity-recognition/src/main.py` - 6.6/10 maintainability
2. `services/activity-recognition/src/models/activity_classifier.py` - 6.7/10 maintainability
3. `services/api-automation-edge/src/main.py` - 6.89/10 maintainability
4. `services/health-dashboard/src/main.tsx` - 5.50/10 maintainability
5. `services/ai-pattern-service/src/main.py` - 5.38/10 maintainability
6. `services/ai-query-service/src/main.py` - 6.2/10 maintainability
7. `services/blueprint-index/src/main.py` - 6.7/10 maintainability
8. `services/blueprint-suggestion-service/src/main.py` - 6.7/10 maintainability
9. `services/carbon-intensity-service/src/main.py` - 7.25/10 maintainability (slightly below 7.5)
10. `services/device-context-classifier/src/main.py` - 6.7/10 maintainability
11. `services/device-database-client/src/main.py` - 6.7/10 maintainability
12. `services/device-health-monitor/src/main.py` - 6.7/10 maintainability
13. `services/device-recommender/src/main.py` - 6.7/10 maintainability
14. `services/device-setup-assistant/src/main.py` - 6.7/10 maintainability
15. `services/energy-forecasting/src/main.py` - 6.57/10 maintainability
16. `services/proactive-agent-service/src/main.py` - 6.57/10 maintainability
17. `services/rag-service/src/main.py` - 6.54/10 maintainability
18. `services/rule-recommendation-ml/src/main.py` - 6.58/10 maintainability

## Phase 3: Apply Fixes

For each file requiring fixes, use:
```bash
python -m tapps_agents.cli improver improve-quality <file_path>
```

Then re-review to verify fixes meet thresholds:
```bash
python -m tapps_agents.cli reviewer review <file_path> --format json
```

## Phase 4: Review Additional Source Files

For services with failing main files, review other source files:
- `services/activity-recognition/src/` - Already reviewed all files
- `services/ai-automation-service-new/src/` - Review service files
- `services/ha-ai-agent-service/src/` - Review service files
- Other services with maintainability issues - Review service files

## Phase 5: Documentation

Document recurring patterns:
1. **Device Services Pattern**: All device-* services have 6.7/10 maintainability (consistent code structure)
2. **Missing Type Hints**: Most common issue across all services
3. **Test Coverage**: Universal gap (0-50% vs target 80%)

## Progress Tracking

- ✅ **40+ services main files reviewed**
- ⏳ **18 files identified for fixes**
- ⏳ **Fixes to be applied**
- ⏳ **Re-verification pending**
