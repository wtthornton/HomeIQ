#!/usr/bin/env python3
"""
Investigate why queries don't generate suggestions.

This script analyzes ask_ai_queries to identify patterns in queries that
don't generate suggestions and provides root cause analysis.
"""
import sqlite3
import sys
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta

# Database path (Docker container path)
DB_PATH = Path("/app/data/ai_automation.db")

def analyze_missing_suggestions(conn):
    """Analyze queries without suggestions"""
    cursor = conn.cursor()
    
    # Get all queries
    cursor.execute("""
        SELECT 
            query_id,
            original_query,
            parsed_intent,
            extracted_entities,
            suggestions,
            confidence,
            processing_time_ms,
            created_at
        FROM ask_ai_queries
        ORDER BY created_at DESC
    """)
    
    all_queries = cursor.fetchall()
    
    # Categorize queries
    queries_with_suggestions = []
    queries_without_suggestions = []
    
    for row in all_queries:
        query_id, original_query, parsed_intent, extracted_entities_json, suggestions_json, confidence, processing_time_ms, created_at = row
        
        # Parse JSON fields
        extracted_entities = json.loads(extracted_entities_json) if extracted_entities_json else []
        suggestions = json.loads(suggestions_json) if suggestions_json else []
        
        query_data = {
            'query_id': query_id,
            'original_query': original_query,
            'parsed_intent': parsed_intent,
            'extracted_entities': extracted_entities,
            'suggestions': suggestions,
            'confidence': confidence,
            'processing_time_ms': processing_time_ms,
            'created_at': created_at,
            'entity_count': len(extracted_entities) if extracted_entities else 0,
            'suggestion_count': len(suggestions) if suggestions else 0
        }
        
        if not suggestions or len(suggestions) == 0:
            queries_without_suggestions.append(query_data)
        else:
            queries_with_suggestions.append(query_data)
    
    return all_queries, queries_with_suggestions, queries_without_suggestions

def analyze_patterns(queries_without_suggestions, queries_with_suggestions):
    """Analyze patterns in missing suggestions"""
    patterns = {
        'entity_extraction': {
            'no_entities': 0,
            'with_entities': 0
        },
        'intent_analysis': Counter(),
        'query_length': {
            'short': 0,  # < 20 chars
            'medium': 0,  # 20-100 chars
            'long': 0    # > 100 chars
        },
        'confidence_distribution': [],
        'processing_time': [],
        'query_keywords': Counter()
    }
    
    for query in queries_without_suggestions:
        # Entity extraction analysis
        if query['entity_count'] == 0:
            patterns['entity_extraction']['no_entities'] += 1
        else:
            patterns['entity_extraction']['with_entities'] += 1
        
        # Intent analysis
        if query['parsed_intent']:
            patterns['intent_analysis'][query['parsed_intent']] += 1
        else:
            patterns['intent_analysis']['null'] += 1
        
        # Query length analysis
        query_len = len(query['original_query'])
        if query_len < 20:
            patterns['query_length']['short'] += 1
        elif query_len < 100:
            patterns['query_length']['medium'] += 1
        else:
            patterns['query_length']['long'] += 1
        
        # Confidence and processing time
        if query['confidence'] is not None:
            patterns['confidence_distribution'].append(query['confidence'])
        if query['processing_time_ms'] is not None:
            patterns['processing_time'].append(query['processing_time_ms'])
        
        # Extract keywords (simple word analysis)
        words = query['original_query'].lower().split()
        for word in words[:10]:  # First 10 words
            if len(word) > 3:  # Ignore short words
                patterns['query_keywords'][word] += 1
    
    return patterns

def generate_recommendations(patterns, total_without, total_with):
    """Generate recommendations based on analysis"""
    recommendations = []
    
    # Entity extraction issues
    no_entities_pct = (patterns['entity_extraction']['no_entities'] / total_without * 100) if total_without > 0 else 0
    if no_entities_pct > 50:
        recommendations.append({
            'priority': 'HIGH',
            'issue': f'{no_entities_pct:.1f}% of queries without suggestions have no extracted entities',
            'recommendation': 'Improve entity extraction: Enhance entity resolution, add entity aliases, improve entity matching logic'
        })
    
    # Intent parsing issues
    null_intent_pct = (patterns['intent_analysis'].get('null', 0) / total_without * 100) if total_without > 0 else 0
    if null_intent_pct > 30:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': f'{null_intent_pct:.1f}% of queries without suggestions have no parsed intent',
            'recommendation': 'Improve intent parsing: Enhance intent detection, handle ambiguous queries better, improve prompt engineering'
        })
    
    # Query length issues
    short_query_pct = (patterns['query_length']['short'] / total_without * 100) if total_without > 0 else 0
    if short_query_pct > 40:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': f'{short_query_pct:.1f}% of queries without suggestions are very short (<20 chars)',
            'recommendation': 'Handle short queries: Add clarification flow for vague queries, prompt user for more details'
        })
    
    # Confidence issues
    if patterns['confidence_distribution']:
        avg_confidence = sum(patterns['confidence_distribution']) / len(patterns['confidence_distribution'])
        if avg_confidence < 0.5:
            recommendations.append({
                'priority': 'MEDIUM',
                'issue': f'Average confidence for queries without suggestions: {avg_confidence:.2f}',
                'recommendation': 'Adjust confidence thresholds: Review minimum confidence requirements, consider lowering threshold for certain query types'
            })
    
    # Processing time issues
    if patterns['processing_time']:
        avg_time = sum(patterns['processing_time']) / len(patterns['processing_time'])
        if avg_time > 5000:  # > 5 seconds
            recommendations.append({
                'priority': 'LOW',
                'issue': f'Average processing time for queries without suggestions: {avg_time:.0f}ms',
                'recommendation': 'Optimize processing: Investigate slow queries, add timeouts, optimize entity resolution'
            })
    
    return recommendations

