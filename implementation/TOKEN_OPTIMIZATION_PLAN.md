# Token Optimization Plan for Injection Context

**Date:** December 2025  
**Goal:** Reduce token usage by 50-60% (5,000-8,000 tokens) while maintaining LLM accuracy  
**Status:** In Progress

## Executive Summary

This plan optimizes the Tier 1 Context Injection system (Epic AI-19) to reduce token usage while preserving all essential information for automation creation. All optimizations follow 2025 patterns and Context7 best practices.

## Current Token Usage

- **Entity Inventory:** ~3000 chars (up to 20 lights with full details)
- **Entity Attributes:** ~2500 chars (duplicate effect lists)
- **Areas:** ~1000 chars (with aliases, icons, labels)
- **Services Summary:** ~3000 chars (full parameter schemas)
- **Helpers/Scenes:** ~2000 chars (with states, entity_ids)
- **Capability Patterns:** ~2000 chars
- **Total:** ~13,500 chars (~3,400 tokens)

## Target Token Usage

- **Optimized Total:** ~5,500-6,500 chars (~1,400-1,600 tokens)
- **Savings:** ~7,000-8,000 chars (~1,800-2,000 tokens, 50-60% reduction)

## Optimization Strategy

### Phase 1: High-Impact Optimizations (Priority 1)

#### 1.1 Eliminate Entity Attributes Duplication
**Current:** Entity Inventory shows effect_list, Entity Attributes also shows effect_list  
**Change:** Merge Entity Attributes into Entity Inventory, remove separate service  
**Token Savings:** ~1,500-2,500 tokens  
**Implementation:**
- Enhance Entity Inventory to include all attribute data
- Make Entity Attributes optional/on-demand
- Update ContextBuilder to skip Entity Attributes in default context

#### 1.2 Simplify Effect/Preset Lists
**Current:** Full lists with all effect names (e.g., 186 effects listed)  
**Change:** Format: `effect_list: 186 effects [Fire, Rainbow, Police, ...]` (count + 3-5 examples)  
**Token Savings:** ~500-1,000 tokens  
**Implementation:**
- Update Entity Inventory to show count + samples
- Limit to 5 examples max
- Use ellipsis for large lists

#### 1.3 Reduce Light Examples
**Current:** Up to 20 lights with full details  
**Change:** 5-8 lights showing unique patterns (one WLED, one Hue, one smart switch, etc.)  
**Token Savings:** ~800-1,200 tokens  
**Implementation:**
- Group lights by type/manufacturer
- Show one example per pattern
- Prioritize lights with unique capabilities

### Phase 2: Medium-Impact Optimizations (Priority 2)

#### 2.1 Simplify Area Formatting
**Current:** `Office (area_id: office, aliases: workspace, study, icon: mdi:desk, labels: home, work)`  
**Change:** `office: Office, kitchen: Kitchen` (just area_id → name mapping)  
**Token Savings:** ~300-500 tokens  
**Implementation:**
- Remove aliases, icons, labels
- Use simple `area_id: name` format
- Remove duplicate mapping section

#### 2.2 Simplify Helpers/Scenes Format
**Current:** `morning_routine (id: input_boolean.morning_routine, entity_id: input_boolean.morning_routine, state: on)`  
**Change:** `input_boolean: morning_routine, night_mode (2)` (just names + count)  
**Token Savings:** ~400-600 tokens  
**Implementation:**
- Remove entity_id, state from helpers
- Show only friendly names and counts
- Simplify scene format

#### 2.3 Simplify Services Summary
**Current:** Full parameter schemas with types, required/optional, constraints, descriptions  
**Change:** `light.turn_on(target: entity_id|area_id|device_id, data: rgb_color, brightness, effect, transition)`  
**Token Savings:** ~500-800 tokens  
**Implementation:**
- Remove verbose descriptions
- Use pipe-separated target options
- List parameter names only (no types/constraints)

### Phase 3: Low-Impact Optimizations (Priority 3)

#### 3.1 Remove Current States
**Current:** `state: on/off` for every entity example  
**Change:** Remove states (can be queried via tools)  
**Token Savings:** ~200-400 tokens  
**Implementation:**
- Remove state from entity examples
- Remove state from helpers/scenes

#### 3.2 Remove Device IDs from Examples
**Current:** `device_id: abc123` in every entity example  
**Change:** Remove device_id (can be queried if needed)  
**Token Savings:** ~200-300 tokens  
**Implementation:**
- Remove device_id from entity examples
- Keep only entity_id and friendly_name

#### 3.3 Remove Aliases/Labels
**Current:** `[aliases: workspace, study]` and `[labels: home, work]` for entities  
**Change:** Remove aliases/labels (can be queried if needed)  
**Token Savings:** ~300-500 tokens  
**Implementation:**
- Remove aliases from entity examples
- Remove labels from entity examples
- Remove aliases from areas

#### 3.4 Consolidate Capability Patterns
**Current:** Separate Capability Patterns section  
**Change:** Merge into Entity Inventory (show patterns per domain)  
**Token Savings:** ~500-800 tokens  
**Implementation:**
- Add capability patterns to domain summaries
- Remove separate Capability Patterns section

#### 3.5 Limit Domain Examples
**Current:** 3-5 examples per domain for all domains  
**Change:** Examples only for critical domains (light, switch, sensor, climate)  
**Token Savings:** ~300-500 tokens  
**Implementation:**
- Show examples only for key domains
- Other domains: just counts

## Implementation Order

1. ✅ **Phase 1.1:** Eliminate Entity Attributes Duplication
2. ✅ **Phase 1.2:** Simplify Effect/Preset Lists
3. ✅ **Phase 1.3:** Reduce Light Examples
4. ✅ **Phase 2.1:** Simplify Area Formatting
5. ✅ **Phase 2.2:** Simplify Helpers/Scenes Format
6. ✅ **Phase 2.3:** Simplify Services Summary
7. ✅ **Phase 3:** Apply all low-impact optimizations

## Quality Preservation

All optimizations maintain essential information:
- Entity IDs and friendly names (for automation targets)
- Domain counts and area breakdowns (for context)
- Service names and basic parameters (for automation creation)
- Capability patterns (for device understanding)

Removed data can be queried via tools if needed:
- Current states (via get_states tool)
- Device IDs (via device queries)
- Aliases/labels (via entity queries)
- Full effect lists (via entity queries)

## Testing Strategy

1. **Token Count Verification:**
   - Measure before/after token counts
   - Verify 50-60% reduction achieved

2. **Quality Testing:**
   - Test automation creation with optimized context
   - Verify LLM can still create accurate automations
   - Compare automation quality before/after

3. **Performance Testing:**
   - Verify context generation still <100ms (with cache)
   - Verify cache hit rates maintained
   - Verify no degradation in response quality

## Success Criteria

- ✅ Token usage reduced by 50-60%
- ✅ All essential information preserved
- ✅ LLM accuracy maintained or improved
- ✅ Context generation <100ms (with cache)
- ✅ No breaking changes to API

## 2025 Patterns Applied

- **String Formatting:** Use f-strings with minimal verbosity
- **Caching:** Maintain existing cache TTLs
- **Error Handling:** Graceful degradation if services unavailable
- **Type Safety:** Maintain type hints throughout
- **Async Patterns:** Keep async/await patterns
- **Performance:** Optimize string concatenation

## Context7 Best Practices

- **String Optimization:** Use efficient string formatting
- **Caching:** Leverage existing cache infrastructure
- **Error Handling:** Graceful fallbacks
- **Type Safety:** Maintain type hints

