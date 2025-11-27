"""
Unit tests for Learning modules

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.learning.pattern_rlhf import PatternRLHF
from src.learning.pattern_quality_scorer import PatternQualityScorer
from src.learning.ensemble_quality_scorer import EnsembleQualityScorer
from src.learning.fbvl_quality_scorer import FBVLQualityScorer


class TestPatternRLHF:
    """Test suite for PatternRLHF."""
    
    @pytest.mark.unit
    def test_calculate_reward_accept(self):
        """Test reward calculation for accept action."""
        rlhf = PatternRLHF()
        pattern = {"confidence": 0.8, "occurrences": 10}
        
        reward = rlhf.calculate_reward(pattern, "accept")
        assert reward == 1.0
        assert rlhf.reward_statistics["accept_count"] == 1
    
    @pytest.mark.unit
    def test_calculate_reward_reject(self):
        """Test reward calculation for reject action."""
        rlhf = PatternRLHF()
        pattern = {"confidence": 0.5, "occurrences": 2}
        
        reward = rlhf.calculate_reward(pattern, "reject")
        assert reward == -0.5
        assert rlhf.reward_statistics["reject_count"] == 1
    
    @pytest.mark.unit
    def test_update_quality_weights(self):
        """Test updating quality weights based on reward."""
        rlhf = PatternRLHF()
        pattern = {
            "confidence": 0.8,
            "occurrences": 10,
            "pattern_type": "time_of_day"
        }
        current_weights = {
            "confidence": 0.4,
            "frequency": 0.3,
            "temporal": 0.2,
            "relationship": 0.1
        }
        
        # Positive reward should adjust weights
        updated = rlhf.update_quality_weights(pattern, 1.0, current_weights)
        
        assert isinstance(updated, dict)
        assert "confidence" in updated
        # Weights should be normalized (sum to ~1.0)
        total = sum(updated.values())
        assert abs(total - 1.0) < 0.01
    
    @pytest.mark.unit
    def test_get_reward_statistics(self):
        """Test getting reward statistics."""
        rlhf = PatternRLHF()
        pattern = {"confidence": 0.8}
        
        # Add some feedback
        rlhf.calculate_reward(pattern, "accept")
        rlhf.calculate_reward(pattern, "reject")
        
        stats = rlhf.get_reward_statistics()
        assert stats["total_feedback"] == 2
        assert stats["accept_count"] == 1
        assert stats["reject_count"] == 1


class TestPatternQualityScorer:
    """Test suite for PatternQualityScorer."""
    
    @pytest.mark.unit
    def test_calculate_quality_score_high_quality(self):
        """Test quality score calculation for high-quality pattern."""
        scorer = PatternQualityScorer()
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": "light.office_lamp",
            "confidence": 0.9,
            "occurrences": 20,
            "time_range": "07:00-07:15"
        }
        
        result = scorer.calculate_quality_score(pattern)
        
        assert "quality_score" in result
        assert 0.0 <= result["quality_score"] <= 1.0
        assert "base_quality" in result
        assert "breakdown" in result
        assert "quality_tier" in result
        assert result["quality_tier"] in ["high", "medium", "low"]
    
    @pytest.mark.unit
    def test_calculate_quality_score_low_quality(self):
        """Test quality score calculation for low-quality pattern."""
        scorer = PatternQualityScorer()
        pattern = {
            "pattern_type": "co_occurrence",
            "device_id": "device1+device2",
            "confidence": 0.3,
            "occurrences": 1
        }
        
        result = scorer.calculate_quality_score(pattern)
        
        assert result["quality_score"] < 0.5  # Should be low quality
        assert result["quality_tier"] in ["low", "medium"]


class TestEnsembleQualityScorer:
    """Test suite for EnsembleQualityScorer."""
    
    @pytest.mark.unit
    def test_calculate_ensemble_quality(self):
        """Test ensemble quality calculation."""
        scorer = EnsembleQualityScorer()
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": "light.office_lamp",
            "confidence": 0.85,
            "occurrences": 15
        }
        
        result = scorer.calculate_ensemble_quality(pattern)
        
        assert "quality_score" in result
        assert 0.0 <= result["quality_score"] <= 1.0
        assert "base_score" in result
        assert "model_weights" in result
    
    @pytest.mark.unit
    def test_update_model_weights(self):
        """Test updating model weights based on performance."""
        scorer = EnsembleQualityScorer()
        pattern = {
            "pattern_type": "time_of_day",
            "confidence": 0.8,
            "occurrences": 10
        }
        
        # Update weights with acceptance
        result = scorer.update_model_weights(pattern, actual_acceptance=True)
        
        assert "old_weights" in result
        assert "new_weights" in result
        assert "model_errors" in result


class TestFBVLQualityScorer:
    """Test suite for FBVLQualityScorer."""
    
    @pytest.mark.unit
    def test_calculate_quality_with_feedback(self):
        """Test quality calculation with validation feedback."""
        scorer = FBVLQualityScorer()
        pattern = {
            "pattern_type": "time_of_day",
            "device_id": "light.office_lamp",
            "confidence": 0.8
        }
        
        result = scorer.calculate_quality_with_feedback(pattern, base_quality=0.7)
        
        assert "quality_score" in result
        assert "base_quality" in result
        assert "validation_feedback" in result
        assert "adjustment" in result
    
    @pytest.mark.unit
    def test_add_validation_data(self):
        """Test adding validation data."""
        scorer = FBVLQualityScorer()
        pattern = {"pattern_type": "time_of_day", "device_id": "light.office"}
        
        scorer.add_validation_data(pattern, quality=0.9, user_accepted=True)
        
        assert len(scorer.validation_data) == 1
        assert scorer.validation_data[0]["quality"] == 0.9
        assert scorer.validation_data[0]["user_accepted"] is True

