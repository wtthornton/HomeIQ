#!/usr/bin/env python3
"""
Fix database quality issues identified in the quality report.

This script:
1. Fixes schema mismatches (NULL in NOT NULL columns)
2. Cleans up incomplete records
3. Backfills missing data where possible
4. Provides detailed report of fixes

Usage:
    docker exec ai-automation-service python /app/fix_database_quality.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add /app/src to path for imports
script_dir = Path(__file__).parent
if (script_dir.parent / "services" / "ai-automation-service" / "src").exists():
    sys.path.insert(0, str(script_dir.parent / "services" / "ai-automation-service" / "src"))
else:
    sys.path.insert(0, "/app/src")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

async def fix_database_quality():
    """Fix all database quality issues"""
    print("=" * 80)
    print("FIXING DATABASE QUALITY ISSUES")
    print("=" * 80)
    print()
    
    # Database path
    if Path("/app/data/ai_automation.db").exists():
        db_path = "/app/data/ai_automation.db"
    elif (script_dir.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db").exists():
        db_path = str(script_dir.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db")
    else:
        print("❌ ERROR: Database not found")
        return False
    
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    fixes_applied = []
    records_updated = 0
    
    async with async_session() as db:
        print("Step 1: Fixing Patterns Table (1,139 rows)")
        print("-" * 80)
        
        # Check current state
        result = await db.execute(text("SELECT COUNT(*) FROM patterns WHERE trend_direction IS NULL"))
        null_trend = result.scalar()
        result = await db.execute(text("SELECT COUNT(*) FROM patterns WHERE raw_confidence IS NULL"))
        null_raw_conf = result.scalar()
        result = await db.execute(text("SELECT COUNT(*) FROM patterns WHERE deprecated_at IS NULL"))
        null_deprecated = result.scalar()
        
        print(f"  Found: {null_trend} NULL trend_direction, {null_raw_conf} NULL raw_confidence, {null_deprecated} NULL deprecated_at")
        
        # Fix trend_direction - set to 'stable' for NULL values
        if null_trend > 0:
            await db.execute(text("""
                UPDATE patterns 
                SET trend_direction = 'stable' 
                WHERE trend_direction IS NULL
            """))
            fixes_applied.append(f"patterns.trend_direction: Set {null_trend} NULL values to 'stable'")
            records_updated += null_trend
            print(f"  ✅ Fixed {null_trend} trend_direction values")
        
        # Fix raw_confidence - copy from confidence column
        if null_raw_conf > 0:
            await db.execute(text("""
                UPDATE patterns 
                SET raw_confidence = confidence 
                WHERE raw_confidence IS NULL
            """))
            fixes_applied.append(f"patterns.raw_confidence: Copied {null_raw_conf} values from confidence")
            records_updated += null_raw_conf
            print(f"  ✅ Fixed {null_raw_conf} raw_confidence values")
        
        # Fix deprecated_at - leave as NULL (it's a nullable field, but schema says NOT NULL)
        # We'll make it nullable instead
        if null_deprecated > 0:
            # SQLite doesn't support ALTER COLUMN easily, so we'll note this for manual fix
            fixes_applied.append(f"patterns.deprecated_at: {null_deprecated} NULL values (schema should allow NULL)")
            print(f"  ⚠️  deprecated_at has {null_deprecated} NULLs (schema issue - should be nullable)")
        
        await db.commit()
        print()
        
        print("Step 2: Fixing Ask AI Queries (444 rows)")
        print("-" * 80)
        
        result = await db.execute(text("SELECT COUNT(*) FROM ask_ai_queries WHERE parsed_intent IS NULL"))
        null_intent = result.scalar()
        
        if null_intent > 0:
            # Set empty string for NULL parsed_intent (better than NULL for NOT NULL column)
            await db.execute(text("""
                UPDATE ask_ai_queries 
                SET parsed_intent = '' 
                WHERE parsed_intent IS NULL
            """))
            fixes_applied.append(f"ask_ai_queries.parsed_intent: Set {null_intent} NULL values to empty string")
            records_updated += null_intent
            print(f"  ✅ Fixed {null_intent} parsed_intent values")
        else:
            print("  ✅ No issues found")
        
        await db.commit()
        print()
        
        print("Step 3: Fixing Analysis Run Status (9 rows)")
        print("-" * 80)
        
        result = await db.execute(text("SELECT COUNT(*) FROM analysis_run_status WHERE finished_at IS NULL"))
        null_finished = result.scalar()
        result = await db.execute(text("SELECT COUNT(*) FROM analysis_run_status WHERE duration_seconds IS NULL"))
        null_duration = result.scalar()
        
        if null_finished > 0 or null_duration > 0:
            # For incomplete runs, set finished_at to current time, duration to 0
            await db.execute(text("""
                UPDATE analysis_run_status 
                SET finished_at = CURRENT_TIMESTAMP,
                    duration_seconds = 0
                WHERE finished_at IS NULL OR duration_seconds IS NULL
            """))
            fixes_applied.append(f"analysis_run_status: Fixed {null_finished} finished_at and {null_duration} duration_seconds")
            records_updated += max(null_finished, null_duration)
            print(f"  ✅ Fixed {null_finished} finished_at and {null_duration} duration_seconds values")
        else:
            print("  ✅ No issues found")
        
        await db.commit()
        print()
        
        print("Step 4: Fixing Clarification System")
        print("-" * 80)
        
        # Fix clarification_sessions
        result = await db.execute(text("SELECT COUNT(*) FROM clarification_sessions WHERE completed_at IS NULL"))
        null_completed = result.scalar()
        result = await db.execute(text("SELECT COUNT(*) FROM clarification_sessions WHERE clarification_query_id IS NULL"))
        null_query_id = result.scalar()
        
        if null_completed > 0 or null_query_id > 0:
            # For incomplete sessions, mark as abandoned
            await db.execute(text("""
                UPDATE clarification_sessions 
                SET completed_at = CURRENT_TIMESTAMP,
                    clarification_query_id = COALESCE(clarification_query_id, '')
                WHERE completed_at IS NULL OR clarification_query_id IS NULL
            """))
            fixes_applied.append(f"clarification_sessions: Fixed {null_completed} completed_at and {null_query_id} query_id")
            records_updated += max(null_completed, null_query_id)
            print(f"  ✅ Fixed {null_completed} completed_at and {null_query_id} query_id values")
        
        # Fix clarification_outcomes
        result = await db.execute(text("SELECT COUNT(*) FROM clarification_outcomes WHERE suggestion_approved IS NULL"))
        null_approved = result.scalar()
        result = await db.execute(text("SELECT COUNT(*) FROM clarification_outcomes WHERE suggestion_id IS NULL"))
        null_sugg_id = result.scalar()
        
        if null_approved > 0 or null_sugg_id > 0:
            # Set defaults for incomplete outcomes
            await db.execute(text("""
                UPDATE clarification_outcomes 
                SET suggestion_approved = 0,
                    suggestion_id = COALESCE(suggestion_id, 0)
                WHERE suggestion_approved IS NULL OR suggestion_id IS NULL
            """))
            fixes_applied.append(f"clarification_outcomes: Fixed {null_approved} approved and {null_sugg_id} suggestion_id")
            records_updated += max(null_approved, null_sugg_id)
            print(f"  ✅ Fixed {null_approved} approved and {null_sugg_id} suggestion_id values")
        
        # Fix clarification_confidence_feedback
        result = await db.execute(text("SELECT COUNT(*) FROM clarification_confidence_feedback WHERE suggestion_approved IS NULL"))
        null_feedback_approved = result.scalar()
        
        if null_feedback_approved > 0:
            await db.execute(text("""
                UPDATE clarification_confidence_feedback 
                SET suggestion_approved = 0
                WHERE suggestion_approved IS NULL
            """))
            fixes_applied.append(f"clarification_confidence_feedback: Fixed {null_feedback_approved} approved values")
            records_updated += null_feedback_approved
            print(f"  ✅ Fixed {null_feedback_approved} approved values")
        
        await db.commit()
        print()
        
        print("Step 5: Fixing Model Comparison Metrics (6 rows)")
        print("-" * 80)
        
        # Fix all NULL columns in model_comparison_metrics
        result = await db.execute(text("""
            SELECT COUNT(*) FROM model_comparison_metrics 
            WHERE suggestion_id IS NULL 
               OR model1_error IS NULL 
               OR model2_error IS NULL
               OR model1_approved IS NULL
               OR model2_approved IS NULL
               OR model1_yaml_valid IS NULL
               OR model2_yaml_valid IS NULL
        """))
        null_metrics = result.scalar()
        
        if null_metrics > 0:
            await db.execute(text("""
                UPDATE model_comparison_metrics 
                SET suggestion_id = COALESCE(suggestion_id, 0),
                    model1_error = COALESCE(model1_error, ''),
                    model2_error = COALESCE(model2_error, ''),
                    model1_approved = COALESCE(model1_approved, 0),
                    model2_approved = COALESCE(model2_approved, 0),
                    model1_yaml_valid = COALESCE(model1_yaml_valid, 0),
                    model2_yaml_valid = COALESCE(model2_yaml_valid, 0)
                WHERE suggestion_id IS NULL 
                   OR model1_error IS NULL 
                   OR model2_error IS NULL
                   OR model1_approved IS NULL
                   OR model2_approved IS NULL
                   OR model1_yaml_valid IS NULL
                   OR model2_yaml_valid IS NULL
            """))
            fixes_applied.append(f"model_comparison_metrics: Fixed {null_metrics} rows with NULL values")
            records_updated += null_metrics
            print(f"  ✅ Fixed {null_metrics} rows")
        else:
            print("  ✅ No issues found")
        
        await db.commit()
        print()
        
        print("Step 6: Fixing Synergy Opportunities (50 rows)")
        print("-" * 80)
        
        result = await db.execute(text("SELECT COUNT(*) FROM synergy_opportunities WHERE area IS NULL"))
        null_area = result.scalar()
        
        if null_area > 0:
            # Set defaults for missing synergy data
            await db.execute(text("""
                UPDATE synergy_opportunities 
                SET area = COALESCE(area, ''),
                    embedding_similarity = COALESCE(embedding_similarity, 0.0),
                    rerank_score = COALESCE(rerank_score, 0.0),
                    final_score = COALESCE(final_score, 0.0),
                    supporting_pattern_ids = COALESCE(supporting_pattern_ids, '[]')
                WHERE area IS NULL 
                   OR embedding_similarity IS NULL
                   OR rerank_score IS NULL
                   OR final_score IS NULL
                   OR supporting_pattern_ids IS NULL
            """))
            fixes_applied.append(f"synergy_opportunities: Fixed {null_area} rows with NULL values")
            records_updated += null_area
            print(f"  ✅ Fixed {null_area} rows")
        else:
            print("  ✅ No issues found")
        
        await db.commit()
        print()
        
        print("Step 7: Cleaning Up Incomplete Records")
        print("-" * 80)
        
        # Delete very old incomplete clarification sessions (older than 30 days)
        result = await db.execute(text("""
            SELECT COUNT(*) FROM clarification_sessions 
            WHERE completed_at IS NULL 
              AND created_at < datetime('now', '-30 days')
        """))
        old_incomplete = result.scalar()
        
        if old_incomplete > 0:
            await db.execute(text("""
                DELETE FROM clarification_sessions 
                WHERE completed_at IS NULL 
                  AND created_at < datetime('now', '-30 days')
            """))
            fixes_applied.append(f"clarification_sessions: Deleted {old_incomplete} old incomplete sessions (>30 days)")
            print(f"  ✅ Deleted {old_incomplete} old incomplete sessions")
        else:
            print("  ✅ No old incomplete sessions to clean up")
        
        await db.commit()
        print()
        
        # Summary
        print("=" * 80)
        print("FIXES APPLIED")
        print("=" * 80)
        print()
        
        if fixes_applied:
            for fix in fixes_applied:
                print(f"  ✅ {fix}")
            print()
            print(f"Total records updated: {records_updated}")
        else:
            print("  ✅ No fixes needed - database is clean!")
        
        print()
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print()
        
        # Verify fixes
        verification_passed = True
        
        # Check patterns
        result = await db.execute(text("SELECT COUNT(*) FROM patterns WHERE trend_direction IS NULL"))
        if result.scalar() > 0:
            print(f"  ⚠️  patterns.trend_direction: Still has NULL values")
            verification_passed = False
        else:
            print(f"  ✅ patterns.trend_direction: All fixed")
        
        result = await db.execute(text("SELECT COUNT(*) FROM patterns WHERE raw_confidence IS NULL"))
        if result.scalar() > 0:
            print(f"  ⚠️  patterns.raw_confidence: Still has NULL values")
            verification_passed = False
        else:
            print(f"  ✅ patterns.raw_confidence: All fixed")
        
        # Check ask_ai_queries
        result = await db.execute(text("SELECT COUNT(*) FROM ask_ai_queries WHERE parsed_intent IS NULL"))
        if result.scalar() > 0:
            print(f"  ⚠️  ask_ai_queries.parsed_intent: Still has NULL values")
            verification_passed = False
        else:
            print(f"  ✅ ask_ai_queries.parsed_intent: All fixed")
        
        # Check analysis_run_status
        result = await db.execute(text("SELECT COUNT(*) FROM analysis_run_status WHERE finished_at IS NULL"))
        if result.scalar() > 0:
            print(f"  ⚠️  analysis_run_status.finished_at: Still has NULL values")
            verification_passed = False
        else:
            print(f"  ✅ analysis_run_status.finished_at: All fixed")
        
        print()
        if verification_passed:
            print("✅ All critical issues have been fixed!")
        else:
            print("⚠️  Some issues remain - may require schema changes")
        
        await engine.dispose()
        return verification_passed

async def main():
    """Main entry point"""
    try:
        success = await fix_database_quality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

