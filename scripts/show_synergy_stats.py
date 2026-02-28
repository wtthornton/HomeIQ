#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Show Synergy Statistics by Type and Level

Displays statistics about synergies broken down by:
- Synergy Type (device_pair, device_chain, etc.)
- Synergy Depth/Level (2=pair, 3=chain, 4=4-chain)
- Complexity (low, medium, high)
"""

import os
import sys

import psycopg2
import psycopg2.extras

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

def format_number(num):
    """Format number with commas."""
    return f"{num:,}"

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Show synergy statistics by type and level')
    parser.add_argument('--pg-url', default=POSTGRES_URL, help='PostgreSQL connection URL')
    args = parser.parse_args()

    try:
        conn = psycopg2.connect(args.pg_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        print("=" * 100)
        print("SYNERGY STATISTICS BY TYPE AND LEVEL")
        print("=" * 100)
        print(f"Database: {args.pg_url}\n")

        # Check if table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'patterns' AND table_name = 'synergy_opportunities'
        """)
        if not cursor.fetchone():
            print("[ERROR] synergy_opportunities table not found in patterns schema")
            conn.close()
            sys.exit(1)

        # Get statistics by Type and Depth (Level)
        cursor.execute("""
            SELECT
                synergy_type,
                synergy_depth,
                COUNT(*) as count,
                AVG(impact_score) as avg_impact,
                AVG(confidence) as avg_confidence,
                MIN(impact_score) as min_impact,
                MAX(impact_score) as max_impact
            FROM patterns.synergy_opportunities
            WHERE filter_reason IS NULL
            GROUP BY synergy_type, synergy_depth
            ORDER BY synergy_type, synergy_depth
        """)

        type_depth_stats = cursor.fetchall()

        # Get statistics by Type and Complexity
        cursor.execute("""
            SELECT
                synergy_type,
                complexity,
                COUNT(*) as count,
                AVG(impact_score) as avg_impact,
                AVG(confidence) as avg_confidence
            FROM patterns.synergy_opportunities
            WHERE filter_reason IS NULL
            GROUP BY synergy_type, complexity
            ORDER BY synergy_type, complexity
        """)

        type_complexity_stats = cursor.fetchall()

        # Get total counts
        cursor.execute("SELECT COUNT(*) as count FROM patterns.synergy_opportunities WHERE filter_reason IS NULL")
        total_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(DISTINCT synergy_type) as count FROM patterns.synergy_opportunities WHERE filter_reason IS NULL")
        type_count = cursor.fetchone()['count']

        # Print summary
        print(f"SUMMARY")
        print(f"   Total Synergies: {format_number(total_count)}")
        print(f"   Unique Types: {type_count}\n")

        # Print by Type and Depth
        print("=" * 100)
        print("BY TYPE AND DEPTH (LEVEL)")
        print("=" * 100)
        print(f"{'Type':<20} {'Depth':<8} {'Count':<12} {'Avg Impact':<12} {'Avg Confidence':<15} {'Min Impact':<12} {'Max Impact':<12}")
        print("-" * 100)

        current_type = None
        type_total = 0

        for row in type_depth_stats:
            synergy_type = row['synergy_type']
            depth = row['synergy_depth']
            count = row['count']
            avg_impact = row['avg_impact'] or 0.0
            avg_conf = row['avg_confidence'] or 0.0
            min_impact = row['min_impact'] or 0.0
            max_impact = row['max_impact'] or 0.0

            if current_type != synergy_type:
                if current_type is not None:
                    print(f"{'  └─ Total':<20} {'':<8} {format_number(type_total):<12} {'':<12} {'':<15} {'':<12} {'':<12}")
                    print()
                current_type = synergy_type
                type_total = 0

            type_total += count

            print(f"{synergy_type:<20} {depth:<8} {format_number(count):<12} {avg_impact:.3f}        {avg_conf:.3f}           {min_impact:.3f}        {max_impact:.3f}")

        if current_type is not None:
            print(f"{'  └─ Total':<20} {'':<8} {format_number(type_total):<12} {'':<12} {'':<15} {'':<12} {'':<12}")

        print()

        # Print by Type and Complexity
        print("=" * 100)
        print("BY TYPE AND COMPLEXITY")
        print("=" * 100)
        print(f"{'Type':<20} {'Complexity':<12} {'Count':<12} {'Avg Impact':<12} {'Avg Confidence':<15}")
        print("-" * 100)

        current_type = None
        type_total = 0

        for row in type_complexity_stats:
            synergy_type = row['synergy_type']
            complexity = row['complexity']
            count = row['count']
            avg_impact = row['avg_impact'] or 0.0
            avg_conf = row['avg_confidence'] or 0.0

            if current_type != synergy_type:
                if current_type is not None:
                    print(f"{'  └─ Total':<20} {'':<12} {format_number(type_total):<12} {'':<12} {'':<15}")
                    print()
                current_type = synergy_type
                type_total = 0

            type_total += count

            print(f"{synergy_type:<20} {complexity:<12} {format_number(count):<12} {avg_impact:.3f}        {avg_conf:.3f}")

        if current_type is not None:
            print(f"{'  └─ Total':<20} {'':<12} {format_number(type_total):<12} {'':<12} {'':<15}")

        print()
        print("=" * 100)

        conn.close()

    except psycopg2.Error as e:
        print(f"[ERROR] Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
