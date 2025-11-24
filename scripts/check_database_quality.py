#!/usr/bin/env python3
"""
Check database for bad or incomplete data.

This script:
1. Checks all tables for data quality issues
2. Identifies missing required fields
3. Finds orphaned records
4. Checks for inconsistent data
5. Provides recommendations

Usage:
    docker exec ai-automation-service python /app/check_database_quality.py
"""
import asyncio
import sys
from pathlib import Path
from collections import defaultdict

# Add /app/src to path for imports (works both locally and in Docker)
script_dir = Path(__file__).parent
if (script_dir.parent / "services" / "ai-automation-service" / "src").exists():
    sys.path.insert(0, str(script_dir.parent / "services" / "ai-automation-service" / "src"))
else:
    sys.path.insert(0, "/app/src")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect

async def check_database_quality():
    """Check database for data quality issues"""
    print("=" * 80)
    print("DATABASE QUALITY CHECK")
    print("=" * 80)
    print()
    
    # Database path
    if Path("/app/data/ai_automation.db").exists():
        db_path = "/app/data/ai_automation.db"
    elif (script_dir.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db").exists():
        db_path = str(script_dir.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db")
    else:
        print("❌ ERROR: Database not found")
        return
    
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    issues = []
    warnings = []
    info = []
    
    async with async_session() as db:
        # Get all tables
        result = await db.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        print()
        
        # Check each table
        for table in tables:
            print(f"Checking table: {table}")
            print("-" * 80)
            
            # Get row count
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            row_count = result.scalar()
            info.append(f"{table}: {row_count} rows")
            
            if row_count == 0:
                print(f"  ⚠️  Table is empty")
                warnings.append(f"{table}: Empty table")
                print()
                continue
            
            # Get table schema
            result = await db.execute(text(f"PRAGMA table_info({table})"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]
            nullable_cols = [col[1] for col in columns if col[3] == 0]  # NOT NULL columns
            
            # Check for NULL values in NOT NULL columns (if any)
            for col in nullable_cols:
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"))
                null_count = result.scalar()
                if null_count > 0:
                    issues.append(f"{table}.{col}: {null_count} NULL values in NOT NULL column")
                    print(f"  ❌ {col}: {null_count} NULL values in NOT NULL column")
            
            # Table-specific checks
            if table == 'suggestions':
                # Check for suggestions without required fields
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM suggestions 
                    WHERE description_only IS NULL OR description_only = ''
                """))
                empty_desc = result.scalar()
                if empty_desc > 0:
                    issues.append(f"suggestions: {empty_desc} with empty description_only")
                    print(f"  ❌ {empty_desc} suggestions with empty description_only")
                
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM suggestions 
                    WHERE title IS NULL OR title = ''
                """))
                empty_title = result.scalar()
                if empty_title > 0:
                    issues.append(f"suggestions: {empty_title} with empty title")
                    print(f"  ❌ {empty_title} suggestions with empty title")
                
                # Check for orphaned suggestions (pattern_id doesn't exist)
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM suggestions s
                    LEFT JOIN patterns p ON s.pattern_id = p.id
                    WHERE s.pattern_id IS NOT NULL AND p.id IS NULL
                """))
                orphaned = result.scalar()
                if orphaned > 0:
                    issues.append(f"suggestions: {orphaned} orphaned suggestions (pattern_id doesn't exist)")
                    print(f"  ❌ {orphaned} orphaned suggestions (pattern_id doesn't exist)")
                
                # Check status distribution
                result = await db.execute(text("""
                    SELECT status, COUNT(*) as count 
                    FROM suggestions 
                    GROUP BY status
                """))
                status_dist = result.fetchall()
                print(f"  📊 Status distribution:")
                for status, count in status_dist:
                    print(f"     - {status or 'NULL'}: {count}")
            
            elif table == 'patterns':
                # Check for patterns with invalid confidence
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM patterns 
                        WHERE confidence < 0 OR confidence > 1
                    """))
                    invalid_conf = result.scalar()
                    if invalid_conf > 0:
                        issues.append(f"patterns: {invalid_conf} with invalid confidence (not 0-1)")
                        print(f"  ❌ {invalid_conf} patterns with invalid confidence")
                except Exception:
                    pass  # Column might not exist
                
                # Check pattern_metadata
                try:
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM patterns 
                        WHERE pattern_metadata IS NULL
                    """))
                    empty_metadata = result.scalar()
                    if empty_metadata > 0:
                        warnings.append(f"patterns: {empty_metadata} with NULL pattern_metadata")
                        print(f"  ⚠️  {empty_metadata} patterns with NULL pattern_metadata")
                except Exception:
                    pass
            
            elif table == 'ask_ai_queries':
                # Check for queries without suggestions
                result = await db.execute(text("""
                    SELECT COUNT(*) FROM ask_ai_queries 
                    WHERE suggestions IS NULL OR suggestions = '[]' OR suggestions = ''
                """))
                empty_suggestions = result.scalar()
                if empty_suggestions > 0:
                    warnings.append(f"ask_ai_queries: {empty_suggestions} queries without suggestions")
                    print(f"  ⚠️  {empty_suggestions} queries without suggestions")
            
            elif 'foreign_key' in table.lower() or 'relationship' in table.lower():
                # Check foreign key integrity
                pass  # SQLite doesn't enforce foreign keys by default
            
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        print("📊 Table Statistics:")
        for stat in info:
            print(f"  - {stat}")
        print()
        
        if issues:
            print(f"❌ ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
            print()
        else:
            print("✅ No critical issues found")
            print()
        
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
            print()
        
        # Recommendations
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        if issues:
            print("🔧 Fix Critical Issues:")
            for issue in issues:
                if "NULL values in NOT NULL column" in issue:
                    table_col = issue.split(":")[0]
                    print(f"  - Fix NULL values in {table_col}")
                elif "orphaned" in issue:
                    print(f"  - Clean up orphaned records: {issue.split(':')[0]}")
                elif "empty" in issue.lower():
                    print(f"  - Fill in missing data: {issue.split(':')[0]}")
            print()
        
        if warnings:
            print("💡 Consider:")
            for warning in warnings:
                if "without suggestions" in warning:
                    print(f"  - Review queries that didn't generate suggestions")
            print()
        
        if not issues and not warnings:
            print("✅ Database looks healthy! No issues found.")
            print()
        
        await engine.dispose()

async def main():
    """Main entry point"""
    try:
        await check_database_quality()
        sys.exit(0)
    except Exception as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

