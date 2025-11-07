import sqlite3
import json

query_id = 'query-70dcb45b'
conn = sqlite3.connect('/app/data/ai_automation.db')
cursor = conn.cursor()
cursor.execute('SELECT query_id, original_query, suggestions FROM ask_ai_queries WHERE query_id = ?', (query_id,))
row = cursor.fetchone()

query_id, original_query, suggestions_json = row
suggestions = json.loads(suggestions_json) if suggestions_json else []

print('=' * 80)
print(f'QUERY: {original_query}')
print(f'SUGGESTIONS: {len(suggestions)}')
print('=' * 80)

if suggestions:
    s = suggestions[0]
    debug = s.get('debug', {})
    
    print('\n=== CLARIFICATION CONTEXT ===')
    clarification = debug.get('clarification_context', {})
    if clarification:
        qa_list = clarification.get('questions_and_answers', [])
        print(f'Q&A Pairs: {len(qa_list)}')
        for i, qa in enumerate(qa_list, 1):
            print(f'\n{i}. Q: {qa.get("question")}')
            print(f'   A: {qa.get("answer")}')
            if qa.get('selected_entities'):
                print(f'   Selected Entities: {qa.get("selected_entities")}')
    else:
        print('No clarification context')
    
    print('\n=== SUGGESTION DETAILS ===')
    print(f'Description: {s.get("description", "N/A")}')
    print(f'Devices Involved: {s.get("devices_involved", [])}')
    print(f'Validated Entities: {json.dumps(s.get("validated_entities", {}), indent=2)}')
    
    print('\n=== ENRICHED ENTITY CONTEXT ===')
    user_prompt = debug.get('user_prompt', '')
    if 'ENRICHED ENTITY CONTEXT' in user_prompt:
        json_start = user_prompt.find('{')
        json_end = user_prompt.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            try:
                context_json = json.loads(user_prompt[json_start:json_end])
                entities = context_json.get('entities', [])
                print(f'Total entities in context: {len(entities)}')
                
                print('\nOffice lights:')
                office_lights = [e for e in entities if 'office' in e.get('friendly_name', '').lower() or (e.get('area_name') and 'office' in e.get('area_name', '').lower())]
                print(f'  Found {len(office_lights)} office lights')
                for e in office_lights:
                    print(f'    - {e.get("friendly_name")} ({e.get("entity_id")}) - Area: {e.get("area_name", "N/A")}')
                
                print('\nAll lights (first 10):')
                lights = [e for e in entities if e.get('domain') == 'light'][:10]
                for e in lights:
                    area = e.get('area_name', 'N/A')
                    print(f'    - {e.get("friendly_name")} ({e.get("entity_id")}) - Area: {area}')
            except Exception as e:
                print(f'Error parsing JSON: {e}')

conn.close()

