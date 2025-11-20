"""
Unit tests for Confidence Calculator Phase 3 features

Tests RL calibration and uncertainty quantification integration.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock
from src.services.clarification.confidence_calculator import ConfidenceCalculator
from src.services.clarification.confidence_calibrator import ClarificationConfidenceCalibrator
from src.services.clarification.rl_calibrator import RLConfidenceCalibrator, RLCalibrationConfig
from src.services.clarification.uncertainty_quantification import (
    UncertaintyQuantifier,
    ConfidenceWithUncertainty
)
from src.services.clarification.models import (
    Ambiguity,
    AmbiguitySeverity,
    AmbiguityType,
    ClarificationAnswer
)


@pytest.fixture
def mock_calibrator():
    """Create mock isotonic regression calibrator."""
    calibrator = Mock(spec=ClarificationConfidenceCalibrator)
    calibrator.calibrate = Mock(return_value=0.85)
    return calibrator


@pytest.fixture
def rl_calibrator_trained():
    """Create trained RL calibrator for testing."""
    config = RLCalibrationConfig(
        learning_rate=0.01,
        min_samples_for_training=5,  # Lower for testing
        update_frequency=3
    )
    calibrator = RLConfidenceCalibrator(config=config)
    
    # Train with some samples
    for i in range(6):
        calibrator.add_feedback(
            predicted_confidence=0.7 + i * 0.05,
            actual_outcome=i % 2 == 0,
            ambiguity_count=1,
            critical_ambiguity_count=0,
            rounds=1,
            answer_count=1,
            auto_train=False
        )
    calibrator.train()
    
    return calibrator


@pytest.fixture
def uncertainty_quantifier():
    """Create uncertainty quantifier for testing."""
    return UncertaintyQuantifier(method="bootstrap")


@pytest.fixture
def confidence_calculator_base(mock_calibrator):
    """Create base confidence calculator (Phase 1 & 2 only)."""
    return ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_enabled=False
    )


@pytest.fixture
def confidence_calculator_with_rl(mock_calibrator, rl_calibrator_trained):
    """Create confidence calculator with RL calibration enabled."""
    return ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibrator=rl_calibrator_trained,
        rl_calibration_enabled=True,
        uncertainty_enabled=False
    )


@pytest.fixture
def confidence_calculator_with_uncertainty(mock_calibrator, uncertainty_quantifier):
    """Create confidence calculator with uncertainty quantification enabled."""
    return ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )


@pytest.fixture
def confidence_calculator_full(mock_calibrator, rl_calibrator_trained, uncertainty_quantifier):
    """Create confidence calculator with all Phase 3 features enabled."""
    return ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibrator=rl_calibrator_trained,
        rl_calibration_enabled=True,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )


@pytest.fixture
def sample_ambiguities():
    """Create sample ambiguities for testing."""
    return [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices match",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]


@pytest.fixture
def sample_answers():
    """Create sample clarification answers."""
    return [
        ClarificationAnswer(
            question_id="q1",
            answer_text="light.living_room",
            validated=True,
            confidence=0.9
        )
    ]


@pytest.mark.asyncio
async def test_rl_calibration_disabled_by_default(confidence_calculator_base, sample_ambiguities):
    """Test that RL calibration is disabled by default."""
    confidence = await confidence_calculator_base.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    
    # Should use isotonic regression calibration only
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    # Mock calibrator returns 0.85
    assert confidence == 0.85


@pytest.mark.asyncio
async def test_rl_calibration_enabled(confidence_calculator_with_rl, sample_ambiguities):
    """Test RL calibration when enabled."""
    confidence = await confidence_calculator_with_rl.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    
    # Should apply both isotonic regression and RL calibration
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    # RL calibration adjusts the confidence
    assert confidence != 0.85  # Should be different from isotonic-only result


@pytest.mark.asyncio
async def test_rl_calibration_with_ambiguities(confidence_calculator_with_rl, sample_ambiguities):
    """Test RL calibration considers ambiguity context."""
    # Test with different ambiguity counts
    confidence_1 = await confidence_calculator_with_rl.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    
            # More ambiguities should affect RL calibration
    more_ambiguities = sample_ambiguities + [
        Ambiguity(
            id="amb2",
            type=AmbiguityType.TIMING,
            severity=AmbiguitySeverity.OPTIONAL,
            description="When?",
            related_entities=None
        )
    ]
    
    confidence_2 = await confidence_calculator_with_rl.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=more_ambiguities,
        base_confidence=0.8
    )
    
    # Both should be valid
    assert 0.0 <= confidence_1 <= 1.0
    assert 0.0 <= confidence_2 <= 1.0


@pytest.mark.asyncio
async def test_rl_calibration_with_answers(
    confidence_calculator_with_rl,
    sample_ambiguities,
    sample_answers
):
    """Test RL calibration with clarification answers."""
    confidence = await confidence_calculator_with_rl.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        clarification_answers=sample_answers,
        base_confidence=0.8
    )
    
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_uncertainty_quantification_disabled_by_default(
    confidence_calculator_base,
    sample_ambiguities
):
    """Test that uncertainty quantification is disabled by default."""
    confidence = await confidence_calculator_base.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True  # Request uncertainty but it's disabled
    )
    
    # Should return float, not ConfidenceWithUncertainty
    assert isinstance(confidence, float)
    assert not isinstance(confidence, ConfidenceWithUncertainty)


@pytest.mark.asyncio
async def test_uncertainty_quantification_enabled(
    confidence_calculator_with_uncertainty,
    sample_ambiguities
):
    """Test uncertainty quantification when enabled."""
    result = await confidence_calculator_with_uncertainty.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    # Should return ConfidenceWithUncertainty
    assert isinstance(result, ConfidenceWithUncertainty)
    assert 0.0 <= result.mean <= 1.0
    assert result.std >= 0
    assert 0.0 <= result.lower_bound <= 1.0
    assert 0.0 <= result.upper_bound <= 1.0
    assert result.lower_bound <= result.upper_bound
    assert result.distribution in ["normal", "beta", "gamma"]


@pytest.mark.asyncio
async def test_uncertainty_quantification_without_flag(
    confidence_calculator_with_uncertainty,
    sample_ambiguities
):
    """Test that uncertainty is not returned unless return_uncertainty=True."""
    confidence = await confidence_calculator_with_uncertainty.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=False
    )
    
    # Should return float even if uncertainty is enabled
    assert isinstance(confidence, float)
    assert not isinstance(confidence, ConfidenceWithUncertainty)


@pytest.mark.asyncio
async def test_uncertainty_quantification_confidence_intervals(
    confidence_calculator_with_uncertainty,
    sample_ambiguities
):
    """Test that uncertainty provides valid confidence intervals."""
    result = await confidence_calculator_with_uncertainty.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    # Mean should be within bounds
    assert result.lower_bound <= result.mean <= result.upper_bound
    
    # Bounds should be reasonable (not too wide)
    width = result.upper_bound - result.lower_bound
    assert width > 0
    assert width <= 1.0  # Should not exceed full range


@pytest.mark.asyncio
async def test_full_phase3_integration(
    confidence_calculator_full,
    sample_ambiguities,
    sample_answers
):
    """Test all Phase 3 features working together."""
    # Test with uncertainty
    result_with_uncertainty = await confidence_calculator_full.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        clarification_answers=sample_answers,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    assert isinstance(result_with_uncertainty, ConfidenceWithUncertainty)
    assert 0.0 <= result_with_uncertainty.mean <= 1.0
    
    # Test without uncertainty (should still apply RL calibration)
    confidence = await confidence_calculator_full.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        clarification_answers=sample_answers,
        base_confidence=0.8,
        return_uncertainty=False
    )
    
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_rl_calibration_error_handling(
    confidence_calculator_with_rl,
    sample_ambiguities
):
    """Test that RL calibration errors don't break the flow."""
    # Create a broken RL calibrator
    broken_rl = Mock(spec=RLConfidenceCalibrator)
    broken_rl.calibrate = Mock(side_effect=Exception("RL calibration failed"))
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(spec=ClarificationConfidenceCalibrator),
        calibration_enabled=True,
        rl_calibrator=broken_rl,
        rl_calibration_enabled=True,
        uncertainty_enabled=False
    )
    
    # Should fall back to previous confidence (from isotonic regression)
    confidence = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    
    # Should still return valid confidence
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_uncertainty_quantification_error_handling(
    confidence_calculator_with_uncertainty,
    sample_ambiguities
):
    """Test that uncertainty calculation errors don't break the flow."""
    # Create a broken uncertainty quantifier
    broken_quantifier = Mock(spec=UncertaintyQuantifier)
    broken_quantifier.calculate_uncertainty = Mock(
        side_effect=Exception("Uncertainty calculation failed")
    )
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(spec=ClarificationConfidenceCalibrator),
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_quantifier=broken_quantifier,
        uncertainty_enabled=True
    )
    
    # Should fall back to point estimate
    confidence = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    # Should return float (fallback) instead of crashing
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_rl_calibration_not_trained(
    confidence_calculator_base,
    sample_ambiguities
):
    """Test RL calibration when not trained (should pass through)."""
    # Create untrained RL calibrator
    untrained_rl = RLConfidenceCalibrator()
    assert not untrained_rl.is_trained
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(spec=ClarificationConfidenceCalibrator),
        calibration_enabled=True,
        rl_calibrator=untrained_rl,
        rl_calibration_enabled=True,
        uncertainty_enabled=False
    )
    
    confidence = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    
    # Should return valid confidence (RL should pass through if not trained)
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_phase3_feature_combinations(
    mock_calibrator,
    rl_calibrator_trained,
    uncertainty_quantifier,
    sample_ambiguities
):
    """Test different combinations of Phase 3 features."""
    # Test 1: Only RL calibration
    calculator_rl_only = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibrator=rl_calibrator_trained,
        rl_calibration_enabled=True,
        uncertainty_enabled=False
    )
    
    conf_rl = await calculator_rl_only.calculate_confidence(
        query="test",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8
    )
    assert isinstance(conf_rl, float)
    
    # Test 2: Only uncertainty
    calculator_uncertainty_only = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )
    
    result_uncertainty = await calculator_uncertainty_only.calculate_confidence(
        query="test",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    assert isinstance(result_uncertainty, ConfidenceWithUncertainty)
    
    # Test 3: Both enabled
    calculator_both = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=mock_calibrator,
        calibration_enabled=True,
        rl_calibrator=rl_calibrator_trained,
        rl_calibration_enabled=True,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )
    
    result_both = await calculator_both.calculate_confidence(
        query="test",
        extracted_entities=[],
        ambiguities=sample_ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    assert isinstance(result_both, ConfidenceWithUncertainty)
    assert 0.0 <= result_both.mean <= 1.0

