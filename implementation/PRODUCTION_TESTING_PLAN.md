# Production Testing Plan - Phase 1, 2, 3 Features

**Date:** January 16, 2026  
**Status:** ⏳ **READY TO BEGIN**  
**Service:** `ha-ai-agent-service`  
**Related:** Phase 1, 2, 3 Implementation Complete (January 2, 2025)

---

## Executive Summary

This document outlines the production testing plan for Phase 1, 2, 3 features implemented in the HA AI Agent Service. All 9 recommendations have been implemented and verified. This plan focuses on validating improvements in production with real Home Assistant data.

### Expected Improvements

- **Token Reduction:** 30-50% through filtering/prioritization
- **Accuracy Improvement:** 15-25% through better context relevance
- **Quality Score:** Expected improvement to 75-85/100
- **Total Quality Improvement:** 698 points

---

## Testing Objectives

### Primary Objectives

1. **Validate Token Usage Reduction**
   - Baseline: Measure current token usage before Phase 3 features
   - Target: 30-50% reduction in token usage
   - Method: Compare token counts before/after Phase 3 deployment

2. **Validate Accuracy Improvements**
   - Baseline: Measure current accuracy metrics
   - Target: 15-25% improvement in accuracy
   - Method: Compare automation creation success rates, entity resolution accuracy

3. **Validate Quality Score Improvements**
   - Baseline: Unknown (need to establish)
   - Target: 75-85/100 quality score
   - Method: Code quality reviews, automated scoring

4. **Integration Testing with Real Data**
   - Validate all Phase 1, 2, 3 features work with real Home Assistant data
   - Ensure no regressions in existing functionality
   - Verify performance improvements

---

## Test Environment Setup

### Prerequisites

1. **Production-like Home Assistant Instance**
   - Real device/entity data
   - Real area configurations
   - Real service configurations
   - Production-scale data (100+ devices, 500+ entities)

2. **Monitoring Infrastructure**
   - Token usage tracking (already implemented in `prompt_assembly_service.py`)
   - Response time monitoring
   - Error rate tracking
   - Quality score trending

3. **Test Data Collection**
   - Sample user prompts (20-50 prompts)
   - Expected outcomes for each prompt
   - Baseline metrics (token usage, accuracy, response times)

### Environment Configuration

```yaml
# Test environment variables
HA_AI_AGENT_SERVICE_URL: http://localhost:8025
DATA_API_URL: http://localhost:8006
HOME_ASSISTANT_URL: http://192.168.1.86:8123
HOME_ASSISTANT_TOKEN: <test-token>

# Monitoring
ENABLE_TOKEN_TRACKING: true
ENABLE_PERFORMANCE_MONITORING: true
LOG_LEVEL: INFO
```

---

## Test Phases

### Phase A: Baseline Measurement (Week 1)

**Objective:** Establish baseline metrics before Phase 3 features are enabled

**Activities:**

1. **Token Usage Baseline**
   - Run test suite of 20-50 user prompts
   - Record token counts for each request:
     - System prompt tokens
     - Context tokens
     - History tokens
     - Total tokens
   - Calculate average token usage per request
   - Document token breakdown (system vs context vs history)

2. **Accuracy Baseline**
   - Run test suite of user prompts
   - Measure:
     - Entity resolution accuracy (% correct entity selections)
     - Automation creation success rate
     - User approval rate
     - Error rate (entity not found, invalid service, etc.)
   - Document baseline accuracy metrics

3. **Performance Baseline**
   - Measure response times for each request
   - Calculate average response time
   - Document p50, p95, p99 response times

4. **Quality Score Baseline**
   - Run code quality review on service
   - Document baseline quality scores (if available)

**Tools:**

```bash
# Token tracking is already implemented in prompt_assembly_service.py
# Use chat endpoint metadata to track tokens:
# POST /api/chat
# Response includes: metadata.tokens_used, metadata.token_breakdown

# Manual testing script
python scripts/test_baseline_metrics.py \
  --prompts-file test_data/user_prompts.json \
  --output-file baseline_metrics.json
```

**Deliverables:**

- `baseline_metrics.json` - Baseline token usage, accuracy, performance metrics
- `baseline_report.md` - Baseline measurement report

---

### Phase B: Phase 3 Feature Validation (Week 2)

**Objective:** Validate Phase 3 features (Context Prioritization & Filtering) work correctly

**Activities:**

1. **Feature Verification**
   - Verify `ContextPrioritizationService` is initialized and working
   - Verify `ContextFilteringService` is initialized and working
   - Verify services are integrated into `ContextBuilder`
   - Verify services are called during context building

2. **Functional Testing**
   - Test context prioritization with various user prompts
   - Test context filtering with intent extraction
   - Verify filtered/prioritized context is used in prompts
   - Verify no functionality regressions

