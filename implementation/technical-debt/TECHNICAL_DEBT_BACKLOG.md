# Technical Debt Backlog

**Generated:** 2025-12-03 10:35:27

**Total Items:** 347

## Summary Statistics

### By Priority

- **CRITICAL:** 2 items
- **HIGH:** 17 items
- **MEDIUM:** 318 items
- **LOW:** 10 items

### By Category

- **architecture:** 30 items
- **bug:** 5 items
- **documentation:** 10 items
- **feature:** 69 items
- **other:** 165 items
- **performance:** 30 items
- **refactoring:** 7 items
- **security:** 4 items
- **testing:** 27 items

### By Type

- **FIXME COMMENT.""":** 1 items
- **FIXME COMMENTS:** 2 items
- **FIXME COMMENTS FROM A SINGLE FILE.""":** 1 items
- **FIXME COMMENTS FROM CODEBASE.:** 1 items
- **FIXME COMMENTS.""":** 1 items
- **FIXME ITEMS FOUND IN CODE FILES."):** 1 items
- **FIXME ITEMS"):** 1 items
- **HACK
    MESSAGE:** 1 items
- **NOTE:** 244 items
- **NOTE

                                LOGGER.DEBUG(F"✅ BUILT FILTERED USER PROMPT FOR SUGGESTION {I+1}"):** 1 items
- **NOTE
        PRINT("PERFORMANCE IMPACT:** 2 items
- **NOTE = F" (FROM {MERGED_BRANCH})" IF MERGED_BRANCH ELSE "":** 1 items
- **NOTE = F"\N\N[NOTE:** 1 items
- **NOTE ABOUT FILTERING:** 1 items
- **NOTE CONSOLIDATION IN METADATA:** 2 items
- **NOTE IT MIGHT INDICATE MISSING ENDPOINT IMPLEMENTATION:** 1 items
- **NOTE RELATIVE IMPORTS (CAN'T FULLY VALIDATE STATICALLY):** 1 items
- **NOTE THAT THIS SHOULD BE LONG LIVED IN ORDER FOR RATE LIMITING TO BE EFFECTIVE.:** 2 items
- **NOTE THEIR CONFIGURATION", FILE=SYS.STDERR):** 1 items
- **TODO:** 79 items
- **TODO WEEK 2:** 1 items
- **XXX
OPENAI_API_KEY:** 1 items

## Top 50 High-Priority Items

### 1. [CRITICAL] NOTE

                                LOGGER.DEBUG(F"✅ BUILT FILTERED USER PROMPT FOR SUGGESTION {I+1}"): logger.debug(f"✅ Built filtered user prompt for suggestion {i+1}")

**File:** `services\ai-automation-service\src\api\ask_ai_router.py` (line 4748)

**Category:** bug

**Context:**
```
4745: 
4746:                                 # Add note about filtering
4747:                                 note = f"\n\n[NOTE: Entity context filtered to show only {len(validated_entities)} entities used in this suggestion out of {len(enriched_data)} available]"
4748:                                 filtered_user_prompt = filtered_user_prompt + note
4749: 
4750:                                 logger.debug(f"✅ Built filtered user prompt for suggestion {i+1}")
4751: 
```

---

### 2. [CRITICAL] NOTE: High criticality but clear logic flow. Document edge cases if adding

**File:** `services\ai-automation-service\src\safety_validator.py` (line 240)

**Category:** documentation

**Context:**
```
 237:             ... }
 238: 
 239:         Complexity: C (12) - Multiple pattern checks for bulk operations
 240:         Note: High criticality but clear logic flow. Document edge cases if adding
 241:               new bulk operation patterns.
 242:         """
 243:         issues = []
```

---

### 3. [HIGH] NOTE: The pipeline already returns early on syntax errors, but we double-check

**File:** `services\ai-automation-service\src\services\automation\yaml_generation_service.py` (line 556)

**Category:** bug

**Context:**
```
 553:     )
 554: 
 555:     # Check if syntax validation failed (first stage) - this is critical
 556:     # Note: The pipeline already returns early on syntax errors, but we double-check
 557:     if not validation_result.stages or not validation_result.stages[0].valid:
 558:         syntax_errors = validation_result.stages[0].errors if validation_result.stages else []
 559:         error_msg = syntax_errors[0] if syntax_errors else "Invalid YAML syntax"
