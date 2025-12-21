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
    # Or with specific checks:
    python scripts/check_database_quality.py --all --checks tables,null_values
"""
import asyncio
import sys
import argparse
from pathlib import Path

# Import from refactored package
from quality_checks.config import DATABASE_CONFIGS
from quality_checks.db_common import find_database_path, list_all_databases
from quality_checks.runner import SQLiteCheckRunner


def format_results(results):
    """Format check results for display."""
    print("=" * 80)
    print(f"DATABASE QUALITY CHECK: {results.db_name}")
    print(f"Path: {results.db_path}")
    print("=" * 80)
    print()
    
    for check in results.checks:
        if check.info:
            for info_item in check.info:
                print(f"  📊 {info_item}")
        if check.issues:
            for issue in check.issues:
                print(f"  ❌ {issue}")
        if check.warnings:
            for warning in check.warnings:
                print(f"  ⚠️  {warning}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    if results.error:
        print(f"❌ ERROR: {results.error}")
        return
    
    print(f"📊 Total checks: {len(results.checks)}")
    print(f"❌ Issues: {results.total_issues}")
    print(f"⚠️  Warnings: {results.total_warnings}")
    print()
    
    if results.total_issues == 0 and results.total_warnings == 0:
        print("✅ Database looks healthy! No issues found.")
    elif results.total_issues == 0:
        print("✅ No critical issues found (warnings only)")
    else:
        print("❌ Critical issues found - review above")


async def check_all_databases(runner):
    """Check all databases."""
    print("=" * 80)
    print("MULTI-DATABASE QUALITY CHECK (2025)")
    print("=" * 80)
    print()
    
    all_results = []
    for db_key in DATABASE_CONFIGS.keys():
        db_path = find_database_path(db_key)
        if db_path:
            config = DATABASE_CONFIGS[db_key]
            results = await runner.run_checks(db_key, db_path, config['name'])
            format_results(results)
            all_results.append(results)
            print()
        else:
            print(f"⚠️  {DATABASE_CONFIGS[db_key]['name']}: Database not found (skipping)")
            print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY - ALL DATABASES")
    print("=" * 80)
    print()
    
    total_issues = sum(r.total_issues for r in all_results)
    total_warnings = sum(r.total_warnings for r in all_results)
    databases_checked = len([r for r in all_results if not r.error])
    databases_with_errors = len([r for r in all_results if r.error])
    
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
        for result in all_results:
            if not result.error and (result.total_issues > 0 or result.total_warnings > 0):
                print(f"  - {result.db_name}: {result.total_issues} issues, {result.total_warnings} warnings")
    
    return 0 if total_issues == 0 else 1


async def check_single_database(runner, db_key):
    """Check a single database."""
    if db_key not in DATABASE_CONFIGS:
        print(f"❌ ERROR: Unknown database '{db_key}'")
        print(f"Available databases: {', '.join(DATABASE_CONFIGS.keys())}")
        return 1
    
    db_path = find_database_path(db_key)
    if not db_path:
        print(f"❌ ERROR: Database '{db_key}' not found")
        print(f"Checked paths: {DATABASE_CONFIGS[db_key]['paths']}")
        return 1
    
    config = DATABASE_CONFIGS[db_key]
    results = await runner.run_checks(db_key, db_path, config['name'])
    format_results(results)
    
    if results.error or results.total_issues > 0:
        return 1
    return 0


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
  
  # Check with specific checks only
  python scripts/check_database_quality.py --all --checks tables,null_values
  
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
    parser.add_argument(
        '--checks',
        type=str,
        help='Comma-separated list of checks to run (default: all)'
    )
    
    args = parser.parse_args()
    
    # Parse enabled checks
    enabled_checks = None
    if args.checks:
        enabled_checks = set(c.strip() for c in args.checks.split(','))
    
    if args.list:
        print("Available databases:")
        print("=" * 80)
        for key, config in DATABASE_CONFIGS.items():
            print(f"  {key:20} - {config['name']} ({config['service']})")
        return
    
    runner = SQLiteCheckRunner(enabled_checks=enabled_checks)
    
    if args.all:
        exit_code = await check_all_databases(runner)
        sys.exit(exit_code)
    elif args.database:
        exit_code = await check_single_database(runner, args.database)
        sys.exit(exit_code)
    else:
        # Default: check ai_automation (backward compatibility)
        exit_code = await check_single_database(runner, 'ai_automation')
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
