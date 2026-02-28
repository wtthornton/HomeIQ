#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Low Quality Synergies

Removes synergies with quality_score < 0.50 (below medium quality threshold).
Part of storage strategy optimization to focus on useful synergies for automation creation.

Usage:
    python scripts/cleanup_low_quality_synergies.py [--pg-url URL] [--dry-run]
"""

import argparse
import os
import sys

import psycopg2

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

def cleanup_low_quality_synergies(pg_url: str, min_quality_score: float = 0.50, dry_run: bool = False):
    """Remove synergies with quality_score below threshold."""
    print(f"{'[DRY RUN] ' if dry_run else ''}Cleaning up low-quality synergies...")
    print(f"Database: {pg_url}")
    print(f"Threshold: quality_score < {min_quality_score}\n")

    conn = psycopg2.connect(pg_url)
    cursor = conn.cursor()

    try:
        # Count synergies to be removed
        cursor.execute("""
            SELECT COUNT(*)
            FROM patterns.synergy_opportunities
            WHERE quality_score < %s
        """, (min_quality_score,))

        count_to_remove = cursor.fetchone()[0]

        # Get breakdown by quality tier
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score >= 0.70 THEN 'high'
                    WHEN quality_score >= 0.50 THEN 'medium'
                    WHEN quality_score >= 0.30 THEN 'low'
                    ELSE 'poor'
                END as tier,
                COUNT(*) as count,
                AVG(quality_score) as avg_score,
                AVG(impact_score) as avg_impact
            FROM patterns.synergy_opportunities
            WHERE quality_score < %s
            GROUP BY tier
        """, (min_quality_score,))

        breakdown = cursor.fetchall()

        print(f"Synergies to remove: {count_to_remove}")
        print("\nBreakdown by tier:")
        print(f"{'Tier':<10} | {'Count':<8} | {'Avg Quality':<12} | {'Avg Impact':<12}")
        print("-" * 50)
        for row in breakdown:
            print(f"{row[0]:<10} | {row[1]:<8} | {row[2]:<12.4f} | {row[3]:<12.4f}")

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM patterns.synergy_opportunities")
        total_before = cursor.fetchone()[0]
        total_after = total_before - count_to_remove

        print(f"\nBefore: {total_before:,} synergies")
        print(f"After:  {total_after:,} synergies")
        print(f"Remove: {count_to_remove:,} synergies ({count_to_remove/total_before*100:.1f}%)")

        if count_to_remove == 0:
            print("\n✅ No synergies to remove (all meet quality threshold)")
            return {
                'removed': 0,
                'before': total_before,
                'after': total_after
            }

        if dry_run:
            print(f"\n⚠️  [DRY RUN] Would remove {count_to_remove:,} synergies")
            conn.rollback()
            return {
                'removed': 0,
                'before': total_before,
                'after': total_after
            }

        # Remove low-quality synergies
        print(f"\nRemoving {count_to_remove:,} low-quality synergies...")
        cursor.execute("""
            DELETE FROM patterns.synergy_opportunities
            WHERE quality_score < %s
        """, (min_quality_score,))

        removed_count = cursor.rowcount
        conn.commit()

        # Verify
        cursor.execute("SELECT COUNT(*) FROM patterns.synergy_opportunities")
        total_after_verify = cursor.fetchone()[0]

        print(f"\n✅ Cleanup complete!")
        print(f"  Removed: {removed_count:,} synergies")
        print(f"  Remaining: {total_after_verify:,} synergies")

        return {
            'removed': removed_count,
            'before': total_before,
            'after': total_after_verify
        }

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cleanup low-quality synergies (quality_score < 0.50)'
    )
    parser.add_argument(
        '--pg-url',
        type=str,
        default=POSTGRES_URL,
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--min-quality',
        type=float,
        default=0.50,
        help='Minimum quality score threshold (default: 0.50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )

    args = parser.parse_args()

    result = cleanup_low_quality_synergies(
        args.pg_url,
        min_quality_score=args.min_quality,
        dry_run=args.dry_run
    )

    if args.dry_run:
        print("\n⚠️  This was a dry run. Remove --dry-run to apply changes.")

if __name__ == '__main__':
    main()