```

---

### 4. [HIGH] NOTE: This is probabilistic, so we just check the method runs without error

**File:** `services\ai-automation-service\tests\training\test_context_correlator.py` (line 171)

**Category:** bug

**Context:**
```
 168: 
 169:         # May have added energy event (probabilistic)
 170:         energy_events = [e for e in result if 'energy_low_carbon' in e.get('attributes', {}).get('context', '')]
 171:         # Note: This is probabilistic, so we just check the method runs without error
 172: 
 173:     def test_apply_energy_patterns_high_carbon(self):
 174:         """Test energy-aware pattern: high carbon → reduce usage."""
```

---

### 5. [HIGH] NOTE: The error field may be added directly to action dict

**File:** `services\ai-automation-service\tests\test_best_practice_enhancements_integration.py` (line 134)

**Category:** feature

**Context:**
```
 131:         assert len(actions) >= 2
 132: 
 133:         # Both actions should have error: "continue" (non-critical)
 134:         # Note: The error field may be added directly to action dict
 135:         for action in actions:
 136:             # Check if error field exists or action has been wrapped
 137:             assert "service" in action  # Basic validation
```

---

### 6. [HIGH] TODO: Implement once we have error tracking in InfluxDB

**File:** `services\data-api\src\analytics_endpoints.py` (line 307)

**Category:** feature

**Context:**
```
 304: 
 305: async def query_error_rate(start_time: str, interval: str, num_points: int) -> list[dict[str, Any]]:
 306:     """Query error rate (mock data for now)"""
 307:     # TODO: Implement once we have error tracking in InfluxDB
 308:     return generate_mock_series(start_time, interval, num_points, base=0.5, variance=0.5)
 309: 
 310: 
```

---

### 7. [HIGH] NOTE: ** Optional enhancement - not required for production deployment\n")

**File:** `scripts\prepare_for_production.py` (line 971)

**Category:** other

**Context:**
```
 968:                 f.write(f"- **Status:** {status_icon} {'PASSED' if result.get('success') else 'NOT CONFIGURED'}\n")
 969:                 f.write(f"- **Type:** 🟡 OPTIONAL\n")
 970:                 if not result.get('success'):
 971:                     f.write("- **Note:** Optional enhancement - not required for production deployment\n")
 972:                 if result.get('results'):
 973:                     f.write("- **Metrics:**\n")
 974:                     for key, value in result['results'].items():
```

---

### 8. [HIGH] NOTE: In production, these would be imported from homeassistant.components.*

**File:** `services\ai-automation-service\src\clients\capability_parsers\constants.py` (line 4)

**Category:** other

**Context:**
```
   1: """
   2: Home Assistant supported_features Bitmask Constants.
   3: 
   4: Note: In production, these would be imported from homeassistant.components.*
   5: For now, we define them manually to avoid the heavy HA dependency.
   6: """
   7: 
```

---

### 9. [HIGH] NOTE: Training might still fail if all 50 samples have same outcome, but with mixed outcomes it should wor

**File:** `services\ai-automation-service\tests\test_confidence_calibrator.py` (line 328)

**Category:** other

**Context:**
```
 325:         )
 326: 
 327:         # Should be fitted after auto-retrain (if we have enough samples and both classes)
 328:         # Note: Training might still fail if all 50 samples have same outcome, but with mixed outcomes it should work
 329:         # The test verifies the auto-retrain trigger mechanism, not necessarily successful training
 330:         assert len(calibrator.features_history) == 50
 331: 
```

---

### 10. [HIGH] NOTE: Due to randomness, we can't guarantee failures, but we can check structure

**File:** `services\ai-automation-service\tests\training\test_failure_scenarios.py` (line 167)

**Category:** other

**Context:**
```
 164: 
 165:         # Check that some devices may have failure scenarios (probabilistic)
 166:         failed_devices = [d for d in devices_with_failures if 'failure_scenario' in d]
 167:         # Note: Due to randomness, we can't guarantee failures, but we can check structure
 168: 
 169:     def test_assign_failure_scenarios_structure(self):
 170:         """Test that assigned failure scenarios have correct structure."""
```

---

### 11. [HIGH] NOTE: High complexity arises from:

**File:** `services\data-api\src\config_manager.py` (line 213)

**Category:** other

**Context:**
```
 210:             >>> else:
 211:             ...     print(f"Errors: {result['errors']}")
 212: 
 213:         Note:
 214:             High complexity arises from:
 215:             - Multiple service types with different validation rules
 216:             - Nested validation logic for each service
