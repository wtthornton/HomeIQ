#!/usr/bin/env python3
"""Check synergy types in the database."""

import sqlite3
import sys

# Database path (adjust as needed)
DB_PATH = "/app/data/ai_automation.db"

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        # Check synergy_opportunities table
        if ('synergy_opportunities',) in tables:
            # Get synergy types and depths
            cursor.execute("""
                SELECT synergy_type, synergy_depth, COUNT(*) as count
                FROM synergy_opportunities 
                GROUP BY synergy_type, synergy_depth
                ORDER BY count DESC
            """)
            results = cursor.fetchall()
            print(f"\nSynergy Types and Depths:")
            for row in results:
                print(f"  Type: {row[0]}, Depth: {row[1]}, Count: {row[2]}")
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
            total = cursor.fetchone()[0]
            print(f"\nTotal synergies: {total}")
            
            # Sample a few synergies
            cursor.execute("""
                SELECT synergy_id, synergy_type, synergy_depth, device_ids, confidence
                FROM synergy_opportunities 
                LIMIT 5
            """)
            samples = cursor.fetchall()
            print(f"\nSample synergies:")
            for s in samples:
                print(f"  ID: {s[0][:20]}..., Type: {s[1]}, Depth: {s[2]}, Confidence: {s[4]}")
            
            # Check for scene_based and context_aware synergies
            for synergy_type in ['scene_based', 'context_aware']:
                cursor.execute("""
                    SELECT synergy_id, device_ids, confidence, opportunity_metadata
                    FROM synergy_opportunities 
                    WHERE synergy_type = ?
                    LIMIT 3
                """, (synergy_type,))
                samples = cursor.fetchall()
                if samples:
                    print(f"\n{synergy_type} samples:")
                    for s in samples:
                        print(f"  ID: {s[0][:20]}..., Devices: {s[1][:50]}..., Confidence: {s[2]}")
                else:
                    print(f"\nNo {synergy_type} synergies found")
        else:
            print("synergy_opportunities table not found!")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