3. **Token Usage Validation**
   - Run same test suite as baseline
   - Compare token counts:
     - System prompt tokens (should be similar)
     - Context tokens (should be 30-50% lower)
     - Total tokens (should be 30-50% lower)
   - Document token reduction percentage

**Test Cases:**

```python
# Test case 1: Area-focused prompt
user_prompt = "Turn on the office lights"
# Expected: Context filtered to office area entities only
# Expected: Token reduction in context tokens

# Test case 2: Device-type focused prompt
user_prompt = "Set all lights to red"
# Expected: Context filtered to light entities only
# Expected: Token reduction in context tokens

# Test case 3: Complex prompt with multiple intents
user_prompt = "When motion is detected in the office, turn on the lights and set temperature to 72"
# Expected: Context prioritized by relevance (motion sensors, lights, climate)
# Expected: Token reduction while maintaining accuracy
```

**Tools:**

```bash
# Feature verification script (already exists)
python services/ha-ai-agent-service/scripts/verify_phase_features.py

# Token comparison script
python scripts/compare_token_usage.py \
  --baseline baseline_metrics.json \
  --current current_metrics.json \
  --output comparison_report.json
```

**Deliverables:**

- Feature verification report
- Token usage comparison report
- Functional test results

---

### Phase C: Accuracy Validation (Week 3)

**Objective:** Validate accuracy improvements (15-25% improvement target)

**Activities:**

1. **Entity Resolution Accuracy**
   - Run test suite with entity resolution scenarios
   - Measure:
     - Correct entity selection rate
     - Ambiguity resolution accuracy
     - Entity not found errors
   - Compare to baseline

2. **Automation Creation Accuracy**
   - Run test suite with automation creation prompts
   - Measure:
     - Successful automation creation rate
     - YAML validation success rate
     - User approval rate
   - Compare to baseline

3. **Context Relevance Validation**
   - Analyze context used for each prompt
   - Verify relevant entities/services are included
   - Verify irrelevant context is filtered out
   - Validate prioritization is working correctly

**Test Cases:**

```python
# Accuracy test cases
test_cases = [
    {
        "prompt": "Turn on the office lights",
        "expected_entities": ["light.office_*"],
        "expected_accuracy": "high"
    },
    {
        "prompt": "Set the bedroom temperature to 72",
        "expected_entities": ["climate.bedroom_*"],
        "expected_accuracy": "high"
    },
    # ... more test cases
]
```

**Metrics:**

- Entity Resolution Accuracy: Target 15-25% improvement
- Automation Creation Success Rate: Target 15-25% improvement
- User Approval Rate: Monitor for improvements

**Deliverables:**

- Accuracy validation report
- Comparison to baseline metrics
- Context relevance analysis

---

### Phase D: Performance & Quality Validation (Week 4)

**Objective:** Validate performance improvements and quality scores

**Activities:**

1. **Performance Testing**
   - Measure response times with Phase 3 features
   - Compare to baseline
   - Validate no performance regressions
   - Monitor for performance improvements (faster context building)

2. **Quality Score Validation**
   - Run code quality review
   - Validate quality score meets target (75-85/100)
   - Review quality metrics:
     - Complexity
     - Security
     - Maintainability
     - Test coverage
     - Performance

3. **Long-term Monitoring**
   - Set up continuous monitoring
   - Track metrics over time (1-2 weeks)
   - Identify any degradation or improvements

**Tools:**

```bash
# Code quality review
python -m tapps_agents.cli reviewer review services/ha-ai-agent-service/src/services/

# Quality score
python -m tapps_agents.cli reviewer score services/ha-ai-agent-service/src/services/context_prioritization_service.py
python -m tapps_agents.cli reviewer score services/ha-ai-agent-service/src/services/context_filtering_service.py

# Performance testing
python scripts/performance_test.py \
  --prompts-file test_data/user_prompts.json \
  --iterations 100 \
  --output performance_report.json
```

**Deliverables:**

- Performance validation report
- Quality score validation report
- Long-term monitoring setup

---

## Monitoring & Metrics

### Key Metrics to Track

1. **Token Usage**
   - Average tokens per request
   - Token breakdown (system, context, history)
   - Token reduction percentage
   - Target: 30-50% reduction

2. **Accuracy Metrics**
   - Entity resolution accuracy
   - Automation creation success rate
   - User approval rate
   - Error rate
   - Target: 15-25% improvement

3. **Performance Metrics**
   - Average response time
   - p50, p95, p99 response times
   - Context building time
   - API call latency

4. **Quality Metrics**
   - Overall quality score (target: 75-85/100)
   - Complexity score
   - Security score
   - Maintainability score
   - Test coverage

### Monitoring Dashboard

Create monitoring dashboard with:

- Real-time token usage trends
- Accuracy metrics over time
- Performance metrics
- Error rates
- Quality scores

### Alerting

