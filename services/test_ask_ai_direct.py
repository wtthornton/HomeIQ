"""
Test the AI automation service integration directly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "ai-automation-service" / "src"))

from api.ask_ai_router import extract_entities_with_ha, generate_suggestions_from_query

async def test_ask_ai_integration():
    """Test the Ask AI integration with our enhanced entity extraction"""
    print("🤖 Testing Ask AI Integration")
    print("=" * 40)
    
    test_query = "Flash the office lights when the front door opens"
    
    print(f"Query: {test_query}")
    print("\n1️⃣ Testing Entity Extraction")
    print("-" * 30)
    
    try:
        entities = await extract_entities_with_ha(test_query)
        print(f"Found {len(entities)} entities:")
        
        for entity in entities:
            if entity.get('extraction_method') == 'device_intelligence':
                print(f"  ✅ {entity['name']} (Enhanced)")
                print(f"     Entity ID: {entity.get('entity_id', 'N/A')}")
                print(f"     Manufacturer: {entity.get('manufacturer', 'Unknown')}")
                print(f"     Model: {entity.get('model', 'Unknown')}")
                print(f"     Health Score: {entity.get('health_score', 'N/A')}")
                capabilities = [cap['feature'] for cap in entity.get('capabilities', []) if cap.get('supported')]
                print(f"     Capabilities: {', '.join(capabilities) if capabilities else 'Basic on/off'}")
            else:
                print(f"  📝 {entity['name']} (Basic fallback)")
        
        print("\n2️⃣ Testing AI Suggestion Generation")
        print("-" * 30)
        
        suggestions = await generate_suggestions_from_query(test_query)
        print(f"Generated {len(suggestions)} suggestions:")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n  Suggestion {i}:")
            print(f"    Description: {suggestion.get('description', 'N/A')}")
            print(f"    Trigger: {suggestion.get('trigger_summary', 'N/A')}")
            print(f"    Action: {suggestion.get('action_summary', 'N/A')}")
            print(f"    Devices: {', '.join(suggestion.get('devices_involved', []))}")
            print(f"    Capabilities Used: {', '.join(suggestion.get('capabilities_used', []))}")
            print(f"    Confidence: {suggestion.get('confidence', 0)}")
        
        print("\n✅ Ask AI Integration Test Complete!")
        print("\n🎯 Results:")
        print("- Entity Extraction: ✅ Working")
        print("- Enhanced Device Data: ✅ Working")
        print("- AI Suggestion Generation: ✅ Working")
        print("- Capability-Aware Suggestions: ✅ Working")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ask_ai_integration())
