#!/usr/bin/env python3
"""Test full flow with clarification answers to verify device names"""
import asyncio
import aiohttp
import json
import sys
import os

async def test_full_flow():
    """Test complete flow: query -> clarification -> suggestions"""
    print("=" * 120)
    print("TESTING FULL FLOW: Query -> Clarification -> Suggestions")
    print("=" * 120)
    
    url = "http://localhost:8024/api/v1/ask-ai/query"
    api_key = os.getenv('AI_AUTOMATION_API_KEY', 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR')
    
    headers = {
        "Content-Type": "application/json",
        "X-HomeIQ-API-Key": api_key
    }
    
    # Step 1: Submit initial query
    query = "Flash all the Office Hue lights for 30 seconds at the top of every hour"
    payload = {
        "query": query,
        "user_id": "test_user"
    }
    
    print(f"\n1. Submitting query: '{query}'")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status != 201:
                error_text = await response.text()
                print(f"[FAIL] Query failed: {response.status} - {error_text}")
                return False
            
            result = await response.json()
            clarification_session_id = result.get('clarification_session_id')
            query_id = result.get('query_id')
            
            print(f"[OK] Query submitted successfully")
            print(f"    Query ID: {query_id}")
            print(f"    Clarification Session ID: {clarification_session_id}")
            
            questions = result.get('questions', [])
            print(f"\n    Found {len(questions)} clarification questions")
            
            if not clarification_session_id:
                print("[WARN] No clarification session ID - checking for direct suggestions")
                suggestions = result.get('suggestions', [])
                if suggestions:
                    print(f"\n[OK] Found {len(suggestions)} suggestions directly")
                    return check_suggestions(suggestions)
                else:
                    print("[FAIL] No suggestions and no clarification session")
                    return False
            
            # Step 2: Answer clarification questions
            print("\n2. Answering clarification questions...")
            
            answers = []
            for i, question in enumerate(questions, 1):
                q_id = question.get('id', f'q{i}')
                q_text = question.get('question_text', '')
                options = question.get('options', [])
                
                print(f"\n   Question {i}: {q_text}")
                if options:
                    print(f"   Options: {options}")
                
                # Auto-answer based on question type
                if 'all four' in q_text.lower() or 'specific ones' in q_text.lower():
                    answer = "All four lights"
                elif 'top of the hour' in q_text.lower():
                    answer = "Exactly at the top of the hour"
                elif 'color or pattern' in q_text.lower():
                    answer = "Standard flash"
                else:
                    answer = options[0] if options else "Yes"
                
                answers.append({
                    "question_id": q_id,
                    "answer": answer
                })
                print(f"   Answer: {answer}")
            
            # Step 3: Submit clarification answers
            print("\n3. Submitting clarification answers...")
            
            clarification_url = f"http://localhost:8024/api/v1/ask-ai/clarify/{clarification_session_id}"
            clarification_payload = {
                "answers": answers,
                "user_id": "test_user"
            }
            
            async with session.post(clarification_url, json=clarification_payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as clarify_response:
                if clarify_response.status != 200:
                    error_text = await clarify_response.text()
                    print(f"[FAIL] Clarification failed: {clarify_response.status} - {error_text}")
                    return False
                
                clarify_result = await clarify_response.json()
                print(f"[OK] Clarification submitted successfully")
                
                # Step 4: Check suggestions
                suggestions = clarify_result.get('suggestions', [])
                print(f"\n4. Checking suggestions ({len(suggestions)} found)...")
                
                return check_suggestions(suggestions)

def check_suggestions(suggestions):
    """Check if suggestions have correct device names"""
    print("\n" + "=" * 120)
    print("DEVICE NAME VERIFICATION")
    print("=" * 120)
    
    if not suggestions:
        print("[FAIL] No suggestions found")
        return False
    
    all_correct = True
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n--- Suggestion {i} ---")
        print(f"Description: {suggestion.get('description', 'N/A')[:80]}...")
        
        devices_involved = suggestion.get('devices_involved', [])
        print(f"\nDevices Involved ({len(devices_involved)}):")
        
        friendly_names_found = 0
        generic_names_found = 0
        
        for device in devices_involved:
            print(f"  - {device}")
            
            # Check if it's a friendly name
            if any(keyword in device for keyword in ['Office', 'Back', 'Front', 'Left', 'Right']):
                friendly_names_found += 1
                print(f"    [OK] Friendly name detected")
            elif any(keyword in device.lower() for keyword in ['hue color downlight', 'downlight']):
                generic_names_found += 1
                print(f"    [WARN] Generic name detected")
        
        if friendly_names_found > 0:
            print(f"\n[PASS] Found {friendly_names_found} friendly device name(s)")
        elif generic_names_found > 0:
            print(f"\n[FAIL] Still showing {generic_names_found} generic device name(s)")
            all_correct = False
        else:
            print(f"\n[WARN] No recognizable device names found")
        
        # Check validated_entities
        validated_entities = suggestion.get('validated_entities', {})
        if validated_entities:
            print(f"\nValidated Entities ({len(validated_entities)}):")
            for device_name, entity_id in list(validated_entities.items())[:5]:
                print(f"  {device_name} -> {entity_id}")
    
    print("\n" + "=" * 120)
    if all_correct and friendly_names_found > 0:
        print("[SUCCESS] Device names are displaying correctly!")
        return True
    else:
        print("[FAILURE] Device names are NOT displaying correctly")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_flow())
    sys.exit(0 if success else 1)

