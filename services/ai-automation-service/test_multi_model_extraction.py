"""
Test script for Multi-Model Entity Extraction
Tests the hybrid approach: NER → OpenAI → Pattern Matching
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.entity_extraction.multi_model_extractor import MultiModelEntityExtractor
from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.config import settings

async def test_multi_model_extraction():
    """Test multi-model entity extraction with various query types"""
    print("🧪 Testing Multi-Model Entity Extraction")
    print("=" * 50)
    
    # Initialize extractor
    device_client = DeviceIntelligenceClient(base_url="http://localhost:8021")
    extractor = MultiModelEntityExtractor(
        openai_api_key=settings.openai_api_key,
        device_intelligence_client=device_client,
        ner_model=settings.ner_model,
        openai_model=settings.openai_model
    )
    
    # Test queries of different complexity levels
    test_queries = [
        # Simple queries (should use NER)
        "Turn on office lights",
        "Flash kitchen lights",
        "Monitor bedroom temperature",
        
        # Medium complexity (might use NER or OpenAI)
        "Turn on the lights in the office when I arrive home",
        "Flash the kitchen lights when the door opens",
        
        # Complex queries (should use OpenAI)
        "When I come home in the evening, turn on the lights in the office and kitchen, but only if it's after sunset and the bedroom lights are off",
        "Create an automation that monitors the front door sensor and flashes the living room lights in a pattern, but only during nighttime hours",
        "If the temperature in the bedroom is too high and the window is open, turn on the fan and send me a notification",
        
        # Ambiguous queries (should use OpenAI)
        "Turn on the thing in the corner",
        "Make the stuff in my room work better",
        "Do something with the lights when I'm not home"
    ]
    
    print(f"Testing {len(test_queries)} queries...")
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"🔍 Test {i}: {query}")
        print("-" * 40)
        
        try:
            entities = await extractor.extract_entities(query)
            print(f"Found {len(entities)} entities:")
            
            for entity in entities:
                method = entity.get('extraction_method', 'unknown')
                confidence = entity.get('confidence', 0)
                name = entity.get('name', 'Unknown')
                
                if method == 'device_intelligence':
                    print(f"  ✅ {name} (Enhanced - {confidence:.2f})")
                    if entity.get('manufacturer'):
                        print(f"     Manufacturer: {entity.get('manufacturer')} {entity.get('model')}")
                    if entity.get('capabilities'):
                        caps = [cap['feature'] for cap in entity.get('capabilities', []) if cap.get('supported')]
                        print(f"     Capabilities: {', '.join(caps) if caps else 'Basic'}")
                elif method == 'ner':
                    print(f"  🧠 {name} (NER - {confidence:.2f})")
                elif method == 'openai':
                    print(f"  🤖 {name} (OpenAI - {confidence:.2f})")
                else:
                    print(f"  📝 {name} (Pattern - {confidence:.2f})")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    # Show performance statistics
    stats = extractor.get_stats()
    print("📊 Performance Statistics")
    print("=" * 30)
    print(f"Total Queries: {stats['total_queries']}")
    print(f"NER Success Rate: {stats.get('ner_success_rate', 0):.1%}")
    print(f"OpenAI Success Rate: {stats.get('openai_success_rate', 0):.1%}")
    print(f"Pattern Fallback Rate: {stats.get('pattern_fallback_rate', 0):.1%}")
    print(f"Average Processing Time: {stats['avg_processing_time']:.3f}s")
    
    await extractor.close()
    await device_client.close()

async def test_model_loading():
    """Test individual model loading"""
    print("\n🔧 Testing Model Loading")
    print("=" * 30)
    
    extractor = MultiModelEntityExtractor(
        openai_api_key=settings.openai_api_key,
        device_intelligence_client=None
    )
    
    # Test NER model loading
    print("Loading NER model...")
    ner_pipeline = extractor._get_ner_pipeline()
    if ner_pipeline:
        print("✅ NER model loaded successfully")
    else:
        print("❌ NER model failed to load")
    
    # Test OpenAI client
    print("Initializing OpenAI client...")
    openai_client = extractor._get_openai_client()
    if openai_client:
        print("✅ OpenAI client initialized")
    else:
        print("❌ OpenAI client failed to initialize")
    
    # Test spaCy model
    print("Loading spaCy model...")
    spacy_model = extractor._get_spacy_model()
    if spacy_model:
        print("✅ spaCy model loaded")
    else:
        print("❌ spaCy model failed to load")
    
    await extractor.close()

async def main():
    """Run all tests"""
    print("🚀 Multi-Model Entity Extraction Test Suite")
    print("=" * 60)
    
    # Test model loading first
    await test_model_loading()
    
    # Test extraction with various queries
    await test_multi_model_extraction()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