```

---

### 12. [HIGH] NOTE: In production, use Alembic migrations instead.

**File:** `services\data-api\src\database.py` (line 137)

**Category:** other

**Context:**
```
 134:     Initialize database by creating all tables.
 135: 
 136:     Called during application startup.
 137:     Note: In production, use Alembic migrations instead.
 138:     """
 139:     async with async_engine.begin() as conn:
 140:         # Create all tables defined in Base metadata
```

---

### 13. [HIGH] NOTE: High complexity arises from:

**File:** `services\data-api\src\events_endpoints.py` (line 932)

**Category:** other

**Context:**
```
 929:             >>> for event in events:
 930:             ...     print(f"{event.timestamp}: {event.entity_id} = {event.state_value}")
 931: 
 932:         Note:
 933:             High complexity arises from:
 934:             - Dynamic Flux query construction based on filters
 935:             - Multiple optional filter conditions
```

---

### 14. [HIGH] NOTE: In production, delete raw data here after verification

**File:** `services\data-retention\src\tiered_retention.py` (line 121)

**Category:** other

**Context:**
```
 118: 
 119:                 records_downsampled = len(result)
 120: 
 121:                 # Note: In production, delete raw data here after verification
 122:                 # For safety, we'll leave deletion as manual step initially
 123: 
 124:                 logger.info(f"Downsampled {records_downsampled} hourly records")
```

---

### 15. [HIGH] NOTE: These are placeholder icons. For production, use proper icon generation tools.")

**File:** `services\health-dashboard\scripts\generate-icons.py` (line 43)

**Category:** other

**Context:**
```
  40:     create_icon_png(512, public_dir / "icon-512.png")
  41: 
  42:     print("Icons generated successfully!")
  43:     print("Note: These are placeholder icons. For production, use proper icon generation tools.")
  44: 
  45: if __name__ == "__main__":
  46:     main()
```

---

### 16. [HIGH] NOTE
        PRINT("PERFORMANCE IMPACT: print("Performance Impact:")

**File:** `scripts\add_composite_indexes.py` (line 166)

**Category:** performance

**Context:**
```
 163:         print(f"📊 Total composite indexes: {len(COMPOSITE_INDEXES)}")
 164:         print()
 165: 
 166:         # Performance note
 167:         print("Performance Impact:")
 168:         print("  - Queries filtering by status + ordering by created_at will be faster")
 169:         print("  - Pattern type + confidence queries will benefit from composite index")
```

---

### 17. [HIGH] NOTE
        PRINT("PERFORMANCE IMPACT: print("Performance Impact:")

**File:** `scripts\add_partial_indexes.py` (line 151)

**Category:** performance

**Context:**
```
 148:         print(f"📊 Total partial indexes: {len(PARTIAL_INDEXES)}")
 149:         print()
 150: 
 151:         # Performance note
 152:         print("Performance Impact:")
 153:         print("  - Queries filtering active suggestions (draft/refining) will be faster")
 154:         print("  - Queries filtering active patterns (deprecated=0) will be faster")
```

---

### 18. [HIGH] NOTE: This test may fail if model training is slow

**File:** `services\ai-automation-service\tests\services\pattern_quality\test_incremental_learner.py` (line 289)

**Category:** performance

**Context:**
```
 286: 
 287:             result = await learner.update_model()
 288: 
 289:             # Note: This test may fail if model training is slow
 290:             # In practice, with optimized training, should be <5 seconds
 291:             assert result['status'] == 'success'
 292:             # Performance check (may need adjustment based on actual performance)
```

---

### 19. [HIGH] NOTE: Production bucket has 365 days retention, test bucket has 7 days

**File:** `services\ai-automation-service\tests\datasets\test_single_home_patterns.py` (line 243)

**Category:** testing

**Context:**
```
 240:     # Test: ~7.5 events per device per day (doubled for better accuracy)
 241:     # Also factor in areas (more rooms = more activity)
 242: 
 243:     # Note: Production bucket has 365 days retention, test bucket has 7 days
 244:     # We generate 7 days to match test bucket retention (168h = 7 days)
 245:     days = 7  # 7 days of history (matches test bucket retention)
 246: 
```

---


## All Items by Priority

### CRITICAL Priority (2 items)

#### BUG (1 items)

- **NOTE

                                LOGGER.DEBUG(F"✅ BUILT FILTERED USER PROMPT FOR SUGGESTION {I+1}")** in `services\ai-automation-service\src\api\ask_ai_router.py:4748`: logger.debug(f"✅ Built filtered user prompt for suggestion {i+1}")

#### DOCUMENTATION (1 items)

- **NOTE** in `services\ai-automation-service\src\safety_validator.py:240`: High criticality but clear logic flow. Document edge cases if adding


### HIGH Priority (17 items)

#### BUG (2 items)

- **NOTE** in `services\ai-automation-service\src\services\automation\yaml_generation_service.py:556`: The pipeline already returns early on syntax errors, but we double-check
- **NOTE** in `services\ai-automation-service\tests\training\test_context_correlator.py:171`: This is probabilistic, so we just check the method runs without error

#### FEATURE (2 items)

- **NOTE** in `services\ai-automation-service\tests\test_best_practice_enhancements_integration.py:134`: The error field may be added directly to action dict
- **TODO** in `services\data-api\src\analytics_endpoints.py:307`: Implement once we have error tracking in InfluxDB

#### OTHER (9 items)

- **NOTE** in `scripts\prepare_for_production.py:971`: ** Optional enhancement - not required for production deployment\n")
- **NOTE** in `services\ai-automation-service\src\clients\capability_parsers\constants.py:4`: In production, these would be imported from homeassistant.components.*
- **NOTE** in `services\ai-automation-service\tests\test_confidence_calibrator.py:328`: Training might still fail if all 50 samples have same outcome, but with mixed outcomes it should work
- **NOTE** in `services\ai-automation-service\tests\training\test_failure_scenarios.py:167`: Due to randomness, we can't guarantee failures, but we can check structure
- **NOTE** in `services\data-api\src\config_manager.py:213`: High complexity arises from:
- **NOTE** in `services\data-api\src\database.py:137`: In production, use Alembic migrations instead.
- **NOTE** in `services\data-api\src\events_endpoints.py:932`: High complexity arises from:
- **NOTE** in `services\data-retention\src\tiered_retention.py:121`: In production, delete raw data here after verification
- **NOTE** in `services\health-dashboard\scripts\generate-icons.py:43`: These are placeholder icons. For production, use proper icon generation tools.")

#### PERFORMANCE (3 items)

- **NOTE
        PRINT("PERFORMANCE IMPACT** in `scripts\add_composite_indexes.py:166`: print("Performance Impact:")
- **NOTE
        PRINT("PERFORMANCE IMPACT** in `scripts\add_partial_indexes.py:151`: print("Performance Impact:")
- **NOTE** in `services\ai-automation-service\tests\services\pattern_quality\test_incremental_learner.py:289`: This test may fail if model training is slow

#### TESTING (1 items)

- **NOTE** in `services\ai-automation-service\tests\datasets\test_single_home_patterns.py:243`: Production bucket has 365 days retention, test bucket has 7 days


### MEDIUM Priority (318 items)

#### ARCHITECTURE (30 items)

- **NOTE** in `scripts\setup_downsampling_schedule.py:81`: Schedules are configured in services/data-retention/src/main.py")
- **NOTE** in `services\ai-automation-service-new\tests\conftest.py:37`: Automation service uses shared database models (Suggestion, etc.).
- **NOTE** in `services\ai-automation-service\scripts\seed_rag_simple.py:106`: Embeddings are placeholders. Run full seeding script with OpenVINO service")
- **NOTE** in `services\ai-automation-service\src\api\health.py:188`: For precise uptime, SERVICE_START_TIME would be tracked in main.py
- **NOTE** in `services\ai-automation-service\src\migration\data_migration.py:95`: This is a simplified migration since Device Intelligence Service
- **NOTE** in `services\ai-automation-service\src\migration\data_migration.py:135`: Device count might be 0 initially since Device Intelligence Service
- **TODO** in `services\ai-automation-service\src\preprocessing\feature_extractors.py:116`: Advanced seasonal pattern detection"""
- **TODO** in `services\ai-automation-service\src\services\clarification\ab_testing.py:153`: Send to metrics/analytics service for statistical analysis
- **NOTE** in `services\ai-automation-service\src\services\entity_capability_enrichment.py:236`: For now, we'll rely on the discovery service to update capabilities
- **NOTE** in `services\ai-automation-service\src\training\quality_gates.py:178`: This requires pattern detection to be run on events.
- **NOTE** in `services\ai-automation-service\tests\datasets\test_synergy_detection_comprehensive.py:449`: May be 0 if not enough event data or patterns
- **NOTE** in `services\ai-pattern-service\src\crud\patterns.py:15`: Pattern model is defined in shared database (ai-automation-service)
- **NOTE** in `services\ai-pattern-service\src\database\models.py:15`: Pattern and SynergyOpportunity models are defined in
- **NOTE** in `services\ai-pattern-service\tests\conftest.py:18`: Pattern and SynergyOpportunity models are in shared database
- **NOTE** in `services\ai-pattern-service\tests\conftest.py:39`: Pattern and SynergyOpportunity tables are in shared database,
- **NOTE** in `services\ai-query-service\src\database\models.py:8`: Actual models are defined in ai-automation-service/src/database/models.py
- **NOTE** in `services\ai-training-service\scripts\train_gnn_synergy.py:17`: This script currently depends on modules from ai-automation-service:
- **NOTE** in `services\ai-training-service\scripts\train_gnn_synergy.py:33`: This may need adjustment based on how we handle cross-service dependencies
- **NOTE** in `services\ai-training-service\scripts\train_home_type_classifier.py:9`: This script currently depends on FineTunedHomeTypeClassifier from ai-automation-service.
- **NOTE** in `services\ai-training-service\scripts\train_home_type_classifier.py:21`: This may need adjustment based on how we handle cross-service dependencies
- *... and 10 more items*

