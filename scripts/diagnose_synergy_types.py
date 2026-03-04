#!/usr/bin/env python3
"""
Diagnose Synergy Types Issue

Analyzes why all synergies have synergy_type='event_context' instead of
'device_pair' or 'device_chain'.
"""

import json
import os

import psycopg2
import psycopg2.extras

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

def analyze_synergy_types(pg_url: str):
    """Analyze synergy types in database."""
    conn = psycopg2.connect(pg_url)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("=" * 80)
    print("Synergy Types Analysis")
    print("=" * 80)

    # Check synergy types
    cursor.execute("""
        SELECT
            synergy_type,
            COUNT(*) as count,
            AVG(impact_score) as avg_impact,
            AVG(confidence) as avg_confidence,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created
        FROM patterns.synergy_opportunities
        GROUP BY synergy_type
        ORDER BY count DESC
    """)

    print("\nSynergy Types Summary:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"Type: {row['synergy_type']}")
        print(f"  Count: {row['count']}")
        print(f"  Avg Impact: {row['avg_impact']:.2f}")
        print(f"  Avg Confidence: {row['avg_confidence']:.2f}")
        print(f"  First Created: {row['first_created']}")
        print(f"  Last Created: {row['last_created']}")
        print()

    # Check synergy_depth distribution
    cursor.execute("""
        SELECT
            synergy_depth,
            COUNT(*) as count
        FROM patterns.synergy_opportunities
        GROUP BY synergy_depth
        ORDER BY synergy_depth
    """)

    print("Synergy Depth Distribution:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"Depth {row['synergy_depth']}: {row['count']} synergies")
    print()

    # Sample synergies by type
    cursor.execute("""
        SELECT
            synergy_id,
            synergy_type,
            synergy_depth,
            device_ids,
            opportunity_metadata,
            impact_score,
            confidence,
            created_at
        FROM patterns.synergy_opportunities
        ORDER BY created_at DESC
        LIMIT 5
    """)

    print("Sample Synergies (Most Recent):")
    print("-" * 80)
    for row in cursor.fetchall():
        device_ids = row['device_ids']
        if isinstance(device_ids, str):
            try:
                device_ids = json.loads(device_ids)
            except Exception:
                device_ids = device_ids[:50]

        metadata = row['opportunity_metadata']
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = metadata[:100]

        print(f"ID: {row['synergy_id'][:8]}...")
        print(f"  Type: {row['synergy_type']}")
        print(f"  Depth: {row['synergy_depth']}")
        print(f"  Devices: {device_ids if isinstance(device_ids, list) else str(device_ids)[:50]}")
        print(f"  Impact: {row['impact_score']:.2f}, Confidence: {row['confidence']:.2f}")
        if isinstance(metadata, dict):
            print(f"  Relationship: {metadata.get('relationship', 'N/A')}")
            print(f"  Trigger: {metadata.get('trigger_entity', 'N/A')}")
            print(f"  Action: {metadata.get('action_entity', 'N/A')}")
        print()

    # Check if there are any device_pair or device_chain types
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM patterns.synergy_opportunities
        WHERE synergy_type IN ('device_pair', 'device_chain')
    """)
    pair_chain_count = cursor.fetchone()['count']

    print("=" * 80)
    print(f"Total synergies with 'device_pair' or 'device_chain' type: {pair_chain_count}")
    print("=" * 80)

    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Diagnose synergy types issue')
    parser.add_argument('--pg-url', default=POSTGRES_URL, help='PostgreSQL connection URL')
    parser.add_argument('--docker-container', default='ai-pattern-service', help='Docker container')
    parser.add_argument('--use-docker-db', action='store_true', help='Use Docker container database')

    args = parser.parse_args()

    pg_url = args.pg_url

    if args.use_docker_db:
        # When using Docker, connect to PostgreSQL via the container network
        pg_url = "postgresql://homeiq:homeiq@localhost:5432/homeiq"

    analyze_synergy_types(pg_url)
