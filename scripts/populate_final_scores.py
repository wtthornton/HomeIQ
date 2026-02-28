#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Final Scores for Synergies

Calculates final_score from embedding_similarity and rerank_score for n-level synergies.
Formula: final_score = 0.5 * embedding_similarity + 0.5 * rerank_score
"""

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

def populate_final_scores(pg_url: str, dry_run: bool = False):
    """Populate final_score from embedding_similarity and rerank_score."""
    print(f"{'[DRY RUN] ' if dry_run else ''}Populating final scores...")
    print(f"Database: {pg_url}\n")

    conn = psycopg2.connect(pg_url)
    cursor = conn.cursor()

    try:
        # Find synergies with both embedding_similarity and rerank_score
        cursor.execute("""
            SELECT
                synergy_id,
                embedding_similarity,
                rerank_score,
                final_score
            FROM patterns.synergy_opportunities
            WHERE embedding_similarity IS NOT NULL
            AND rerank_score IS NOT NULL
            AND (final_score IS NULL OR final_score = 0.0)
        """)

        synergies = cursor.fetchall()
        total = len(synergies)

        print(f"Found {total} synergies with embedding_similarity and rerank_score (but no final_score)")

        if total == 0:
            print("✅ All synergies with embedding/rerank scores already have final_score")
            return {
                'total': 0,
                'updated': 0,
                'errors': 0
            }

        updated_count = 0
        error_count = 0

        for row in synergies:
            synergy_id, embedding_sim, rerank, current_final = row

            try:
                # Calculate final_score: 0.5 * embedding + 0.5 * rerank
                final_score = 0.5 * float(embedding_sim) + 0.5 * float(rerank)

                if dry_run:
                    print(f"  [WOULD UPDATE] {synergy_id}: final_score={final_score:.4f} (embedding={embedding_sim:.4f}, rerank={rerank:.4f})")
                else:
                    cursor.execute("""
                        UPDATE patterns.synergy_opportunities
                        SET final_score = %s
                        WHERE synergy_id = %s
                    """, (final_score, synergy_id))

                updated_count += 1

            except Exception as e:
                error_count += 1
                print(f"  ❌ Error processing {synergy_id}: {e}")
                continue

        if not dry_run:
            conn.commit()
        else:
            conn.rollback()

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Complete!")
        print(f"  Total: {total}")
        print(f"  Updated: {updated_count}")
        print(f"  Errors: {error_count}")

        return {
            'total': total,
            'updated': updated_count,
            'errors': error_count
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
    import argparse
    parser = argparse.ArgumentParser(description='Populate final scores for synergies')
    parser.add_argument('--pg-url', type=str, default=POSTGRES_URL,
                       help='PostgreSQL connection URL')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying them')

    args = parser.parse_args()

    populate_final_scores(args.pg_url, dry_run=args.dry_run)

    if args.dry_run:
        print("\n⚠️  This was a dry run. Remove --dry-run to apply changes.")

if __name__ == '__main__':
    main()