#### BUG (2 items)

- **NOTE** in `services\ai-automation-service\src\services\automation\yaml_generation_service.py:1342`: The 'id' field will automatically be made unique (timestamp + UUID suffix appended) to ensure each approval creates a NEW automation, not an update to
- **TODO** in `services\ai-automation-ui\src\services\api.ts:406`: Fix data API device resolution

#### DOCUMENTATION (9 items)

- **FIXME COMMENTS FROM CODEBASE.** in `scripts\extract-technical-debt.py:3`: comments from codebase.
- **FIXME COMMENTS** in `scripts\extract-technical-debt.py:15`: comments
- **FIXME COMMENT."""** in `scripts\extract-technical-debt.py:75`: comment."""
- **FIXME COMMENTS FROM A SINGLE FILE."""** in `scripts\extract-technical-debt.py:110`: comments from a single file."""
- **FIXME COMMENTS** in `scripts\extract-technical-debt.py:123`: comments
- **FIXME COMMENTS."""** in `scripts\extract-technical-debt.py:156`: comments."""
- **NOTE** in `services\ai-automation-service\src\home_type\home_type_classifier.py:109`: This runs ONCE before release, model is included in Docker image.
- **NOTE** in `tests\integration\test_ask_ai_test_button_api.py:35`: ai-automation-service is on port 8024 externally (docker maps 8024:8018)
- **NOTE** in `tools\ask-ai-continuous-improvement-unit-test.py:1022`: This version uses direct function calls and connects to real Docker services!")

