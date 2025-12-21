#!/usr/bin/env python3
"""
Check InfluxDB for data quality issues.

This script:
1. Checks bucket configuration and retention policies
2. Analyzes data volume and distribution
3. Identifies missing or incomplete data
4. Checks for data gaps
5. Validates schema consistency
6. Provides recommendations

Usage:
    docker exec homeiq-influxdb python /app/check_influxdb_quality.py
    OR
    python scripts/check_influxdb_quality.py
    OR with specific checks:
    python scripts/check_influxdb_quality.py --checks connection,buckets,data_volume
"""
import sys
import argparse

from quality_checks.influxdb_common import get_influxdb_config
from quality_checks.runner import InfluxDBCheckRunner


def format_results(results):
    """Format check results for display."""
    config = get_influxdb_config()
    
    print("=" * 80)
    print("INFLUXDB QUALITY CHECK")
    print("=" * 80)
    print()
    print(f"URL: {config['url']}")
    print(f"Org: {config['org']}")
    print(f"Primary Bucket: {config['bucket']}")
    print()
    
    step_num = 1
    for check in results:
        print(f"Step {step_num}: {check.check_name.replace('_', ' ').title()}")
        print("-" * 80)
        
        if check.info:
            for info_item in check.info:
                print(f"  ✅ {info_item}")
        
        if check.issues:
            for issue in check.issues:
                print(f"  ❌ {issue}")
        
        if check.warnings:
            for warning in check.warnings:
                print(f"  ⚠️  {warning}")
        
        print()
        step_num += 1
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    total_issues = sum(len(r.issues) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    
    print(f"📊 Checks run: {len(results)}")
    print(f"❌ Issues: {total_issues}")
    print(f"⚠️  Warnings: {total_warnings}")
    print()
    
    if total_issues == 0 and total_warnings == 0:
        print("✅ InfluxDB looks healthy! No issues found.")
    elif total_issues == 0:
        print("✅ No critical issues found (warnings only)")
    else:
        print("❌ Critical issues found - review above")
        print()
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        print("🔧 Fix Critical Issues:")
        for result in results:
            for issue in result.issues:
                if "No data found" in issue:
                    print("  - Investigate ingestion pipeline - check websocket-ingestion logs")
                elif "bucket not found" in issue.lower():
                    print(f"  - Create missing bucket: {config['bucket']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check InfluxDB for data quality issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all checks
  python scripts/check_influxdb_quality.py
  
  # Run specific checks only
  python scripts/check_influxdb_quality.py --checks connection,buckets,data_volume
        """
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
    
    runner = InfluxDBCheckRunner(enabled_checks=enabled_checks)
    results = runner.run_checks()
    
    format_results(results)
    
    total_issues = sum(len(r.issues) for r in results)
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
