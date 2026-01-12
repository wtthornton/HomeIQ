#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Synergy Scoring

Analyzes synergy scores and groups them by score ranges.
"""

import json
import sqlite3
import sys
from collections import defaultdict
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


def analyze_synergy_scoring(db_path: str = "/app/data/ai_automation.db", use_docker: bool = True):
    """Analyze synergy scoring and group by score ranges."""
    
    if use_docker:
        # Query via docker exec
        import subprocess
        cmd = [
            "docker", "exec", "ai-pattern-service", "python", "-c",
            """
import sqlite3
import json
conn = sqlite3.connect('/app/data/ai_automation.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT 
        quality_score,
        quality_tier,
        impact_score,
        confidence,
        final_score,
        synergy_type
    FROM synergy_opportunities
''')
rows = cursor.fetchall()
results = {
    'total': len(rows),
    'scores': []
}
for row in rows:
    results['scores'].append({
        'quality_score': row[0],
        'quality_tier': row[1],
        'impact_score': row[2],
        'confidence': row[3],
        'final_score': row[4],
        'synergy_type': row[5]
    })
conn.close()
print(json.dumps(results))
"""
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print(f"Error querying database: {result.stderr}")
            return None
        data = json.loads(result.stdout)
    else:
        # Direct database access
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                quality_score,
                quality_tier,
                impact_score,
                confidence,
                final_score,
                synergy_type
            FROM synergy_opportunities
        """)
        rows = cursor.fetchall()
        data = {
            'total': len(rows),
            'scores': [
                {
                    'quality_score': row['quality_score'],
                    'quality_tier': row['quality_tier'],
                    'impact_score': row['impact_score'],
                    'confidence': row['confidence'],
                    'final_score': row['final_score'],
                    'synergy_type': row['synergy_type']
                }
                for row in rows
            ]
        }
        conn.close()
    
    total = data['total']
    scores = data['scores']
    
    print("=" * 80)
    print("Synergy Scoring Analysis")
    print("=" * 80)
    print(f"\nTotal Synergies: {total:,}")
    
    # Analyze quality_score
    print("\n" + "-" * 80)
    print("Quality Score Distribution")
    print("-" * 80)
    
    quality_score_ranges = {
        "0.0": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0,
        "1.0": 0,
        "NULL": 0
    }
    
    quality_tier_counts = defaultdict(int)
    
    for score_data in scores:
        qs = score_data['quality_score']
        qt = score_data['quality_tier']
        
        if qt:
            quality_tier_counts[qt] += 1
        
        if qs is None:
            quality_score_ranges["NULL"] += 1
        elif qs == 0.0:
            quality_score_ranges["0.0"] += 1
        elif qs == 1.0:
            quality_score_ranges["1.0"] += 1
        elif 0.1 <= qs < 0.2:
            quality_score_ranges["0.1-0.2"] += 1
        elif 0.2 <= qs < 0.3:
            quality_score_ranges["0.2-0.3"] += 1
        elif 0.3 <= qs < 0.4:
            quality_score_ranges["0.3-0.4"] += 1
        elif 0.4 <= qs < 0.5:
            quality_score_ranges["0.4-0.5"] += 1
        elif 0.5 <= qs < 0.6:
            quality_score_ranges["0.5-0.6"] += 1
        elif 0.6 <= qs < 0.7:
            quality_score_ranges["0.6-0.7"] += 1
        elif 0.7 <= qs < 0.8:
            quality_score_ranges["0.7-0.8"] += 1
        elif 0.8 <= qs < 0.9:
            quality_score_ranges["0.8-0.9"] += 1
        elif 0.9 <= qs < 1.0:
            quality_score_ranges["0.9-1.0"] += 1
    
    print("\nQuality Score Ranges:")
    for range_name in sorted(quality_score_ranges.keys(), key=lambda x: (x == "NULL", float(x.split("-")[0]) if "-" in x else (float(x) if x != "NULL" else 999))):
        count = quality_score_ranges[range_name]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {range_name:10s}: {count:6,} ({pct:5.1f}%)")
    
    print("\nQuality Tiers:")
    for tier in sorted(quality_tier_counts.keys()):
        count = quality_tier_counts[tier]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {tier:10s}: {count:6,} ({pct:5.1f}%)")
    
    # Analyze impact_score
    print("\n" + "-" * 80)
    print("Impact Score Distribution")
    print("-" * 80)
    
    impact_ranges = {
        "0.0-0.1": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0,
        "NULL": 0
    }
    
    impact_values = [s['impact_score'] for s in scores if s['impact_score'] is not None]
    if impact_values:
        min_impact = min(impact_values)
        max_impact = max(impact_values)
        avg_impact = sum(impact_values) / len(impact_values)
    else:
        min_impact = max_impact = avg_impact = None
    
    for score_data in scores:
        impact = score_data['impact_score']
        if impact is None:
            impact_ranges["NULL"] += 1
        elif 0.0 <= impact < 0.1:
            impact_ranges["0.0-0.1"] += 1
        elif 0.1 <= impact < 0.2:
            impact_ranges["0.1-0.2"] += 1
        elif 0.2 <= impact < 0.3:
            impact_ranges["0.2-0.3"] += 1
        elif 0.3 <= impact < 0.4:
            impact_ranges["0.3-0.4"] += 1
        elif 0.4 <= impact < 0.5:
            impact_ranges["0.4-0.5"] += 1
        elif 0.5 <= impact < 0.6:
            impact_ranges["0.5-0.6"] += 1
        elif 0.6 <= impact < 0.7:
            impact_ranges["0.6-0.7"] += 1
        elif 0.7 <= impact < 0.8:
            impact_ranges["0.7-0.8"] += 1
        elif 0.8 <= impact < 0.9:
            impact_ranges["0.8-0.9"] += 1
        elif 0.9 <= impact <= 1.0:
            impact_ranges["0.9-1.0"] += 1
    
    print(f"\nImpact Score Stats:")
    if min_impact is not None:
        print(f"  Min: {min_impact:.3f}")
        print(f"  Max: {max_impact:.3f}")
        print(f"  Avg: {avg_impact:.3f}")
    
    print("\nImpact Score Ranges:")
    for range_name in sorted(impact_ranges.keys(), key=lambda x: (x == "NULL", float(x.split("-")[0]) if "-" in x else 999)):
        count = impact_ranges[range_name]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {range_name:10s}: {count:6,} ({pct:5.1f}%)")
    
    # Analyze confidence
    print("\n" + "-" * 80)
    print("Confidence Distribution")
    print("-" * 80)
    
    confidence_ranges = {
        "0.0-0.1": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0,
        "NULL": 0
    }
    
    confidence_values = [s['confidence'] for s in scores if s['confidence'] is not None]
    if confidence_values:
        min_conf = min(confidence_values)
        max_conf = max(confidence_values)
        avg_conf = sum(confidence_values) / len(confidence_values)
    else:
        min_conf = max_conf = avg_conf = None
    
    for score_data in scores:
        conf = score_data['confidence']
        if conf is None:
            confidence_ranges["NULL"] += 1
        elif 0.0 <= conf < 0.1:
            confidence_ranges["0.0-0.1"] += 1
        elif 0.1 <= conf < 0.2:
            confidence_ranges["0.1-0.2"] += 1
        elif 0.2 <= conf < 0.3:
            confidence_ranges["0.2-0.3"] += 1
        elif 0.3 <= conf < 0.4:
            confidence_ranges["0.3-0.4"] += 1
        elif 0.4 <= conf < 0.5:
            confidence_ranges["0.4-0.5"] += 1
        elif 0.5 <= conf < 0.6:
            confidence_ranges["0.5-0.6"] += 1
        elif 0.6 <= conf < 0.7:
            confidence_ranges["0.6-0.7"] += 1
        elif 0.7 <= conf < 0.8:
            confidence_ranges["0.7-0.8"] += 1
        elif 0.8 <= conf < 0.9:
            confidence_ranges["0.8-0.9"] += 1
        elif 0.9 <= conf <= 1.0:
            confidence_ranges["0.9-1.0"] += 1
    
    print(f"\nConfidence Stats:")
    if min_conf is not None:
        print(f"  Min: {min_conf:.3f}")
        print(f"  Max: {max_conf:.3f}")
        print(f"  Avg: {avg_conf:.3f}")
    
    print("\nConfidence Ranges:")
    for range_name in sorted(confidence_ranges.keys(), key=lambda x: (x == "NULL", float(x.split("-")[0]) if "-" in x else 999)):
        count = confidence_ranges[range_name]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {range_name:10s}: {count:6,} ({pct:5.1f}%)")
    
    # Analyze final_score
    print("\n" + "-" * 80)
    print("Final Score Distribution")
    print("-" * 80)
    
    final_score_ranges = {
        "0.0": 0,
        "0.0-0.1": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0,
        "NULL": 0
    }
    
    final_values = [s['final_score'] for s in scores if s['final_score'] is not None]
    if final_values:
        min_final = min(final_values)
        max_final = max(final_values)
        avg_final = sum(final_values) / len(final_values)
    else:
        min_final = max_final = avg_final = None
    
    for score_data in scores:
        final = score_data['final_score']
        if final is None:
            final_score_ranges["NULL"] += 1
        elif final == 0.0:
            final_score_ranges["0.0"] += 1
        elif 0.0 < final < 0.1:
            final_score_ranges["0.0-0.1"] += 1
        elif 0.1 <= final < 0.2:
            final_score_ranges["0.1-0.2"] += 1
        elif 0.2 <= final < 0.3:
            final_score_ranges["0.2-0.3"] += 1
        elif 0.3 <= final < 0.4:
            final_score_ranges["0.3-0.4"] += 1
        elif 0.4 <= final < 0.5:
            final_score_ranges["0.4-0.5"] += 1
        elif 0.5 <= final < 0.6:
            final_score_ranges["0.5-0.6"] += 1
        elif 0.6 <= final < 0.7:
            final_score_ranges["0.6-0.7"] += 1
        elif 0.7 <= final < 0.8:
            final_score_ranges["0.7-0.8"] += 1
        elif 0.8 <= final < 0.9:
            final_score_ranges["0.8-0.9"] += 1
        elif 0.9 <= final <= 1.0:
            final_score_ranges["0.9-1.0"] += 1
    
    print(f"\nFinal Score Stats:")
    if min_final is not None:
        print(f"  Min: {min_final:.3f}")
        print(f"  Max: {max_final:.3f}")
        print(f"  Avg: {avg_final:.3f}")
    
    print("\nFinal Score Ranges:")
    for range_name in sorted(final_score_ranges.keys(), key=lambda x: (x == "NULL", float(x.split("-")[0]) if "-" in x else (float(x) if x != "NULL" else 999))):
        count = final_score_ranges[range_name]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {range_name:10s}: {count:6,} ({pct:5.1f}%)")
    
    # Summary by synergy type
    print("\n" + "-" * 80)
    print("Scoring Summary by Synergy Type")
    print("-" * 80)
    
    type_stats = defaultdict(lambda: {'count': 0, 'quality_scores': [], 'impact_scores': [], 'confidence_scores': []})
    
    for score_data in scores:
        stype = score_data['synergy_type']
        type_stats[stype]['count'] += 1
        if score_data['quality_score'] is not None:
            type_stats[stype]['quality_scores'].append(score_data['quality_score'])
        if score_data['impact_score'] is not None:
            type_stats[stype]['impact_scores'].append(score_data['impact_score'])
        if score_data['confidence'] is not None:
            type_stats[stype]['confidence_scores'].append(score_data['confidence'])
    
    for stype in sorted(type_stats.keys()):
        stats = type_stats[stype]
        print(f"\n{stype}:")
        print(f"  Count: {stats['count']:,}")
        if stats['quality_scores']:
            avg_qs = sum(stats['quality_scores']) / len(stats['quality_scores'])
            print(f"  Avg Quality Score: {avg_qs:.3f}")
        if stats['impact_scores']:
            avg_is = sum(stats['impact_scores']) / len(stats['impact_scores'])
            print(f"  Avg Impact Score: {avg_is:.3f}")
        if stats['confidence_scores']:
            avg_cs = sum(stats['confidence_scores']) / len(stats['confidence_scores'])
            print(f"  Avg Confidence: {avg_cs:.3f}")
    
    print("\n" + "=" * 80)
    
    # Return results for further processing
    return {
        'total': total,
        'quality_score_ranges': quality_score_ranges,
        'quality_tier_counts': dict(quality_tier_counts),
        'impact_ranges': impact_ranges,
        'confidence_ranges': confidence_ranges,
        'final_score_ranges': final_score_ranges,
        'type_stats': {k: {
            'count': v['count'],
            'avg_quality': sum(v['quality_scores']) / len(v['quality_scores']) if v['quality_scores'] else None,
            'avg_impact': sum(v['impact_scores']) / len(v['impact_scores']) if v['impact_scores'] else None,
            'avg_confidence': sum(v['confidence_scores']) / len(v['confidence_scores']) if v['confidence_scores'] else None
        } for k, v in type_stats.items()}
    }


if __name__ == "__main__":
    results = analyze_synergy_scoring(use_docker=True)
    if results:
        # Save results to JSON
        output_path = Path("implementation/synergy_scoring_analysis.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")