#### FEATURE (67 items)

- **NOTE** in `services\ai-automation-service\alembic\versions\20251020_add_pattern_synergy_integration.py:86`: SQLite doesn't support ALTER COLUMN, so we'll update NULLs but can't enforce NOT NULL
- **NOTE** in `services\ai-automation-service\alembic\versions\20251201_bge_m3_embedding_upgrade.py:10`: No schema changes required - JSON column already supports variable dimensions.
- **NOTE** in `services\ai-automation-service\scripts\test_cleanup_functionality.py:94`: InfluxDB delete API doesn't support regex, so we use measurement-only predicate
- **TODO** in `services\ai-automation-service\src\api\ask_ai_router.py:7512`: Implement actual refinement logic
- **TODO** in `services\ai-automation-service\src\api\conversational_router.py:1259`: Implement database fetch
- **NOTE** in `services\ai-automation-service\src\api\pattern_router.py:497`: This is a simplified version - full implementation would
- **NOTE** in `services\ai-automation-service\src\integration\pattern_synergy_validator.py:323`: Don't add to supporting_patterns (indirect support)
- **TODO** in `services\ai-automation-service\src\llm\openai_client.py:538`: Re-enable when OpenAI SDK fully supports GPT-5.1 parameters
- **TODO** in `services\ai-automation-service\src\patterns\pattern_composer.py:100`: In full implementation, parse YAML and merge actions from other patterns
- **TODO WEEK 2** in `services\ai-automation-service\src\preprocessing\feature_extractors.py:34`: Week 2: Implement HA sensor queries
- **TODO** in `services\ai-automation-service\src\preprocessing\feature_extractors.py:126`: Anomaly detection features (z-scores, outliers)"""
- **NOTE** in `services\ai-automation-service\src\services\automation\action_executor.py:192`: In a real implementation, we'd track completion via callbacks
- **NOTE** in `services\ai-automation-service\src\services\automation\label_target_optimizer.py:132`: Label API validation could be added here if needed
- **NOTE** in `services\ai-automation-service\src\services\automation\yaml_generation_service.py:1820`: Entity validation is already done in the pipeline, but HA API provides additional checks
- **TODO** in `services\ai-automation-service\src\services\pattern_quality\model_trainer.py:110`: Implement blueprint corpus loading (Epic AI-4)
- **NOTE** in `services\ai-automation-service\src\services\pattern_quality\transfer_learner.py:240`: RandomForest doesn't support true fine-tuning (incremental learning).
- **TODO** in `services\ai-automation-service\src\services\safety_validator.py:195`: Implement full conflict detection
- **TODO** in `services\ai-automation-service\src\synergy_detection\sequence_transformer.py:25`: Implement fine-tuning)
- **TODO** in `services\ai-automation-service\src\synergy_detection\sequence_transformer.py:26`: Implement transformer-based prediction)
- **TODO** in `services\ai-automation-service\src\synergy_detection\sequence_transformer.py:125`: Implement fine-tuning logic
- *... and 47 more items*

#### OTHER (150 items)

- **NOTE** in `scripts\check-hacs-status.py:8`: HACS cannot be installed via HA API - it requires manual installation.
- **NOTE** in `scripts\check_openai_rate_limits.py:263`: Rate limit headers are only in successful responses, "
- **NOTE** in `scripts\db_summary.py:41`: Row counts not available via CLI")
- **HACK
    MESSAGE** in `scripts\extract-technical-debt.py:78`: message: str
- **FIXME ITEMS")** in `scripts\extract-technical-debt.py:307`: items")
- **FIXME ITEMS FOUND IN CODE FILES.")** in `scripts\extract-technical-debt.py:324`: items found in code files.")
- **NOTE** in `scripts\fetch_suggestion_debug_data.py:243`: ** Filtered prompt shows only {used} of {total} available entities to reduce token usage\n"
- **NOTE** in `scripts\fix-external-data-sources-env.py:221`: Make sure to replace placeholder values with your actual API keys:")
- **NOTE** in `scripts\load_dataset_to_ha.py:34`: This requires the entity to exist first (via configuration)
- **NOTE** in `scripts\optimize_influxdb_shards.py:104`: Changing shard duration requires manual configuration")
- **NOTE** in `scripts\refresh-context7-docs.py:11`: Requires Context7 MCP server to be configured with valid API key.
- **NOTE** in `scripts\refresh-context7-docs.py:117`: These commands require Context7 MCP server with valid API key.")
- **NOTE** in `scripts\setup_downsampling_schedule.py:30`: This would require InfluxDB API access
- **NOTE** in `scripts\setup_downsampling_schedule.py:42`: Buckets are created automatically by the downsampling process")
- **NOTE = F" (FROM {MERGED_BRANCH})" IF MERGED_BRANCH ELSE ""** in `scripts\update-documentation.py:135`: = f" (from {merged_branch})" if merged_branch else ""
- **NOTE RELATIVE IMPORTS (CAN'T FULLY VALIDATE STATICALLY)** in `scripts\validate_imports.py:126`: relative imports (can't fully validate statically)
- **NOTE** in `services\ai-automation-service-new\tests\conftest.py:17`: These imports will be available once main.py and routers are created
- **NOTE** in `services\ai-automation-service\alembic\versions\20251020_add_pattern_synergy_integration.py:40`: For existing rows, we set defaults that will be updated on next detection
- **NOTE** in `services\ai-automation-service\alembic\versions\20251020_add_pattern_synergy_integration.py:124`: These might already exist, but Alembic will handle that gracefully
- **NOTE** in `services\ai-automation-service\list_agents.py:255`: The /api/conversation/agents endpoint is not available in HA 2025.10.4", file=sys.stderr)
- *... and 130 more items*

#### PERFORMANCE (25 items)

- **NOTE** in `scripts\add_composite_indexes.py:172`: Run ANALYZE after creating indexes to update query planner statistics")
- **NOTE** in `scripts\add_partial_indexes.py:157`: Run ANALYZE after creating indexes to update query planner statistics")
- **NOTE** in `scripts\fetch_suggestion_debug_data.py:386`: For suggestion #2060, you may need to provide the query_id.")
- **NOTE** in `scripts\optimize_influxdb_shards.py:62`: In a real implementation, we would analyze actual query logs
- **NOTE** in `scripts\train_soft_prompt.py:246`: TRANSFORMERS_CACHE is deprecated, use HF_HOME only
- **NOTE** in `services\ai-automation-service\scripts\train_soft_prompt.py:275`: TRANSFORMERS_CACHE is deprecated, use HF_HOME only
- **NOTE** in `services\ai-automation-service\src\clients\influxdb_client.py:108`: When querying context_id field, _value contains context_id, not state
- **TODO** in `services\ai-automation-service\src\database\crud.py:1295`: Implement entity validation by querying Home Assistant or entity database
- **NOTE** in `services\ai-automation-service\src\llm\openai_client.py:483`: Prompt caching via cache_control parameter is not currently supported
- **NOTE** in `services\ai-automation-service\src\llm\openai_client.py:533`: cache_control parameter is not supported in OpenAI Python SDK
- **NOTE** in `services\ai-automation-service\src\services\entity_validator.py:784`: Location filtering happens at API level if query_location is provided
- **NOTE** in `services\ai-automation-service\src\synergy_detection\synergy_detector.py:1076`: synergy_cache.clear() is async, but clear_cache is sync
- **NOTE** in `services\ai-automation-service\src\utils\performance.py:191`: These should be set at connection level, not query level
- **NOTE** in `services\ai-automation-service\tests\test_phase3d_blueprint_discovery.py:301`: This depends on cache TTL being > 0
- **NOTE** in `services\ai-automation-ui\src\pages\AskAI.tsx:1666`: validated_entities keys are user query terms, not necessarily actual friendly names
- **NOTE** in `services\ai-pattern-service\src\synergy_detection\synergy_detector.py:189`: synergy_cache module will be copied in later stories
- **NOTE** in `services\ai-pattern-service\src\synergy_detection\synergy_detector.py:1081`: synergy_cache.clear() is async, but clear_cache is sync
- **NOTE** in `services\ai-query-service\src\database\models.py:4`: Query service uses shared database tables from ai-automation-service.
- **TODO** in `services\ai-query-service\src\services\suggestion\generator.py:58`: Full implementation from generate_suggestions_from_query()
- **NOTE** in `services\ai-query-service\tests\conftest.py:36`: Query service uses shared database models (AskAIQuery, ClarificationSessionDB).
- *... and 5 more items*

#### REFACTORING (6 items)

- **NOTE** in `services\ai-automation-service\src\correlation\feature_extractor.py:346`: Calendar integration is async, but feature extraction is sync
- **NOTE** in `services\ai-automation-service\src\nl_automation_generator.py:502`: _extract_area_from_request() has been moved to utils.area_detection
- **TODO** in `services\ai-automation-service\src\preprocessing\feature_extractors.py:121`: Frequency-based feature extraction (FFT, etc.)"""
- **TODO** in `services\ai-automation-service\src\services\learning\continuous_improvement.py:101`: Extract from automation
- **NOTE** in `services\ai-query-service\src\api\query_router.py:13`: This is a foundation implementation. Full extraction from ask_ai_router.py
- **TODO** in `services\tests\datasets\home-assistant-datasets\home_assistant_datasets\metrics\scrape_reader.py:48`: Cleanup old records with no model_id

