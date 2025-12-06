#!/usr/bin/env python3
"""
Check database for bad or incomplete data (2025 Edition - Multi-Database Support).

This script:
1. Checks all SQLite databases in the project for data quality issues
2. Identifies missing required fields
3. Finds orphaned records
4. Checks for inconsistent data
5. Provides recommendations

Supported Databases (2025):
- ai_automation.db (ai-automation-service)
- metadata.db (data-api) - Epic 22
- ha_ai_agent.db (ha-ai-agent-service)
- proactive_agent.db (proactive-agent-service)
- device_intelligence.db (device-intelligence-service)
- ha-setup.db (ha-setup-service)
- automation_miner.db (automation-miner)

Usage:
    python scripts/check_database_quality.py [database_name]
    # Or check all databases:
    python scripts/check_database_quality.py --all
"""
import asyncio
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Optional

# Add /app/src to path for imports (works both locally and in Docker)
script_dir = Path(__file__).parent

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Database configurations (2025)
DATABASE_CONFIGS = {
    'ai_automation': {
        'name': 'AI Automation Service',
        'paths': [
            '/app/data/ai_automation.db',
            'services/ai-automation-service/data/ai_automation.db',
            'data/ai_automation.db',
        ],
        'service': 'ai-automation-service'
    },
    'metadata': {
        'name': 'Data API (Metadata)',
        'paths': [
            '/app/data/metadata.db',
            'services/data-api/data/metadata.db',
            'data/metadata.db',
        ],
        'service': 'data-api'
    },
    'ha_ai_agent': {
        'name': 'HA AI Agent Service',
        'paths': [
            '/app/data/ha_ai_agent.db',
            'services/ha-ai-agent-service/data/ha_ai_agent.db',
            'data/ha_ai_agent.db',
        ],
        'service': 'ha-ai-agent-service'
    },
    'proactive_agent': {
        'name': 'Proactive Agent Service',
        'paths': [
            '/app/data/proactive_agent.db',
            'services/proactive-agent-service/data/proactive_agent.db',
            'data/proactive_agent.db',
        ],
        'service': 'proactive-agent-service'
    },
    'device_intelligence': {
        'name': 'Device Intelligence Service',
        'paths': [
            '/app/data/device_intelligence.db',
            'services/device-intelligence-service/data/device_intelligence.db',
            'data/device_intelligence.db',
        ],
        'service': 'device-intelligence-service'
    },
    'ha-setup': {
        'name': 'HA Setup Service',
        'paths': [
            '/app/data/ha-setup.db',
            'services/ha-setup-service/data/ha-setup.db',
            'data/ha-setup.db',
        ],
        'service': 'ha-setup-service'
    },
    'automation_miner': {
        'name': 'Automation Miner',
        'paths': [
            '/app/data/automation_miner.db',
            'services/automation-miner/data/automation_miner.db',
            'data/automation_miner.db',
        ],
        'service': 'automation-miner'
    },
}

def find_database_path(db_key: str) -> Optional[Path]:
    """Find database file path using multiple possible locations"""
    config = DATABASE_CONFIGS.get(db_key)
    if not config:
        return None
    
    for path_str in config['paths']:
        path = Path(path_str)
        # Handle absolute paths
        if path.is_absolute():
            if path.exists():
                return path
        # Handle relative paths from script directory
        else:
            # Try from script directory
            full_path = script_dir.parent / path
            if full_path.exists():
                return full_path
            # Try from current directory
            if path.exists():
                return path
    
    return None

