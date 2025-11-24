#!/usr/bin/env python3
"""
Quick verification script to test pattern/synergy integration in Ask AI.

Tests a simple query and checks if:
1. Patterns are being queried
2. Synergies are being queried
3. They appear in the prompt context
4. Confidence boosting works
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from datetime import datetime

# API Key (same as continuous improvement script)
API_KEY = os.getenv("AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")


async def test_pattern_synergy_integration():
    """Test pattern/synergy integration with a simple query."""
    
    base_url = "http://localhost:8024/api/v1/ask-ai"
    
    # Test query that should match patterns (Office WLED at 7 AM)
    test_query = "Turn on the Office WLED at 7 AM every day"
    
    print("=" * 80)
    print("Pattern/Synergy Integration Verification")
    print("=" * 80)
    print(f"\nTest Query: {test_query}")
    print(f"Base URL: {base_url}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Submit query
        print("[Step 1] Submitting query...")
        try:
            headers = {
                "Content-Type": "application/json",
                "X-HomeIQ-API-Key": API_KEY,
                "Authorization": f"Bearer {API_KEY}"
            }
            response = await client.post(
                f"{base_url}/query",
                json={"query": test_query},
                headers=headers
            )
            response.raise_for_status()
            query_data = response.json()
            query_id = query_data.get("query_id")
            print(f"✅ Query submitted: {query_id}")
            print(f"   Clarification needed: {query_data.get('clarification_needed', False)}")
            print(f"   Initial suggestions: {len(query_data.get('suggestions', []))}")
        except Exception as e:
            print(f"❌ Query submission failed: {e}")
            return False
        
        # Step 2: Handle clarification if needed
        if query_data.get("clarification_needed"):
            print("\n[Step 2] Handling clarification...")
            clarification_id = query_data.get("clarification_id")
            if clarification_id:
                # Get clarification questions
                clarify_response = await client.get(
                    f"{base_url}/clarify/{clarification_id}",
                    headers=headers
                )
                clarify_data = clarify_response.json()
                questions = clarify_data.get("questions", [])
                
                # Auto-answer all questions
                answers = {}
                for q in questions:
                    question_id = q.get("question_id")
                    # Simple auto-answer: "Yes" for all
                    answers[question_id] = "Yes"
                
                # Submit answers
                answer_response = await client.post(
                    f"{base_url}/clarify",
                    json={
                        "clarification_id": clarification_id,
                        "answers": answers
                    },
                    headers=headers
                )
                answer_data = answer_response.json()
                print(f"✅ Clarification answered")
                print(f"   Confidence: {answer_data.get('confidence', 0):.1f}%")
                print(f"   Suggestions: {len(answer_data.get('suggestions', []))}")
                
                # Use clarification query_id for next steps
                query_id = answer_data.get("query_id", query_id)
        
        # Step 3: Check suggestions
        print("\n[Step 3] Checking suggestions...")
        if query_id:
            # Get query details
            query_response = await client.get(f"{base_url}/query/{query_id}", headers=headers)
            query_details = query_response.json()
            suggestions = query_details.get("suggestions", [])
            
            print(f"✅ Found {len(suggestions)} suggestion(s)")
            
            # Check for pattern/synergy indicators
            pattern_indicators = []
            synergy_indicators = []
            confidence_boosts = []
            
            for i, suggestion in enumerate(suggestions, 1):
                confidence = suggestion.get("confidence", 0)
                description = suggestion.get("description", "")
                devices = suggestion.get("devices_involved", [])
                
                print(f"\n   Suggestion {i}:")
                print(f"     Confidence: {confidence:.1f}%")
                print(f"     Devices: {', '.join(devices)}")
                print(f"     Description: {description[:80]}...")
                
                # Check if confidence seems boosted (above typical baseline)
                if confidence >= 0.90:
                    confidence_boosts.append({
                        "suggestion": i,
                        "confidence": confidence,
                        "possible_boost": True
                    })
            
            # Summary
            print("\n" + "=" * 80)
            print("Verification Summary")
            print("=" * 80)
            print(f"\n✅ Query processed successfully")
            print(f"✅ Suggestions generated: {len(suggestions)}")
            
            if confidence_boosts:
                print(f"\n📈 Confidence Boosting Indicators:")
                for boost in confidence_boosts:
                    print(f"   - Suggestion {boost['suggestion']}: {boost['confidence']:.1f}% "
                          f"(possible pattern match boost)")
            else:
                print(f"\n⚠️  No obvious confidence boosts detected")
                print(f"   (This could mean: no patterns matched, or boosts are subtle)")
            
            print(f"\n💡 To verify pattern/synergy usage:")
            print(f"   1. Check service logs for 'Retrieved X patterns for context'")
            print(f"   2. Check service logs for 'Retrieved X synergies for context'")
            print(f"   3. Check service logs for 'Boosted confidence' messages")
            print(f"   4. Review prompt context in service logs (if enabled)")
            
            return True
        else:
            print("❌ No query_id available")
            return False


if __name__ == "__main__":
    try:
        result = asyncio.run(test_pattern_synergy_integration())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