#### SECURITY (4 items)

- **NOTE** in `scripts\check_openai_rate_limits.py:49`: This endpoint may require organization-level authentication or a valid project ID.
- **NOTE** in `scripts\check_openai_rate_limits.py:87`: This may also require organization-level authentication
- **TODO** in `services\ai-query-service\src\main.py:127`: Story 39.10 - Add authentication middleware
- **NOTE** in `services\data-api\src\devices_endpoints.py:1196`: No authentication needed for home use - services run on internal Docker network

#### TESTING (25 items)

- **NOTE** in `services\ai-automation-service-new\tests\conftest.py:169`: client fixture will be added once main.py is created
- **NOTE** in `services\ai-automation-service\scripts\test_json_home_loading.py:127`: To test actual HA loading, run:")
- **NOTE** in `services\ai-automation-service\tests\correlation\test_correlation_service.py:116`: In real test, would use time mocking
- **NOTE** in `services\ai-automation-service\tests\datasets\test_pattern_detection_comprehensive.py:273`: In real testing, we'd assert co_occurrence_percentage < 90
- **NOTE** in `services\ai-automation-service\tests\datasets\test_pattern_detection_with_datasets.py:61`: In a real test, you might want to use a test bucket
- **NOTE** in `services\ai-automation-service\tests\datasets\test_synergy_detection_comprehensive.py:51`: In a real test, we'd need to inject devices into the system
- **NOTE** in `services\ai-automation-service\tests\datasets\test_synergy_detection_comprehensive.py:134`: Full coverage requires datasets with all relationship types
- **NOTE** in `services\ai-automation-service\tests\integration\test_phase4_yaml_generation.py:318`: This test now uses generate_automation_yaml from ask_ai_router
- **NOTE** in `services\ai-automation-service\tests\test_spatial_validator.py:299`: This test verifies integration, actual filtering depends on relationship types
- **NOTE** in `services\data-api\tests\test_main.py:154`: Testing CORS properly requires actual cross-origin requests
- **TODO** in `services\device-intelligence-service\src\api\health.py:65`: Actually test database connection
- **TODO** in `services\device-intelligence-service\src\api\health.py:66`: Actually test Redis connection
- **TODO** in `services\device-intelligence-service\src\api\health.py:67`: Actually test HA connection
- **TODO** in `services\device-intelligence-service\src\api\health.py:68`: Actually test MQTT connection
- **NOTE** in `services\ha-simulator\tests\test_websocket_server.py:186`: In a real test, we'd need to check the JSON content
- **TODO** in `services\tests\datasets\home-assistant-datasets\home_assistant_datasets\tool\assist\collect\test_collect.py:17`: Some assist tests need to override validation to function
- **NOTE** in `services\weather-api\src\main.py:159`: InfluxDBClient3 doesn't have a direct ping, so we'll test on first write
- **NOTE** in `services\websocket-ingestion\tests\test_event_rate_monitor.py:308`: This test may not always trigger due to timing
- **NOTE** in `tests\e2e\ai-automation-analysis.spec.ts:388`: POST /api/analysis/trigger is mocked per-test for tracking
- **NOTE** in `tests\e2e\ai-automation-device-intelligence.spec.ts:13`: These tests verify device intelligence if implemented.
- *... and 5 more items*


