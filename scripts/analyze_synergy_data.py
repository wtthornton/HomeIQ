#!/usr/bin/env python3
"""
Synergy Data Analysis Script

Analyzes synergy opportunities database to provide detailed insights:
- Impact score distribution
- Area distribution
- Relationship type distribution
- Pattern validation statistics
- Priority scoring recommendations

Usage:
    python scripts/analyze_synergy_data.py
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import statistics

# Database path
DB_PATH = Path(__file__).parent.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db"
if not DB_PATH.exists():
    DB_PATH = Path(__file__).parent.parent / "data" / "ai_automation.db"


def get_impact_distribution(cursor) -> Dict[str, int]:
    """Get distribution of impact scores."""
    cursor.execute("""
        SELECT 
            CASE 
                WHEN impact_score >= 0.8 THEN '80-100%'
                WHEN impact_score >= 0.6 THEN '60-80%'
                WHEN impact_score >= 0.4 THEN '40-60%'
                WHEN impact_score >= 0.2 THEN '20-40%'
                ELSE '0-20%'
            END as impact_range,
            COUNT(*) as count
        FROM synergy_opportunities
        GROUP BY impact_range
        ORDER BY impact_range DESC
    """)
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_area_distribution(cursor, limit: int = 20) -> List[Dict[str, Any]]:
    """Get top areas by synergy count."""
    cursor.execute("""
        SELECT 
            area, 
            COUNT(*) as count, 
            AVG(impact_score) as avg_impact,
            AVG(confidence) as avg_confidence,
            SUM(CASE WHEN validated_by_patterns = 1 THEN 1 ELSE 0 END) as validated_count
        FROM synergy_opportunities
        WHERE area IS NOT NULL AND area != ''
        GROUP BY area
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    
    return [
        {
            'area': row[0],
            'count': row[1],
            'avg_impact': round(row[2], 3) if row[2] else 0,
            'avg_confidence': round(row[3], 3) if row[3] else 0,
            'validated_count': row[4]
        }
        for row in cursor.fetchall()
    ]


def get_relationship_distribution(cursor) -> List[Dict[str, Any]]:
    """Get distribution by relationship type."""
    cursor.execute("""
        SELECT 
            json_extract(opportunity_metadata, '$.relationship') as relationship,
            COUNT(*) as count,
            AVG(impact_score) as avg_impact,
            AVG(confidence) as avg_confidence,
            AVG(pattern_support_score) as avg_pattern_support,
            SUM(CASE WHEN validated_by_patterns = 1 THEN 1 ELSE 0 END) as validated_count
        FROM synergy_opportunities
        WHERE opportunity_metadata IS NOT NULL
        GROUP BY relationship
        ORDER BY count DESC
    """)
    
    return [
        {
            'relationship': row[0] or 'unknown',
            'count': row[1],
            'avg_impact': round(row[2], 3) if row[2] else 0,
            'avg_confidence': round(row[3], 3) if row[3] else 0,
            'avg_pattern_support': round(row[4], 3) if row[4] else 0,
            'validated_count': row[4]
        }
        for row in cursor.fetchall()
    ]


