"""Test imports for new modules"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.api.community_pattern_router import router
    print("✅ community_pattern_router imported")
except Exception as e:
    print(f"❌ community_pattern_router failed: {e}")

try:
    from src.pattern_detection.multi_factor_detector import MultiFactorPatternDetector
    print("✅ MultiFactorPatternDetector imported")
except Exception as e:
    print(f"❌ MultiFactorPatternDetector failed: {e}")

try:
    from src.suggestion_generation.cascade_generator import CascadeSuggestionGenerator
    print("✅ CascadeSuggestionGenerator imported")
except Exception as e:
    print(f"❌ CascadeSuggestionGenerator failed: {e}")

try:
    from src.suggestion_generation.predictive_generator import PredictiveAutomationGenerator
    print("✅ PredictiveAutomationGenerator imported")
except Exception as e:
    print(f"❌ PredictiveAutomationGenerator failed: {e}")

try:
    from src.suggestion_generation.community_learner import CommunityPatternLearner
    print("✅ CommunityPatternLearner imported")
except Exception as e:
    print(f"❌ CommunityPatternLearner failed: {e}")

try:
    from src.synergy_detection.enhanced_synergy_detector import EnhancedSynergyDetector
    print("✅ EnhancedSynergyDetector imported")
except Exception as e:
    print(f"❌ EnhancedSynergyDetector failed: {e}")

print("\nAll imports tested!")