### LOW Priority (10 items)

#### OTHER (6 items)

- **NOTE** in `services\ai-automation-service\src\api\conversational_router.py:832`: 'approved' status is set after YAML generation, so it should be allowed for re-deployment
- **NOTE** in `services\ai-automation-service\src\synergy_detection\explainable_synergy.py:187`: Currently in peak energy hours - consider scheduling for off-peak."
- **NOTE** in `services\ai-pattern-service\src\synergy_detection\synergy_detector.py:238`: PDL workflows are optional - gracefully handle if not available
- **NOTE** in `services\ai-training-service\src\training\synthetic_home_openai_generator.py:144`: Requires OpenAI client to be configured. The client type is Any to allow
- **NOTE** in `services\health-dashboard\scripts\generate-icons-proper.py:79`: Install Pillow for better icon quality:")
- **NOTE** in `services\health-dashboard\src\components\AnimatedDependencyGraph.tsx:212`: Pulse and active flows managed through CSS animations and real-time data

#### PERFORMANCE (2 items)

- **NOTE** in `services\ai-automation-service\src\api\admin_router.py:170`: TRANSFORMERS_CACHE is deprecated, use HF_HOME only to avoid FutureWarning
- **NOTE** in `services\ai-automation-service\src\services\comprehensive_entity_enrichment.py:506`: This is optional as it may be slow for many entities

#### REFACTORING (1 items)

- **NOTE** in `services\ai-automation-service\src\safety_validator.py:361`: Consider extracting destructive action detection to separate helper method

#### TESTING (1 items)

- **NOTE** in `services\ai-automation-service\tests\test_phase3d_blueprint_discovery.py:259`: This test uses mocks, so actual time may be lower



## Recommendations

### Immediate Actions (Week 1-2)

1. **Address 2 critical items** - Security, bugs, data loss risks
2. **Review 17 high-priority items** - Production issues, performance
3. **Create GitHub issues** for top 50 items
4. **Set up tracking** - Use project board or issue labels

### Short-term (Month 1)

1. **Address top 50 high-priority items**
2. **Categorize remaining items** by service/module
3. **Create service-specific backlogs**
4. **Set up automated tracking** - Prevent new debt accumulation

### Long-term (Quarter 1)

1. **Reduce technical debt by 10%** per quarter
2. **Establish code review standards** - Prevent new TODOs
3. **Regular backlog reviews** - Monthly prioritization
4. **Documentation improvements** - Address doc-related TODOs

