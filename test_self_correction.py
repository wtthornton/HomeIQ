"""Test script for self-correction with regeneration feature."""
import asyncio
import json
import httpx

# API Key for authentication
API_KEY = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"

async def test_self_correction():
    """Test the reverse-engineer-yaml endpoint."""
    url = "http://localhost:8024/api/v1/ask-ai/reverse-engineer-yaml"
    headers = {"X-HomeIQ-API-Key": API_KEY}
    
    # Test payload
    payload = {
        "yaml": """alias: Turn on kitchen light at 7 AM
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen""",
        "original_prompt": "Turn on the kitchen light at 7 AM every day"
    }
    
    print("=" * 60)
    print("Testing Self-Correction with Regeneration")
    print("=" * 60)
    print(f"\nOriginal Prompt: {payload['original_prompt']}")
    print(f"\nYAML to correct:")
    print(payload['yaml'])
    print("\n" + "=" * 60)
    print("Sending request... (this may take 30-60 seconds)")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ SUCCESS!")
                print(f"\nFinal Similarity: {result.get('final_similarity', 0) * 100:.1f}%")
                print(f"Iterations Completed: {result.get('iterations_completed', 0)}")
                print(f"Convergence Achieved: {result.get('convergence_achieved', False)}")
                
                # Always show all keys returned
                print(f"\n📋 Response keys: {list(result.keys())}")
                
                # Check for regeneration fields (new feature)
                print(f"\n🔄 REGENERATION METRICS:")
                print(f"  YAML Source: {result.get('yaml_source', 'N/A (field not present)')}")
                print(f"  Regeneration Attempted: {result.get('regeneration_attempted', 'N/A')}")
                print(f"  Regeneration Successful: {result.get('regeneration_successful', 'N/A')}")
                if result.get('regeneration_similarity') is not None:
                    print(f"  Regeneration Similarity: {result.get('regeneration_similarity', 0) * 100:.1f}%")
                if result.get('regeneration_validation_passed') is not None:
                    print(f"  Regeneration Validation: {result.get('regeneration_validation_passed')}")
                
                print(f"\n📊 Token Usage: {result.get('total_tokens_used', 0)}")
                
                # Print iteration history
                if result.get('iteration_history'):
                    print(f"\n📈 Iteration History:")
                    for iteration in result['iteration_history'][:3]:  # Show first 3
                        print(f"  - Iteration {iteration.get('iteration', '?')}: "
                              f"Similarity {iteration.get('similarity_score', 0) * 100:.1f}%")
                
                print("\n" + "=" * 60)
                print("FINAL YAML:")
                print("=" * 60)
                print(result.get('final_yaml', 'No YAML returned'))
                
            else:
                print(f"\n❌ ERROR: {response.text}")
                
        except httpx.TimeoutException:
            print("\n❌ Request timed out (>120 seconds)")
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_self_correction())