Set up alerts for:

- Token usage above baseline (regression detection)
- Accuracy below baseline (regression detection)
- Response times above threshold (performance degradation)
- Error rates above threshold (quality issues)

---

## Test Data

### User Prompts Test Suite

Create test suite with 20-50 user prompts covering:

1. **Simple Prompts** (10 prompts)
   - Single entity, single action
   - Example: "Turn on the office lights"

2. **Area-focused Prompts** (10 prompts)
   - Multiple entities in an area
   - Example: "Turn on all bedroom lights"

3. **Device-type Focused Prompts** (10 prompts)
   - Multiple entities of same type
   - Example: "Set all lights to red"

4. **Complex Prompts** (10 prompts)
   - Multiple entities, conditions, actions
   - Example: "When motion is detected in the office, turn on lights and set temperature to 72"

5. **Edge Cases** (10 prompts)
   - Ambiguous entities
   - Missing entities
   - Invalid services
   - Complex conditions

### Expected Outcomes

For each prompt, document:

- Expected entities to be selected
- Expected automation structure
- Expected token usage range
- Expected accuracy level

---

## Success Criteria

### Phase A: Baseline Measurement

- ✅ Baseline metrics collected for all key metrics
- ✅ Test suite executed successfully
- ✅ Baseline report documented

### Phase B: Phase 3 Feature Validation

- ✅ Phase 3 features verified working
- ✅ Token reduction of 30-50% achieved (or documented deviation)
- ✅ No functionality regressions

### Phase C: Accuracy Validation

- ✅ Accuracy improvement of 15-25% achieved (or documented deviation)
- ✅ Entity resolution accuracy improved
- ✅ Automation creation success rate improved

### Phase D: Performance & Quality Validation

- ✅ Quality score of 75-85/100 achieved
- ✅ No performance regressions
- ✅ Monitoring infrastructure set up

### Overall Success Criteria

- ✅ All Phase 1, 2, 3 features working in production
- ✅ Token usage reduced by 30-50%
- ✅ Accuracy improved by 15-25%
- ✅ Quality score meets target (75-85/100)
- ✅ No regressions in existing functionality
- ✅ Monitoring infrastructure operational

---

## Rollback Plan

If production testing reveals issues:

1. **Immediate Rollback**
   - Disable Phase 3 features (prioritization/filtering)
   - Revert to baseline configuration
   - Monitor for stability

2. **Partial Rollback**
   - Disable specific Phase 3 features causing issues
   - Keep Phase 1, 2 features enabled
   - Monitor and fix issues

3. **Fix and Re-test**
   - Fix identified issues
   - Re-run testing phases
   - Validate fixes

---

## Timeline

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Phase A: Baseline Measurement | 1 week | TBD | TBD | ⏳ Pending |
| Phase B: Phase 3 Feature Validation | 1 week | TBD | TBD | ⏳ Pending |
| Phase C: Accuracy Validation | 1 week | TBD | TBD | ⏳ Pending |
| Phase D: Performance & Quality Validation | 1 week | TBD | TBD | ⏳ Pending |
| **Total** | **4 weeks** | | | |

---

## Next Steps

### Immediate Actions

1. **Set Up Test Environment**
   - Configure production-like Home Assistant instance
   - Set up monitoring infrastructure
   - Prepare test data (user prompts test suite)

2. **Create Test Scripts**
   - Baseline measurement script
   - Token comparison script
   - Accuracy validation script
   - Performance testing script

3. **Begin Phase A: Baseline Measurement**
   - Execute test suite
   - Collect baseline metrics
   - Document baseline report

### Follow-up Actions

1. **Execute Testing Phases**
   - Phase A → Phase B → Phase C → Phase D
   - Document results at each phase
   - Adjust plan based on findings

2. **Set Up Continuous Monitoring**
   - Implement monitoring dashboard
   - Set up alerting
   - Document monitoring procedures

3. **Fine-tune Based on Results**
   - Adjust scoring algorithms based on real-world usage
   - Optimize filtering/prioritization logic
   - Improve accuracy based on findings

---

## Related Documentation

- `implementation/PHASE_1_2_3_FINAL_STATUS.md` - Implementation status
- `implementation/PHASE_1_2_3_VERIFICATION_COMPLETE.md` - Verification results
- `implementation/COMPREHENSIVE_STATUS_SUMMARY.md` - Overall status summary
- `services/ha-ai-agent-service/src/services/context_prioritization_service.py` - Phase 3.1 implementation
- `services/ha-ai-agent-service/src/services/context_filtering_service.py` - Phase 3.2 implementation
- `services/ha-ai-agent-service/src/services/prompt_assembly_service.py` - Token tracking implementation

---

**Status:** ⏳ **READY TO BEGIN**  
**Last Updated:** January 16, 2026  
**Next Review:** After Phase A completion
