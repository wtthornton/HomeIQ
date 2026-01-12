#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Device Chain Quality Scoring Discrepancy

Investigates why device_chain synergies have lower quality scores despite higher impact.
"""

import sqlite3
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def analyze_device_chain_scoring(db_path: str):
    """Analyze device_chain vs device_pair scoring differences."""
    print("Analyzing device_chain quality scoring discrepancy...\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Compare overall averages
        print("=" * 70)
        print("Overall Comparison")
        print("=" * 70)
        cursor.execute("""
            SELECT 
                synergy_type,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality,
                AVG(impact_score) as avg_impact,
                AVG(confidence) as avg_confidence,
                AVG(pattern_support_score) as avg_pattern_support
            FROM synergy_opportunities
            WHERE synergy_type IN ('device_pair', 'device_chain')
            GROUP BY synergy_type
        """)
        
        for row in cursor.fetchall():
            print(f"\n{row[0]}:")
            print(f"  Count: {row[1]}")
            print(f"  Avg Quality: {row[2]:.4f}")
            print(f"  Avg Impact: {row[3]:.4f}")
            print(f"  Avg Confidence: {row[4]:.4f}")
            print(f"  Avg Pattern Support: {row[5]:.4f}")
        
        # Complexity distribution
        print("\n" + "=" * 70)
        print("Complexity Distribution")
        print("=" * 70)
        cursor.execute("""
            SELECT 
                synergy_type,
                complexity,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality,
                AVG(impact_score) as avg_impact
            FROM synergy_opportunities
            WHERE synergy_type IN ('device_pair', 'device_chain')
            GROUP BY synergy_type, complexity
            ORDER BY synergy_type, complexity
        """)
        
        print(f"\n{'Type':<15} | {'Complexity':<10} | {'Count':<6} | {'Avg Quality':<12} | {'Avg Impact':<12}")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"{row[0]:<15} | {str(row[1]):<10} | {row[2]:<6} | {row[3]:<12.4f} | {row[4]:<12.4f}")
        
        # Validation status
        print("\n" + "=" * 70)
        print("Validation Status")
        print("=" * 70)
        cursor.execute("""
            SELECT 
                synergy_type,
                validated_by_patterns,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality,
                AVG(pattern_support_score) as avg_pattern_support
            FROM synergy_opportunities
            WHERE synergy_type IN ('device_pair', 'device_chain')
            GROUP BY synergy_type, validated_by_patterns
            ORDER BY synergy_type, validated_by_patterns
        """)
        
        print(f"\n{'Type':<15} | {'Validated':<9} | {'Count':<6} | {'Avg Quality':<12} | {'Avg Pattern':<12}")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"{row[0]:<15} | {str(row[1]):<9} | {row[2]:<6} | {row[3]:<12.4f} | {row[4]:<12.4f}")
        
        # Sample device_chain synergies with breakdown
        print("\n" + "=" * 70)
        print("Sample Device Chain Synergies (Top 10 by Impact)")
        print("=" * 70)
        cursor.execute("""
            SELECT 
                synergy_id,
                impact_score,
                confidence,
                complexity,
                pattern_support_score,
                validated_by_patterns,
                quality_score
            FROM synergy_opportunities
            WHERE synergy_type = 'device_chain'
            ORDER BY impact_score DESC
            LIMIT 10
        """)
        
        print(f"\n{'ID':<40} | {'Impact':<8} | {'Conf':<6} | {'Complex':<8} | {'Pattern':<8} | {'Valid':<6} | {'Quality':<8}")
        print("-" * 100)
        for row in cursor.fetchall():
            print(f"{row[0]:<40} | {row[1]:<8.4f} | {row[2]:<6.4f} | {str(row[3]):<8} | {row[4]:<8.4f} | {str(row[5]):<6} | {row[6]:<8.4f}")
        
        # Calculate expected quality scores (for comparison)
        print("\n" + "=" * 70)
        print("Quality Score Formula Analysis")
        print("=" * 70)
        print("\nFormula: Base(60%) + Validation(25%) + Complexity(15%)")
        print("  Base = impact*0.25 + confidence*0.20 + pattern_support*0.15")
        print("  Validation = pattern_validation*0.10 + active_devices*0.10 + blueprint*0.05")
        print("  Complexity: low=+0.15, medium=0.0, high=-0.15\n")
        
        # Calculate expected scores for device_chain with different complexities
        cursor.execute("""
            SELECT 
                complexity,
                AVG(impact_score) as avg_impact,
                AVG(confidence) as avg_conf,
                AVG(pattern_support_score) as avg_pattern,
                AVG(CASE WHEN validated_by_patterns THEN 1.0 ELSE 0.0 END) as validation_rate
            FROM synergy_opportunities
            WHERE synergy_type = 'device_chain'
            GROUP BY complexity
        """)
        
        print("Expected Quality Scores (device_chain by complexity):")
        print(f"{'Complexity':<10} | {'Base':<8} | {'Validation':<12} | {'Complex Adj':<12} | {'Expected':<10}")
        print("-" * 60)
        for row in cursor.fetchall():
            complexity = row[0] or 'medium'
            avg_impact = row[1] or 0.5
            avg_conf = row[2] or 0.7
            avg_pattern = row[3] or 0.0
            validation_rate = row[4] or 0.0
            
            # Base score (60%)
            base = avg_impact * 0.25 + avg_conf * 0.20 + avg_pattern * 0.15
            
            # Validation bonus (25%) - assume no active_devices or blueprint for now
            validation_bonus = validation_rate * 0.10  # Only pattern validation
            
            # Complexity adjustment (15%)
            if complexity == 'low':
                complex_adj = 0.15
            elif complexity == 'high':
                complex_adj = -0.15
            else:
                complex_adj = 0.0
            
            expected = base + validation_bonus + complex_adj
            
            print(f"{complexity:<10} | {base:<8.4f} | {validation_bonus:<12.4f} | {complex_adj:<12.4f} | {expected:<10.4f}")
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Analyze device_chain quality scoring')
    parser.add_argument('--db-path', type=str, default='/app/data/ai_automation.db',
                       help='Path to SQLite database file')
    
    args = parser.parse_args()
    
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"ERROR: Database file does not exist: {db_path}")
        sys.exit(1)
    
    analyze_device_chain_scoring(str(db_path))

if __name__ == '__main__':
    main()