async def check_database_quality(db_key: str, db_path: Path, db_name: str):
    """Check a single database for data quality issues"""
    print("=" * 80)
    print(f"DATABASE QUALITY CHECK: {db_name}")
    print(f"Path: {db_path}")
    print("=" * 80)
    print()
    
    # Use absolute path for SQLite
    abs_path = db_path.resolve()
    database_url = f"sqlite+aiosqlite:///{abs_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    issues = []
    warnings = []
    info = []
    
    try:
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
        
        return {
            'db_name': db_name,
            'db_path': str(db_path),
            'issues': issues,
            'warnings': warnings,
            'info': info
        }
    except Exception as e:
        print(f"❌ ERROR checking {db_name}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {
            'db_name': db_name,
            'db_path': str(db_path),
            'error': str(e),
            'issues': [],
            'warnings': [],
            'info': []
        }

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check SQLite database quality (2025 Edition)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all databases
  python scripts/check_database_quality.py --all
  
  # Check specific database
  python scripts/check_database_quality.py ai_automation
  
  # List available databases
  python scripts/check_database_quality.py --list
        """
    )
    parser.add_argument(
        'database',
        nargs='?',
        help='Database key to check (ai_automation, metadata, ha_ai_agent, etc.)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Check all databases'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available databases'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available databases:")
        print("=" * 80)
        for key, config in DATABASE_CONFIGS.items():
            print(f"  {key:20} - {config['name']} ({config['service']})")
        return
    
    if args.all:
        # Check all databases
        print("=" * 80)
        print("MULTI-DATABASE QUALITY CHECK (2025)")
        print("=" * 80)
        print()
        
        results = []
        for db_key in DATABASE_CONFIGS.keys():
            db_path = find_database_path(db_key)
            if db_path:
                config = DATABASE_CONFIGS[db_key]
                result = await check_database_quality(db_key, db_path, config['name'])
                results.append(result)
                print()  # Blank line between databases
            else:
                print(f"⚠️  {DATABASE_CONFIGS[db_key]['name']}: Database not found (skipping)")
                print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY - ALL DATABASES")
        print("=" * 80)
        print()
        
        total_issues = sum(len(r.get('issues', [])) for r in results)
        total_warnings = sum(len(r.get('warnings', [])) for r in results)
        databases_checked = len([r for r in results if 'error' not in r])
        databases_with_errors = len([r for r in results if 'error' in r])
        
        print(f"Databases checked: {databases_checked}")
        if databases_with_errors > 0:
            print(f"Databases with errors: {databases_with_errors}")
        print(f"Total issues: {total_issues}")
        print(f"Total warnings: {total_warnings}")
        print()
        
        if total_issues == 0 and total_warnings == 0:
            print("✅ All databases look healthy!")
        else:
            print("📊 Issues by database:")
            for result in results:
                if 'error' not in result:
                    issue_count = len(result.get('issues', []))
                    warning_count = len(result.get('warnings', []))
                    if issue_count > 0 or warning_count > 0:
                        print(f"  - {result['db_name']}: {issue_count} issues, {warning_count} warnings")
        
    elif args.database:
        # Check specific database
        db_key = args.database
        if db_key not in DATABASE_CONFIGS:
            print(f"❌ ERROR: Unknown database '{db_key}'")
            print(f"Available databases: {', '.join(DATABASE_CONFIGS.keys())}")
            sys.exit(1)
        
        db_path = find_database_path(db_key)
        if not db_path:
            print(f"❌ ERROR: Database '{db_key}' not found")
            print(f"Checked paths: {DATABASE_CONFIGS[db_key]['paths']}")
            sys.exit(1)
        
        config = DATABASE_CONFIGS[db_key]
        result = await check_database_quality(db_key, db_path, config['name'])
        
        if result.get('error'):
            sys.exit(1)
        elif result.get('issues'):
            sys.exit(1)
        else:
            sys.exit(0)
    else:
        # Default: check ai_automation (backward compatibility)
        db_key = 'ai_automation'
        db_path = find_database_path(db_key)
        if not db_path:
            print("❌ ERROR: ai_automation.db not found")
            print("Use --list to see available databases")
            print("Use --all to check all databases")
            sys.exit(1)
        
        config = DATABASE_CONFIGS[db_key]
        result = await check_database_quality(db_key, db_path, config['name'])
        
        if result.get('error'):
            sys.exit(1)
        elif result.get('issues'):
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())