def get_complexity_distribution(cursor) -> Dict[str, int]:
    """Get distribution by complexity."""
    cursor.execute("""
        SELECT complexity, COUNT(*) as count
        FROM synergy_opportunities
        GROUP BY complexity
        ORDER BY complexity
    """)
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_pattern_validation_stats(cursor) -> Dict[str, Any]:
    """Get pattern validation statistics."""
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN validated_by_patterns = 1 THEN 1 ELSE 0 END) as validated,
            AVG(pattern_support_score) as avg_pattern_support,
            AVG(CASE WHEN validated_by_patterns = 1 THEN impact_score ELSE NULL END) as avg_impact_validated,
            AVG(CASE WHEN validated_by_patterns = 0 THEN impact_score ELSE NULL END) as avg_impact_unvalidated
        FROM synergy_opportunities
    """)
    row = cursor.fetchone()
    
    return {
        'total': row[0],
        'validated': row[1],
        'unvalidated': row[0] - row[1],
        'validation_rate': round((row[1] / row[0] * 100) if row[0] > 0 else 0, 2),
        'avg_pattern_support': round(row[2], 3) if row[2] else 0,
        'avg_impact_validated': round(row[3], 3) if row[3] else 0,
        'avg_impact_unvalidated': round(row[4], 3) if row[4] else 0
    }


def get_priority_tier_distribution(cursor) -> Dict[str, int]:
    """Get distribution by priority tier based on impact score."""
    cursor.execute("""
        SELECT 
            CASE 
                WHEN impact_score >= 0.7 THEN 'Tier 1: High (≥70%)'
                WHEN impact_score >= 0.6 THEN 'Tier 2: Medium-High (60-70%)'
                WHEN impact_score >= 0.5 THEN 'Tier 3: Medium (50-60%)'
                WHEN impact_score >= 0.4 THEN 'Tier 4: Low-Medium (40-50%)'
                ELSE 'Tier 5: Low (<40%)'
            END as tier,
            COUNT(*) as count
        FROM synergy_opportunities
        GROUP BY tier
        ORDER BY tier
    """)
    return {row[0]: row[1] for row in cursor.fetchall()}


def calculate_priority_scores(cursor, limit: int = 20) -> List[Dict[str, Any]]:
    """Calculate priority scores for top synergies."""
    cursor.execute("""
        SELECT 
            id,
            synergy_id,
            impact_score,
            confidence,
            COALESCE(pattern_support_score, 0) as pattern_support_score,
            CASE WHEN validated_by_patterns = 1 THEN 1 ELSE 0 END as validated,
            complexity,
            area,
            json_extract(opportunity_metadata, '$.relationship') as relationship,
            json_extract(opportunity_metadata, '$.trigger_name') as trigger_name,
            json_extract(opportunity_metadata, '$.action_name') as action_name
        FROM synergy_opportunities
        ORDER BY 
            (impact_score * 0.40 + 
             confidence * 0.25 + 
             COALESCE(pattern_support_score, 0) * 0.25 + 
             CASE WHEN validated_by_patterns = 1 THEN 0.10 ELSE 0 END +
             CASE WHEN complexity = 'low' THEN 0.10 ELSE 0 END) DESC
        LIMIT ?
    """, (limit,))
    
    results = []
    for row in cursor.fetchall():
        priority_score = (
            row[2] * 0.40 +  # impact_score
            row[3] * 0.25 +  # confidence
            row[4] * 0.25 +  # pattern_support_score
            row[5] * 0.10 +  # validated bonus
            (0.10 if row[6] == 'low' else 0)  # complexity bonus
        )
        results.append({
            'id': row[0],
            'synergy_id': row[1],
            'priority_score': round(priority_score, 3),
            'impact_score': round(row[2], 3),
            'confidence': round(row[3], 3),
            'pattern_support_score': round(row[4], 3),
            'validated': bool(row[5]),
            'complexity': row[6],
            'area': row[7],
            'relationship': row[8],
            'trigger_name': row[9],
            'action_name': row[10]
        })
    
    return results


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def main():
    """Main analysis function."""
    import sys
    import io
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at: {DB_PATH}")
        print("   Please ensure the ai-automation-service has been run at least once.")
        return
    
    print(f"[INFO] Analyzing synergy data from: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Basic statistics
        cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("[ERROR] No synergy opportunities found in database.")
            return
        
        print_section("OVERVIEW")
        print(f"Total Opportunities: {total:,}")
        
        # Impact distribution
        print_section("IMPACT SCORE DISTRIBUTION")
        impact_dist = get_impact_distribution(cursor)
        for range_name, count in impact_dist.items():
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {range_name:12} {count:6,} ({percentage:5.1f}%) {bar}")
        
        # Priority tier distribution
        print_section("PRIORITY TIER DISTRIBUTION")
        tier_dist = get_priority_tier_distribution(cursor)
        for tier, count in tier_dist.items():
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {tier:35} {count:6,} ({percentage:5.1f}%) {bar}")
        
        # Complexity distribution
        print_section("COMPLEXITY DISTRIBUTION")
        complexity_dist = get_complexity_distribution(cursor)
        for complexity, count in complexity_dist.items():
            percentage = (count / total) * 100
            print(f"  {complexity:10} {count:6,} ({percentage:5.1f}%)")
        
        # Pattern validation stats
        print_section("PATTERN VALIDATION STATISTICS")
        pattern_stats = get_pattern_validation_stats(cursor)
        print(f"  Total Synergies:        {pattern_stats['total']:,}")
        print(f"  Validated:              {pattern_stats['validated']:,} ({pattern_stats['validation_rate']}%)")
        print(f"  Unvalidated:            {pattern_stats['unvalidated']:,}")
        print(f"  Avg Pattern Support:    {pattern_stats['avg_pattern_support']:.3f}")
        print(f"  Avg Impact (Validated): {pattern_stats['avg_impact_validated']:.3f}")
        print(f"  Avg Impact (Unvalidated): {pattern_stats['avg_impact_unvalidated']:.3f}")
        
        # Area distribution
        print_section("TOP AREAS BY SYNERGY COUNT")
        area_dist = get_area_distribution(cursor, limit=15)
        print(f"{'Area':<30} {'Count':>8} {'Avg Impact':>12} {'Avg Conf':>10} {'Validated':>10}")
        print("-" * 80)
        for area in area_dist:
            print(f"{area['area']:<30} {area['count']:>8,} {area['avg_impact']:>11.3f} "
                  f"{area['avg_confidence']:>9.3f} {area['validated_count']:>10,}")
        
        # Relationship distribution
        print_section("RELATIONSHIP TYPE DISTRIBUTION")
        rel_dist = get_relationship_distribution(cursor)
        print(f"{'Relationship':<30} {'Count':>8} {'Avg Impact':>12} {'Avg Conf':>10} {'Pattern':>10} {'Validated':>10}")
        print("-" * 90)
        for rel in rel_dist:
            print(f"{rel['relationship']:<30} {rel['count']:>8,} {rel['avg_impact']:>11.3f} "
                  f"{rel['avg_confidence']:>9.3f} {rel['avg_pattern_support']:>9.3f} {rel['validated_count']:>10,}")
        
        # Top priority synergies
        print_section("TOP 20 PRIORITY SYNERGIES")
        top_priorities = calculate_priority_scores(cursor, limit=20)
        print(f"{'Priority':>8} {'Impact':>8} {'Conf':>6} {'Pattern':>8} {'Valid':>6} {'Area':<20} {'Relationship':<25}")
        print("-" * 100)
        for synergy in top_priorities:
            validated_str = "[V]" if synergy['validated'] else "[ ]"
            area_str = (synergy['area'] or 'unknown')[:20]
            rel_str = (synergy['relationship'] or 'unknown')[:25]
            print(f"{synergy['priority_score']:>8.3f} {synergy['impact_score']:>8.3f} "
                  f"{synergy['confidence']:>6.3f} {synergy['pattern_support_score']:>8.3f} "
                  f"{validated_str:>6} {area_str:<20} {rel_str:<25}")
        
        # Recommendations
        print_section("RECOMMENDATIONS")
        
        tier1_count = sum(count for tier, count in tier_dist.items() if 'Tier 1' in tier)
        tier2_count = sum(count for tier, count in tier_dist.items() if 'Tier 2' in tier)
        validated_high_impact = pattern_stats['validated']
        
        print(f"1. Quick Wins (Tier 1 + Tier 2): {tier1_count + tier2_count:,} synergies")
        print(f"   → Focus on implementing these first for maximum ROI")
        print()
        print(f"2. Pattern-Validated Opportunities: {validated_high_impact:,} synergies")
        print(f"   → High confidence, validated by historical patterns")
        print()
        print(f"3. Top Areas for Implementation:")
        for i, area in enumerate(area_dist[:5], 1):
            print(f"   {i}. {area['area']}: {area['count']:,} opportunities "
                  f"(avg impact: {area['avg_impact']:.1%})")
        print()
        print(f"4. Relationship Types to Prioritize:")
        for i, rel in enumerate(rel_dist[:5], 1):
            print(f"   {i}. {rel['relationship']}: {rel['count']:,} opportunities "
                  f"(avg impact: {rel['avg_impact']:.1%})")
        
    except Exception as e:
        print(f"[ERROR] Error analyzing data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print("\n" + "="*80)
    print("Analysis complete! See implementation/analysis/SYNERGY_DATA_ANALYSIS.md for detailed insights.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

