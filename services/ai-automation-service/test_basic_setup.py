"""
Simple test for Multi-Model Entity Extraction (without external dependencies)
Tests the configuration and basic functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configuration():
    """Test that configuration is properly set up"""
    print("🔧 Testing Configuration")
    print("=" * 30)
    
    try:
        from src.config import settings
        
        print(f"Entity Extraction Method: {settings.entity_extraction_method}")
        print(f"NER Model: {settings.ner_model}")
        print(f"OpenAI Model: {settings.openai_model}")
        print(f"NER Confidence Threshold: {settings.ner_confidence_threshold}")
        print(f"Enable Entity Caching: {settings.enable_entity_caching}")
        print(f"Max Cache Size: {settings.max_cache_size}")
        
        print("✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_imports():
    """Test that all required modules can be imported"""
    print("\n📦 Testing Imports")
    print("=" * 20)
    
    modules_to_test = [
        ("src.entity_extraction.pattern_extractor", "Pattern Extractor"),
        ("src.entity_extraction.enhanced_extractor", "Enhanced Extractor"),
        ("src.clients.device_intelligence_client", "Device Intelligence Client"),
        ("src.monitoring.performance_monitor", "Performance Monitor"),
    ]
    
    all_passed = True
    
    for module_name, display_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {display_name}")
        except Exception as e:
            print(f"❌ {display_name}: {e}")
            all_passed = False
    
    return all_passed

def test_multi_model_extractor_import():
    """Test multi-model extractor import (will fail without transformers)"""
    print("\n🤖 Testing Multi-Model Extractor Import")
    print("=" * 40)
    
    try:
        from src.entity_extraction.multi_model_extractor import MultiModelEntityExtractor
        print("✅ Multi-Model Extractor imported successfully")
        return True
    except ImportError as e:
        print(f"⚠️  Multi-Model Extractor import failed (expected): {e}")
        print("   This is expected without transformers installed")
        return False
    except Exception as e:
        print(f"❌ Multi-Model Extractor import failed: {e}")
        return False

def test_ask_ai_router_integration():
    """Test that Ask AI router has been updated"""
    print("\n🔌 Testing Ask AI Router Integration")
    print("=" * 35)
    
    try:
        from src.api.ask_ai_router import _multi_model_extractor, set_device_intelligence_client
        
        print("✅ Multi-model extractor variable exists")
        print("✅ set_device_intelligence_client function exists")
        
        # Test that the function signature is correct
        import inspect
        sig = inspect.signature(set_device_intelligence_client)
        params = list(sig.parameters.keys())
        
        if 'client' in params:
            print("✅ Function signature is correct")
            return True
        else:
            print("❌ Function signature is incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Ask AI Router integration test failed: {e}")
        return False

def test_performance_monitor():
    """Test performance monitor functionality"""
    print("\n📊 Testing Performance Monitor")
    print("=" * 30)
    
    try:
        from src.monitoring.performance_monitor import MultiModelPerformanceMonitor
        
        monitor = MultiModelPerformanceMonitor()
        
        # Test logging a metric
        monitor.log_extraction(
            query="Test query",
            method_used="pattern",
            processing_time=0.001,
            entities_found=2,
            confidence_score=0.8
        )
        
        # Test getting stats
        stats = monitor.get_daily_summary()
        
        print(f"✅ Performance monitor created")
        print(f"✅ Metric logging works")
        print(f"✅ Daily summary works: {stats['total_queries']} queries")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitor test failed: {e}")
        return False

def test_docker_configuration():
    """Test Docker configuration updates"""
    print("\n🐳 Testing Docker Configuration")
    print("=" * 30)
    
    try:
        dockerfile_path = Path("Dockerfile")
        if dockerfile_path.exists():
            with open(dockerfile_path, 'r') as f:
                content = f.read()
            
            if "spacy download en_core_web_sm" in content:
                print("✅ spaCy model download added to Dockerfile")
            else:
                print("❌ spaCy model download not found in Dockerfile")
                return False
            
            if "libgomp1" in content:
                print("✅ OpenVINO threading support added")
            else:
                print("❌ OpenVINO threading support not found")
                return False
            
            return True
        else:
            print("❌ Dockerfile not found")
            return False
            
    except Exception as e:
        print(f"❌ Docker configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Multi-Model Entity Extraction - Basic Tests")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Imports", test_imports),
        ("Multi-Model Extractor", test_multi_model_extractor_import),
        ("Ask AI Router", test_ask_ai_router_integration),
        ("Performance Monitor", test_performance_monitor),
        ("Docker Configuration", test_docker_configuration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} Test...")
        if test_func():
            passed += 1
        print()
    
    print("📊 Test Results")
    print("=" * 15)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total:.1%}")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-Model Entity Extraction is ready for deployment.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please check the issues above.")
    
    print("\n📋 Next Steps:")
    print("1. Install transformers: pip install transformers")
    print("2. Install spaCy: pip install spacy && python -m spacy download en_core_web_sm")
    print("3. Run full integration test: python test_multi_model_extraction.py")
    print("4. Deploy with: ./scripts/deploy_multi_model.sh")

if __name__ == "__main__":
    main()
