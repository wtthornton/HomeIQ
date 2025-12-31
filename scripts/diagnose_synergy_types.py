#!/usr/bin/env python3
"""
Diagnose Synergy Types Issue

Analyzes why all synergies have synergy_type='event_context' instead of
'device_pair' or 'device_chain'.
"""

import sqlite3
import json
import sys
from pathlib import Path

def analyze_synergy_types(db_path: str):
    """Analyze synergy types in database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("Synergy Types Analysis")
    print("=" * 80)
    
    # Check synergy types
    cursor = conn.execute("""
        SELECT 
            synergy_type,
            COUNT(*) as count,
            AVG(impact_score) as avg_impact,
            AVG(confidence) as avg_confidence,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created
        FROM synergy_opportunities
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
    cursor = conn.execute("""
        SELECT 
            synergy_depth,
            COUNT(*) as count
        FROM synergy_opportunities
        GROUP BY synergy_depth
        ORDER BY synergy_depth
    """)
    
    print("Synergy Depth Distribution:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"Depth {row['synergy_depth']}: {row['count']} synergies")
    print()
    
    # Sample synergies by type
    cursor = conn.execute("""
        SELECT 
            synergy_id,
            synergy_type,
            synergy_depth,
            device_ids,
            opportunity_metadata,
            impact_score,
            confidence,
            created_at
        FROM synergy_opportunities
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
            except:
                device_ids = device_ids[:50]
        
        metadata = row['opportunity_metadata']
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
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
    cursor = conn.execute("""
        SELECT COUNT(*) as count
        FROM synergy_opportunities
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
    parser.add_argument('--db-path', default='data/ai_automation.db', help='Database path')
    parser.add_argument('--docker-container', default='ai-pattern-service', help='Docker container')
    parser.add_argument('--use-docker-db', action='store_true', help='Copy from Docker')
    
    args = parser.parse_args()
    
    db_path = args.db_path
    
    if args.use_docker_db:
        import subprocess
        import tempfile
        from pathlib import Path
        
        temp_dir = tempfile.mkdtemp(prefix='synergy_diagnose_')
        temp_db_path = Path(temp_dir) / 'ai_automation.db'
        
        try:
            subprocess.run([
                'docker', 'cp',
                f'{args.docker_container}:/app/data/ai_automation.db',
                str(temp_db_path)
            ], check=True, capture_output=True)
            db_path = str(temp_db_path)
            print(f"Copied database from Docker to: {db_path}\n")
        except Exception as e:
            print(f"Failed to copy database: {e}")
            sys.exit(1)
    
    analyze_synergy_types(db_path)
