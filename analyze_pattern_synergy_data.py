"""
Analyze Pattern and Synergy Data for Corruption
Identifies issues with patterns and synergies in the ai_automation database
"""
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = '/app/data/ai_automation.db'

def analyze_patterns(conn):
    """Analyze patterns table for corruption and issues"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("PATTERN ANALYSIS")
    print("="*80)
    
    # Get all patterns
    cursor.execute("SELECT id, pattern_type, entity_id, metadata, confidence FROM patterns")
    patterns = cursor.fetchall()
    
    issues = {
        'invalid_json': [],
        'missing_fields': [],
        'invalid_confidence': [],
        'duplicate_entities': defaultdict(list),
        'old_patterns': [],
        'zero_confidence': []
    }
    
    for pattern in patterns:
        pattern_id, pattern_type, entity_id, metadata_str, confidence = pattern
        
        # Check JSON validity
        try:
            metadata = json.loads(metadata_str)
        except (json.JSONDecodeError, TypeError):
            issues['invalid_json'].append(pattern_id)
            continue
        
        # Check required fields
        required_fields = ['avg_time_decimal', 'cluster_id', 'std_minutes', 'time_range', 'occurrence_ratio']
        missing = [f for f in required_fields if f not in metadata]
        if missing:
            issues['missing_fields'].append((pattern_id, missing))
        
        # Check confidence validity
        if confidence is None or confidence < 0 or confidence > 1:
            issues['invalid_confidence'].append((pattern_id, confidence))
        
        if confidence == 0:
            issues['zero_confidence'].append(pattern_id)
        
        # Track duplicates
        issues['duplicate_entities'][entity_id].append(pattern_id)
    
    # Check pattern history for age
    cursor.execute("""
        SELECT p.id, MAX(ph.timestamp) as last_seen
        FROM patterns p
        LEFT JOIN pattern_history ph ON p.id = ph.pattern_id
        GROUP BY p.id
    """)
    
    cutoff_date = datetime.now() - timedelta(days=30)
    for pattern_id, last_seen in cursor.fetchall():
        if last_seen:
            last_seen_dt = datetime.fromisoformat(last_seen)
            if last_seen_dt < cutoff_date:
                issues['old_patterns'].append((pattern_id, last_seen))
    
    # Print results
    print(f"\nTotal Patterns: {len(patterns)}")
    print(f"\n❌ Invalid JSON: {len(issues['invalid_json'])} patterns")
    if issues['invalid_json']:
        print(f"   Pattern IDs: {issues['invalid_json'][:10]}{'...' if len(issues['invalid_json']) > 10 else ''}")
    
    print(f"\n❌ Missing Required Fields: {len(issues['missing_fields'])} patterns")
    if issues['missing_fields']:
        for pid, fields in issues['missing_fields'][:5]:
            print(f"   Pattern {pid}: missing {fields}")
    
    print(f"\n❌ Invalid Confidence: {len(issues['invalid_confidence'])} patterns")
    if issues['invalid_confidence']:
        for pid, conf in issues['invalid_confidence'][:5]:
            print(f"   Pattern {pid}: confidence={conf}")
    
    print(f"\n⚠️  Zero Confidence: {len(issues['zero_confidence'])} patterns")
    
    duplicates = {k: v for k, v in issues['duplicate_entities'].items() if len(v) > 1}
    print(f"\n⚠️  Duplicate Entities: {len(duplicates)} entities with multiple patterns")
    if duplicates:
        for entity, pids in list(duplicates.items())[:5]:
            print(f"   {entity}: {len(pids)} patterns")
    
    print(f"\n⚠️  Old Patterns (>30 days): {len(issues['old_patterns'])} patterns")
    if issues['old_patterns']:
        for pid, last_seen in issues['old_patterns'][:5]:
            print(f"   Pattern {pid}: last seen {last_seen}")
    
    return issues

def analyze_synergies(conn):
    """Analyze synergy_opportunities table for corruption"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("SYNERGY ANALYSIS")
    print("="*80)
    
    cursor.execute("SELECT id, synergy_id, synergy_type, entities, metadata FROM synergy_opportunities")
    synergies = cursor.fetchall()
    
    issues = {
        'invalid_json_entities': [],
        'invalid_json_metadata': [],
        'missing_metadata_fields': [],
        'empty_entities': [],
        'duplicate_synergy_ids': defaultdict(list)
    }
    
    for synergy in synergies:
        synergy_db_id, synergy_id, synergy_type, entities_str, metadata_str = synergy
        
        # Check entities JSON
        try:
            entities = json.loads(entities_str)
            if not entities or len(entities) == 0:
                issues['empty_entities'].append(synergy_db_id)
        except (json.JSONDecodeError, TypeError):
            issues['invalid_json_entities'].append(synergy_db_id)
        
        # Check metadata JSON
        try:
            metadata = json.loads(metadata_str)
            # Check for required fields
            if 'relationship' not in metadata:
                issues['missing_metadata_fields'].append((synergy_db_id, 'relationship'))
        except (json.JSONDecodeError, TypeError):
            issues['invalid_json_metadata'].append(synergy_db_id)
        
        # Track duplicate synergy IDs
        issues['duplicate_synergy_ids'][synergy_id].append(synergy_db_id)
    
    # Print results
    print(f"\nTotal Synergies: {len(synergies)}")
    print(f"\n❌ Invalid Entities JSON: {len(issues['invalid_json_entities'])} synergies")
    print(f"❌ Invalid Metadata JSON: {len(issues['invalid_json_metadata'])} synergies")
    print(f"❌ Missing Metadata Fields: {len(issues['missing_metadata_fields'])} synergies")
    print(f"⚠️  Empty Entities: {len(issues['empty_entities'])} synergies")
    
    duplicates = {k: v for k, v in issues['duplicate_synergy_ids'].items() if len(v) > 1}
    print(f"⚠️  Duplicate Synergy IDs: {len(duplicates)} synergies")
    
    return issues

