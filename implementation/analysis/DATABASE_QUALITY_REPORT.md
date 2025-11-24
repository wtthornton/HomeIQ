# Database Quality Report
**Date:** November 24, 2025  
**Database:** `ai_automation.db` (SQLite)  
**Service:** ai-automation-service

## Executive Summary

The database contains **23 critical data integrity issues** and **15 warnings**. The primary problems are:
1. **Schema mismatches**: Columns marked as NOT NULL contain NULL values
2. **Incomplete records**: Many queries and sessions are incomplete
3. **Empty feature tables**: Several feature tables are empty (may be expected)

## Critical Issues (23)

### 1. Schema Integrity Violations

**Patterns Table (1,139 rows affected):**
- `trend_direction`: 1,139 NULL values in NOT NULL column
- `raw_confidence`: 1,139 NULL values in NOT NULL column  
- `deprecated_at`: 1,139 NULL values in NOT NULL column

**Analysis Run Status (9 rows affected):**
- `finished_at`: 9 NULL values in NOT NULL column
- `duration_seconds`: 9 NULL values in NOT NULL column

**Ask AI Queries (444 rows affected):**
- `parsed_intent`: 444 NULL values in NOT NULL column

**Clarification System (64-400 rows affected):**
- `clarification_sessions.completed_at`: 400 NULL values
- `clarification_sessions.clarification_query_id`: 400 NULL values
- `clarification_outcomes.suggestion_approved`: 64 NULL values
- `clarification_outcomes.suggestion_id`: 64 NULL values
- `clarification_confidence_feedback.suggestion_approved`: 64 NULL values

**Model Comparison Metrics (4-6 rows affected):**
- Multiple columns with NULL values in NOT NULL columns (6 rows total)

**Synergy Opportunities (50 rows affected):**
- `area`: 50 NULL values
- `embedding_similarity`: 50 NULL values
- `rerank_score`: 50 NULL values
- `final_score`: 50 NULL values
- `supporting_pattern_ids`: 50 NULL values

### 2. Data Completeness Issues

- **551 queries** (54% of 1,018 total) have no suggestions generated
- **400 clarification sessions** (86% of 465 total) are incomplete (missing completion data)

## Warnings (15)

### Empty Feature Tables
These tables are empty, which may be expected if features aren't enabled:
- `suggestions` (0 rows) - ✅ **Expected** (just deleted)
- `device_capabilities` (0 rows)
- `device_embeddings` (0 rows)
- `device_feature_usage` (0 rows)
- `discovered_synergies` (0 rows)
- `entity_aliases` (0 rows)
- `auto_resolution_metrics` (0 rows)
- `automation_versions` (0 rows)
- `qa_outcomes` (0 rows)
- `question_quality_metrics` (0 rows)
- `reverse_engineering_metrics` (0 rows)
- `training_runs` (0 rows)
- `user_feedback` (0 rows)
- `user_preferences` (0 rows)

## Data Statistics

**Active Tables:**
- `ask_ai_queries`: 1,018 rows
- `pattern_history`: 7,443 rows
- `patterns`: 1,139 rows
- `clarification_sessions`: 465 rows
- `semantic_knowledge`: 512 rows
- `synergy_opportunities`: 50 rows

## Root Causes

1. **Schema Evolution Without Migrations**: Columns were added as NOT NULL but existing rows weren't updated
2. **Incomplete Processing**: Many queries/sessions were started but never completed
3. **Feature Flags**: Some features may be disabled, leaving tables empty

## Recommendations

### 🔧 Immediate Actions

1. **Fix Schema Mismatches:**
   ```sql
   -- Option 1: Make columns nullable (if NULL is valid)
   ALTER TABLE patterns ALTER COLUMN trend_direction DROP NOT NULL;
   ALTER TABLE patterns ALTER COLUMN raw_confidence DROP NOT NULL;
   ALTER TABLE patterns ALTER COLUMN deprecated_at DROP NOT NULL;
   
   -- Option 2: Fill with default values (if NULL is invalid)
   UPDATE patterns SET trend_direction = 'stable' WHERE trend_direction IS NULL;
   UPDATE patterns SET raw_confidence = confidence WHERE raw_confidence IS NULL;
   ```

2. **Clean Up Incomplete Records:**
   - Review and either complete or delete incomplete clarification sessions
   - Investigate why 54% of queries don't generate suggestions

3. **Add Data Validation:**
   - Add application-level checks before inserting NULL into NOT NULL columns
   - Add database constraints or triggers

### 💡 Medium-Term Improvements

1. **Database Migrations:**
   - Use Alembic migrations for all schema changes
   - Never add NOT NULL columns without default values or migration scripts

2. **Data Quality Monitoring:**
   - Add periodic data quality checks
   - Alert on schema violations

3. **Feature Enablement:**
   - Review which features are enabled/disabled
   - Document expected empty tables

### 📊 Long-Term Strategy

1. **Data Cleanup Script:**
   - Create script to fix existing NULL violations
   - Run before major releases

2. **Schema Documentation:**
   - Document which columns can be NULL vs NOT NULL
   - Keep schema in sync with models

3. **Testing:**
   - Add integration tests that verify data integrity
   - Test schema migrations on sample data

## Priority Fixes

**High Priority:**
- Fix `patterns` table (1,139 rows) - core data
- Fix `ask_ai_queries.parsed_intent` (444 rows) - affects query processing

**Medium Priority:**
- Fix clarification system tables (64-400 rows)
- Fix synergy_opportunities (50 rows)

**Low Priority:**
- Fix analysis_run_status (9 rows)
- Fix model_comparison_metrics (6 rows)

## Conclusion

The database has **structural integrity issues** but the **core data appears intact**. The main problems are:
- Schema definitions don't match actual data (NOT NULL columns with NULLs)
- Many incomplete processing records
- Some features not yet populated

**Recommendation:** Fix schema mismatches first, then investigate incomplete processing records. The empty tables are likely expected for features not yet enabled.

