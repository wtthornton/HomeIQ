# Deduplication Call Tree Analysis
**Created:** 2025-11-04
**Purpose:** Trace the call flow to understand why deduplication is not executing

## 📋 Call Tree: POST /api/v1/ask-ai/query

```
1. POST /api/v1/ask-ai/query
   └─► process_natural_language_query() [line 2625]
       │
       ├─► extract_entities_with_ha(query) [line 2641]
       │   └─► Returns List[Dict] of entities
       │
       └─► generate_suggestions_from_query(query, entities, user_id) [line 2644]
           │
           ├─► Step 1: Entity Resolution [lines 2346-2463]
           │   ├─► Initialize HomeAssistantClient [lines 2355-2358]
           │   ├─► Initialize EntityValidator [lines 2364-2368]
           │   ├─► Extract location/domain from query [lines 2371-2374]
           │   ├─► Get available entities [lines 2377-2386]
           │   ├─► Expand group entities [lines 2388-2393]
           │   └─► Enrich entities comprehensively [lines 2423-2456]
           │       └─► Returns enriched_data Dict
           │
           ├─► Step 2: Build Unified Prompt [lines 2465-2471]
           │   └─► unified_builder.build_query_prompt()
           │
           ├─► Step 3: Generate Suggestions with OpenAI [lines 2478-2490]
           │   └─► openai_client.generate_with_unified_prompt()
           │       └─► Returns suggestions_data (already parsed JSON)
           │
           └─► Step 4: Process Suggestions [lines 2492-2611]
               ├─► parsed = suggestions_data [line 2503]
               ├─► 🔍 NEW DEBUG LOG: "Processing N suggestions" [line 2504]
               │
               └─► FOR EACH suggestion in parsed: [line 2505]
                   │
                   ├─► Get devices_involved [line 2508]
                   ├─► 🔍 NEW DEBUG LOG: "devices_involved BEFORE processing" [line 2510]
                   │
                   ├─► 🔄 PRE-CONSOLIDATION [lines 2512-2522]
                   │   ├─► IF devices_involved is not empty
                   │   ├─► Call _pre_consolidate_device_names() [line 2515]
                   │   └─► Log if devices removed [lines 2517-2521]
                   │
                   ├─► 🔄 DEDUPLICATION [lines 2524-2539]
                   │   ├─► Create seen set & deduplicated list [lines 2525-2526]
                   │   ├─► FOR EACH device in devices_involved [line 2527]
                   │   │   └─► Add to deduplicated if not in seen [lines 2528-2530]
                   │   └─► IF len(deduplicated) < len(devices_involved) [line 2532]
                   │       └─► Log deduplicated count [lines 2533-2537]
                   │
                   ├─► Entity Mapping [lines 2541-2567]
                   │   └─► map_devices_to_entities() → validated_entities
                   │
                   ├─► Consolidation (post-mapping) [lines 2558-2565]
                   │   └─► consolidate_devices_involved()
                   │
                   └─► Build suggestion dict [lines 2569-2582]
                       └─► devices_involved: devices_involved (should be deduplicated)
```

## 🔍 Expected Log Sequence

When a suggestion is generated, we should see:

```
1. "🔍 [CONSOLIDATION DEBUG] Processing N suggestions from OpenAI"
2. "🔍 [CONSOLIDATION DEBUG] Suggestion 1: devices_involved BEFORE processing = [...]"
3. IF pre-consolidation removes items:
   "🔄 Pre-consolidated devices for suggestion 1: X → Y (removed Z generic/redundant terms)"
4. IF deduplication removes items:
   "🔄 Deduplicated devices for suggestion 1: X → Y (removed Z exact duplicates)"
5. "✅ Mapped X/Y devices to VERIFIED entities for suggestion 1"
6. IF consolidation removes items:
   "🔄 Optimized devices_involved for suggestion 1: X → Y entries (Z redundant entries removed)"
```

## ❌ Actual Logs (Missing Deduplication)

From latest test, we see:
```
❌ NO "Pre-consolidated" messages
❌ NO "Deduplicated" messages
❌ NO "[CONSOLIDATION DEBUG]" messages
```

## 🔬 Root Cause Analysis

### Hypothesis 1: Code Not Deployed ✅ CONFIRMED
- Code is present in container (verified via `docker exec sed`)
- BUT logs show no execution
- **Likely Cause:** Docker cache preventing rebuild

### Hypothesis 2: Code Path Not Executed
- IF `parsed` is empty, loop never runs
- IF `devices_involved` is empty, deduplication skipped (line 2514 check)
- **Need to verify:** Are suggestions actually being generated?

### Hypothesis 3: Logging Not Flushing
- Python logging may be buffered
- **Need to verify:** Add flush or use stderr

## 🛠️ Diagnostic Commands

```powershell
# 1. Verify code is in container
docker exec ai-automation-service grep -A 5 "CONSOLIDATION DEBUG" /app/src/api/ask_ai_router.py

# 2. Check if route is being called
docker logs ai-automation-service --since 5m | Select-String "POST /api/v1/ask-ai/query"

# 3. Check if OpenAI response is received
docker logs ai-automation-service --since 5m | Select-String "OpenAI response"

# 4. Check if suggestions are being parsed
docker logs ai-automation-service --since 5m | Select-String "Processing.*suggestions"

# 5. Full rebuild (no cache)
docker-compose build --no-cache ai-automation-service
docker-compose up -d ai-automation-service
```

## 🎯 Next Steps

1. **Force Clean Rebuild**
   ```powershell
   docker-compose down ai-automation-service
   docker builder prune -af
   docker-compose build --no-cache ai-automation-service
   docker-compose up -d ai-automation-service
   ```

2. **Verify Deployment**
   ```powershell
   docker exec ai-automation-service grep "CONSOLIDATION DEBUG" /app/src/api/ask_ai_router.py
   ```

3. **Test with Fresh Suggestion**
   - Create new suggestion in Ask AI
   - Check logs for "[CONSOLIDATION DEBUG]" messages

4. **If Still Not Working:**
   - Add `import sys; sys.stderr.write()` for immediate output
   - Add debug log at line 2503 (before loop)
   - Add debug log at line 2505 (inside loop)
   - Verify `parsed` is not empty

## 📝 Code Locations

- **Router Entry:** Line 2625 (`process_natural_language_query`)
- **Suggestion Generator:** Line 2331 (`generate_suggestions_from_query`)
- **Pre-Consolidation:** Line 2515 (`_pre_consolidate_device_names`)
- **Deduplication:** Lines 2524-2539 (inline dedup logic)
- **Post-Consolidation:** Line 2559 (`consolidate_devices_involved`)
- **Debug Logs:** Lines 2504, 2510, 2517, 2533

## ⚠️ Critical Observation

The deduplication code is AFTER the debug log at line 2510. If we don't see the line 2510 log, the loop is never being entered, which means:

1. `parsed` is empty, OR
2. The code path is not reaching this function, OR
3. Logs are not flushing/visible

**We MUST see the line 2504 log first:** "🔍 [CONSOLIDATION DEBUG] Processing N suggestions from OpenAI"

If this log is missing, the problem is BEFORE the deduplication code.

