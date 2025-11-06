#!/usr/bin/env python3
"""Quick script to investigate a specific query's prompt"""
import sqlite3
import json
import sys

query_id = sys.argv[1] if len(sys.argv) > 1 else 'query-70dcb45b'

conn = sqlite3.connect('/app/data/ai_automation.db')
cursor = conn.cursor()
cursor.execute('SELECT query_id, original_query, suggestions FROM ask_ai_queries WHERE query_id = ?', (query_id,))
row = cursor.fetchone()

if not row:
    print(f"Query {query_id} not found")
    sys.exit(1)

query_id, original_query, suggestions_json = row
suggestions = json.loads(suggestions_json) if suggestions_json else []

print("=" * 80)
print(f"QUERY: {original_query}")
print(f"SUGGESTIONS: {len(suggestions)}")
print("=" * 80)

if suggestions:
    s = suggestions[0]
    debug = s.get('debug', {})
    
    print("\n=== CLARIFICATION CONTEXT ===")
    clarification = debug.get('clarification_context', {})
    if clarification:
        qa_list = clarification.get('questions_and_answers', [])
        print(f"Q&A Pairs: {len(qa_list)}")
        for i, qa in enumerate(qa_list, 1):
            print(f"\n{i}. Q: {qa.get('question')}")
            print(f"   A: {qa.get('answer')}")
            if qa.get('selected_entities'):
                print(f"   Selected Entities: {qa.get('selected_entities')}")
    else:
        print("No clarification context")
    
    print("\n=== ENRICHED ENTITY CONTEXT (Entities in Prompt) ===")
    user_prompt = debug.get('user_prompt', '')
    if 'ENRICHED ENTITY CONTEXT' in user_prompt:
        # Extract JSON from prompt
        start = user_prompt.find('ENRICHED ENTITY CONTEXT')
        end = user_prompt.find('Use this enriched context', start)
        if end == -1:
            end = user_prompt.find('CAPABILITY-SPECIFIC', start)
        context_section = user_prompt[start:end]
        print(context_section[:2000])
        
        # Try to extract JSON
        json_start = context_section.find('{')
        json_end = context_section.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            try:
                context_json = json.loads(context_section[json_start:json_end])
                entities = context_json.get('entities', [])
                print(f"\n\nTotal entities in context: {len(entities)}")
                print("\nOffice lights:")
                office_lights = [e for e in entities if 'office' in e.get('friendly_name', '').lower() or 'office' in str(e.get('area_name', '')).lower()]
                print(f"  Found {len(office_lights)} office lights")
                for e in office_lights:
                    print(f"    - {e.get('friendly_name')} ({e.get('entity_id')})")
                
                print("\nAll lights (first 10):")
                lights = [e for e in entities if e.get('domain') == 'light'][:10]
                for e in lights:
                    area = e.get('area_name', 'N/A')
                    print(f"    - {e.get('friendly_name')} ({e.get('entity_id')}) - Area: {area}")
            except:
                pass
    
    print("\n=== SUGGESTION DETAILS ===")
    print(f"Description: {s.get('description', 'N/A')}")
    print(f"Devices Involved: {s.get('devices_involved', [])}")
    print(f"Validated Entities: {json.dumps(s.get('validated_entities', {}), indent=2)}")
    
    print("\n=== ENTITY CONTEXT STATS ===")
    stats = debug.get('entity_context_stats', {})
    print(json.dumps(stats, indent=2))

conn.close()