def analyze_pattern_history(conn):
    """Analyze pattern_history table"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("PATTERN HISTORY ANALYSIS")
    print("="*80)
    
    cursor.execute("SELECT COUNT(*) FROM pattern_history")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pattern_history")
    min_date, max_date = cursor.fetchone()
    
    cursor.execute("""
        SELECT pattern_id, COUNT(*) as count
        FROM pattern_history
        GROUP BY pattern_id
        ORDER BY count DESC
        LIMIT 10
    """)
    top_patterns = cursor.fetchall()
    
    print(f"\nTotal History Records: {total}")
    print(f"Date Range: {min_date} to {max_date}")
    print(f"\nTop 10 Patterns by History Count:")
    for pattern_id, count in top_patterns:
        print(f"  Pattern {pattern_id}: {count} records")
    
    # Check for orphaned history (patterns that no longer exist)
    cursor.execute("""
        SELECT COUNT(DISTINCT ph.pattern_id)
        FROM pattern_history ph
        LEFT JOIN patterns p ON ph.pattern_id = p.id
        WHERE p.id IS NULL
    """)
    orphaned = cursor.fetchone()[0]
    print(f"\n⚠️  Orphaned History Records: {orphaned} patterns (history exists but pattern deleted)")
    
    return {'total': total, 'orphaned': orphaned}

def generate_cleanup_recommendations(pattern_issues, synergy_issues, history_issues):
    """Generate cleanup recommendations based on analysis"""
    print("\n" + "="*80)
    print("CLEANUP RECOMMENDATIONS")
    print("="*80)
    
    recommendations = []
    
    # Pattern recommendations
    if pattern_issues['invalid_json']:
        recommendations.append({
            'priority': 'HIGH',
            'action': 'DELETE',
            'target': 'patterns',
            'count': len(pattern_issues['invalid_json']),
            'reason': 'Invalid JSON metadata - cannot be fixed',
            'sql': f"DELETE FROM patterns WHERE id IN ({','.join(map(str, pattern_issues['invalid_json']))})"
        })
    
    if pattern_issues['zero_confidence']:
        recommendations.append({
            'priority': 'HIGH',
            'action': 'DELETE',
            'target': 'patterns',
            'count': len(pattern_issues['zero_confidence']),
            'reason': 'Zero confidence patterns - not useful',
            'sql': f"DELETE FROM patterns WHERE confidence = 0"
        })
    
    if pattern_issues['old_patterns']:
        recommendations.append({
            'priority': 'MEDIUM',
            'action': 'DELETE',
            'target': 'patterns',
            'count': len(pattern_issues['old_patterns']),
            'reason': 'Patterns not seen in >30 days - stale data',
            'sql': "DELETE FROM patterns WHERE id IN (SELECT p.id FROM patterns p LEFT JOIN pattern_history ph ON p.id = ph.pattern_id GROUP BY p.id HAVING MAX(ph.timestamp) < datetime('now', '-30 days'))"
        })
    
    # Synergy recommendations
    if synergy_issues['invalid_json_entities'] or synergy_issues['invalid_json_metadata']:
        total_invalid = len(synergy_issues['invalid_json_entities']) + len(synergy_issues['invalid_json_metadata'])
        recommendations.append({
            'priority': 'HIGH',
            'action': 'DELETE',
            'target': 'synergy_opportunities',
            'count': total_invalid,
            'reason': 'Invalid JSON - cannot be fixed',
            'sql': 'DELETE FROM synergy_opportunities WHERE id IN (...)'  # Would need specific IDs
        })
    
    if synergy_issues['empty_entities']:
        recommendations.append({
            'priority': 'HIGH',
            'action': 'DELETE',
            'target': 'synergy_opportunities',
            'count': len(synergy_issues['empty_entities']),
            'reason': 'Empty entities - not useful',
            'sql': f"DELETE FROM synergy_opportunities WHERE id IN ({','.join(map(str, synergy_issues['empty_entities']))})"
        })
    
    # History recommendations
    if history_issues['orphaned'] > 0:
        recommendations.append({
            'priority': 'MEDIUM',
            'action': 'DELETE',
            'target': 'pattern_history',
            'count': history_issues['orphaned'],
            'reason': 'Orphaned history records - parent pattern deleted',
            'sql': "DELETE FROM pattern_history WHERE pattern_id NOT IN (SELECT id FROM patterns)"
        })
    
    # Nuclear option
    recommendations.append({
        'priority': 'NUCLEAR',
        'action': 'DELETE ALL',
        'target': 'patterns, synergy_opportunities, pattern_history',
        'count': 'ALL',
        'reason': 'Complete cleanup - start fresh',
        'sql': """
            DELETE FROM pattern_history;
            DELETE FROM patterns;
            DELETE FROM synergy_opportunities;
            VACUUM;
        """
    })
    
    # Print recommendations
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['priority']}] {rec['action']} {rec['count']} records from {rec['target']}")
        print(f"   Reason: {rec['reason']}")
        print(f"   SQL: {rec['sql'][:100]}{'...' if len(rec['sql']) > 100 else ''}")
    
    return recommendations

def main():
    """Main analysis function"""
    print("="*80)
    print("PATTERN & SYNERGY DATA CORRUPTION ANALYSIS")
    print("="*80)
    print(f"Database: {DB_PATH}")
    print(f"Analysis Time: {datetime.now().isoformat()}")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        pattern_issues = analyze_patterns(conn)
        synergy_issues = analyze_synergies(conn)
        history_issues = analyze_pattern_history(conn)
        recommendations = generate_cleanup_recommendations(pattern_issues, synergy_issues, history_issues)
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print("\nNext Steps:")
        print("1. Review recommendations above")
        print("2. Backup database: docker cp ai-pattern-service:/app/data/ai_automation.db ./backup.db")
        print("3. Run cleanup script with chosen option")
        print("4. Verify data integrity after cleanup")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