def main():
    """Main entry point"""
    print("=" * 80)
    print("ANALYZING MISSING SUGGESTIONS")
    print("=" * 80)
    print()
    print(f"Database: {DB_PATH}")
    print()
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Make sure you're running this script inside the Docker container")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Analyze queries
        print("Analyzing ask_ai_queries...")
        print("-" * 80)
        
        all_queries, queries_with_suggestions, queries_without_suggestions = analyze_missing_suggestions(conn)
        
        total_queries = len(all_queries)
        total_with = len(queries_with_suggestions)
        total_without = len(queries_without_suggestions)
        missing_pct = (total_without / total_queries * 100) if total_queries > 0 else 0
        
        print(f"Total queries: {total_queries:,}")
        print(f"Queries with suggestions: {total_with:,} ({100-missing_pct:.1f}%)")
        print(f"Queries without suggestions: {total_without:,} ({missing_pct:.1f}%)")
        print()
        
        if total_without == 0:
            print("✅ All queries have suggestions! No analysis needed.")
            conn.close()
            return True
        
        # Analyze patterns
        print("Analyzing patterns in queries without suggestions...")
        print("-" * 80)
        
        patterns = analyze_patterns(queries_without_suggestions, queries_with_suggestions)
        
        # Entity extraction
        print("\nEntity Extraction Analysis:")
        print(f"  Queries with no entities: {patterns['entity_extraction']['no_entities']:,} ({patterns['entity_extraction']['no_entities']/total_without*100:.1f}%)")
        print(f"  Queries with entities: {patterns['entity_extraction']['with_entities']:,} ({patterns['entity_extraction']['with_entities']/total_without*100:.1f}%)")
        
        # Intent analysis
        print("\nIntent Analysis:")
        for intent, count in patterns['intent_analysis'].most_common(5):
            pct = (count / total_without * 100) if total_without > 0 else 0
            print(f"  {intent or 'null'}: {count:,} ({pct:.1f}%)")
        
        # Query length
        print("\nQuery Length Analysis:")
        for length_type, count in patterns['query_length'].items():
            pct = (count / total_without * 100) if total_without > 0 else 0
            print(f"  {length_type}: {count:,} ({pct:.1f}%)")
        
        # Confidence
        if patterns['confidence_distribution']:
            avg_confidence = sum(patterns['confidence_distribution']) / len(patterns['confidence_distribution'])
            min_confidence = min(patterns['confidence_distribution'])
            max_confidence = max(patterns['confidence_distribution'])
            print(f"\nConfidence Analysis:")
            print(f"  Average: {avg_confidence:.2f}")
            print(f"  Range: {min_confidence:.2f} - {max_confidence:.2f}")
        
        # Processing time
        if patterns['processing_time']:
            avg_time = sum(patterns['processing_time']) / len(patterns['processing_time'])
            print(f"\nProcessing Time Analysis:")
            print(f"  Average: {avg_time:.0f}ms")
        
        # Top keywords
        print(f"\nTop Keywords in Queries Without Suggestions:")
        for keyword, count in patterns['query_keywords'].most_common(10):
            print(f"  '{keyword}': {count:,}")
        
        # Generate recommendations
        print()
        print("=" * 80)
        print("ROOT CAUSE ANALYSIS & RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        recommendations = generate_recommendations(patterns, total_without, total_with)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. [{rec['priority']}] {rec['issue']}")
                print(f"   Recommendation: {rec['recommendation']}")
                print()
        else:
            print("✅ No specific patterns identified. Review individual queries for insights.")
            print()
        
        # Sample queries without suggestions
        print("Sample Queries Without Suggestions (recent):")
        print("-" * 80)
        recent_without = sorted(queries_without_suggestions, key=lambda x: x['created_at'], reverse=True)[:5]
        for i, query in enumerate(recent_without, 1):
            print(f"\n{i}. Query: \"{query['original_query'][:80]}{'...' if len(query['original_query']) > 80 else ''}\"")
            print(f"   Intent: {query['parsed_intent'] or 'null'}")
            print(f"   Entities: {query['entity_count']}")
            confidence_str = f"{query['confidence']:.2f}" if query['confidence'] is not None else 'null'
            print(f"   Confidence: {confidence_str}")
            print(f"   Created: {query['created_at']}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

