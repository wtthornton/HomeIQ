#!/usr/bin/env python3
"""
Backfill Quality Scores for Existing Synergies

2025 Enhancement: Calculates quality_score and quality_tier for all existing synergies
in the database that don't have quality scores yet.

Usage:
    python scripts/backfill_quality_scores.py [--db-path /path/to/database.db] [--dry-run]
"""

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root and service src to path
project_root = Path(__file__).parent.parent.parent.parent
service_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(service_root / "src"))

# Import SynergyQualityScorer
from services.synergy_quality_scorer import SynergyQualityScorer


async def backfill_quality_scores(db_path: str, dry_run: bool = False, batch_size: int = 100) -> Dict[str, Any]:
    """
    Calculate and update quality scores for all existing synergies.
    
    Args:
        db_path: Path to SQLite database file
        dry_run: If True, only show what would be updated without making changes
        batch_size: Number of synergies to process in each batch
    
    Returns:
        Dictionary with statistics: {
            'total_synergies': int,
            'updated_count': int,
            'skipped_count': int,
            'error_count': int,
            'tier_distribution': dict
        }
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}Backfilling quality scores for existing synergies...")
    print(f"Database: {db_path}")
    print(f"Batch size: {batch_size}\n")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    scorer = SynergyQualityScorer()
    
    try:
        # Check if quality_score column exists
        cursor.execute("PRAGMA table_info(synergy_opportunities)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'quality_score' not in columns:
            print("ERROR: quality_score column does not exist!")
            print("Please run scripts/add_quality_columns.py first to add the columns.")
            sys.exit(1)
        
        # Fetch all synergies without quality scores (or with NULL quality scores)
        cursor.execute("""
            SELECT 
                synergy_id,
                impact_score,
                confidence,
                complexity,
                pattern_support_score,
                validated_by_patterns,
                device_ids,
                opportunity_metadata,
                area,
                quality_score
            FROM synergy_opportunities
            WHERE quality_score IS NULL OR quality_score = 0.0
        """)
        
        synergies = cursor.fetchall()
        total_synergies = len(synergies)
        
        print(f"Found {total_synergies} synergies without quality scores")
        
        if total_synergies == 0:
            print("✅ All synergies already have quality scores (nothing to do)")
            return {
                'total_synergies': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'error_count': 0,
                'tier_distribution': {}
            }
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        tier_distribution = {'high': 0, 'medium': 0, 'low': 0, 'poor': 0}
        
        # Process in batches
        for batch_start in range(0, total_synergies, batch_size):
            batch_end = min(batch_start + batch_size, total_synergies)
            batch = synergies[batch_start:batch_end]
            
            print(f"Processing batch {batch_start // batch_size + 1} ({batch_start + 1}-{batch_end} of {total_synergies})...")
            
            for row in batch:
                try:
                    # Convert row to dictionary format expected by scorer
                    synergy_dict: Dict[str, Any] = {
                        'synergy_id': row['synergy_id'],
                        'impact_score': row['impact_score'] or 0.5,
                        'confidence': row['confidence'] or 0.5,
                        'complexity': row['complexity'] or 'medium',
                        'pattern_support_score': row['pattern_support_score'] or 0.0,
                        'validated_by_patterns': bool(row['validated_by_patterns']) if row['validated_by_patterns'] is not None else False,
                    }
                    
                    # Parse device_ids if it's a string
                    device_ids = row['device_ids']
                    if isinstance(device_ids, str):
                        try:
                            device_ids = json.loads(device_ids)
                        except (json.JSONDecodeError, TypeError):
                            device_ids = []
                    synergy_dict['device_ids'] = device_ids if isinstance(device_ids, list) else []
                    
                    # Parse opportunity_metadata if it's a string
                    metadata = row['opportunity_metadata']
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except (json.JSONDecodeError, TypeError):
                            metadata = {}
                    synergy_dict['opportunity_metadata'] = metadata if isinstance(metadata, dict) else {}
                    
                    # Calculate quality score
                    quality_result = scorer.calculate_quality_score(synergy_dict)
                    quality_score = quality_result['quality_score']
                    quality_tier = quality_result['quality_tier']
                    
                    # Update database
                    if dry_run:
                        print(f"  [WOULD UPDATE] {row['synergy_id']}: quality_score={quality_score:.4f}, tier={quality_tier}")
                    else:
                        cursor.execute("""
                            UPDATE synergy_opportunities
                            SET quality_score = ?,
                                quality_tier = ?,
                                last_validated_at = ?
                            WHERE synergy_id = ?
                        """, (
                            quality_score,
                            quality_tier,
                            datetime.now(timezone.utc).isoformat(),
                            row['synergy_id']
                        ))
                    
                    updated_count += 1
                    tier_distribution[quality_tier] = tier_distribution.get(quality_tier, 0) + 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Error processing {row['synergy_id']}: {e}")
                    continue
            
            # Commit batch
            if not dry_run:
                conn.commit()
        
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Backfill complete!")
        print(f"  Total synergies: {total_synergies}")
        print(f"  Updated: {updated_count}")
        print(f"  Errors: {error_count}")
        print(f"\nTier distribution:")
        for tier, count in sorted(tier_distribution.items(), key=lambda x: ['high', 'medium', 'low', 'poor'].index(x[0])):
            if count > 0:
                print(f"  {tier}: {count}")
        
        return {
            'total_synergies': total_synergies,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'tier_distribution': tier_distribution
        }
        
    except sqlite3.Error as e:
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
        description='Backfill quality scores for existing synergies'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='/app/data/ai_automation.db',
        help='Path to SQLite database file (default: /app/data/ai_automation.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of synergies to process per batch (default: 100)'
    )
    
    args = parser.parse_args()
    
    # Check if database file exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: Database file does not exist: {db_path}")
        print("Hint: Use --db-path to specify the correct path")
        sys.exit(1)
    
    result = asyncio.run(backfill_quality_scores(
        str(db_path),
        dry_run=args.dry_run,
        batch_size=args.batch_size
    ))
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. Remove --dry-run to apply changes.")


if __name__ == '__main__':
    main()
