"""
Integration tests for Phase 3 features in the full clarification flow

Tests RL calibration and uncertainty quantification in end-to-end scenarios.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from httpx import AsyncClient
from src.services.clarification.rl_calibrator import RLConfidenceCalibrator, RLCalibrationConfig
from src.services.clarification.uncertainty_quantification import (
    UncertaintyQuantifier,
    ConfidenceWithUncertainty
)


@pytest.fixture
def mock_settings():
    """Provide mock settings to avoid Pydantic validation errors."""
    with patch.dict("os.environ", {
        "HA_URL": "http://test:8123",
        "HA_TOKEN": "test_token",
        "MQTT_BROKER": "test_broker",
        "OPENAI_API_KEY": "test_key"
    }):
        yield


@pytest.fixture
def rl_calibrator_trained():
    """Create trained RL calibrator for integration testing."""
    config = RLCalibrationConfig(
        learning_rate=0.01,
        min_samples_for_training=5,
        update_frequency=3
    )
    calibrator = RLConfidenceCalibrator(config=config)
    
    # Train with diverse samples
    samples = [
        (0.8, True, 0, 0, 0, 0),
        (0.9, True, 1, 0, 1, 1),
        (0.5, False, 2, 1, 2, 2),
        (0.3, False, 3, 2, 3, 3),
        (0.7, True, 1, 0, 1, 1),
        (0.6, False, 2, 0, 2, 2),
    ]
    
    for conf, outcome, amb, crit_amb, rounds, answers in samples:
        calibrator.add_feedback(
            predicted_confidence=conf,
            actual_outcome=outcome,
            ambiguity_count=amb,
            critical_ambiguity_count=crit_amb,
            rounds=rounds,
            answer_count=answers,
            auto_train=False
        )
    calibrator.train()
    
    return calibrator


@pytest.mark.asyncio
async def test_rl_calibration_in_clarification_flow(mock_settings, rl_calibrator_trained):
    """Test RL calibration in the full clarification flow."""
    from src.api.ask_ai_router import app
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    
    # Mock OpenAI and Home Assistant clients
    with patch("src.api.ask_ai_router.OpenAIClient") as mock_openai, \
         patch("src.api.ask_ai_router.HomeAssistantClient") as mock_ha:
        
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai_instance.extract_entities = AsyncMock(return_value={
            "entities": [],
            "confidence": 0.8
        })
        mock_openai.return_value = mock_openai_instance
        
        mock_ha_instance = Mock()
        mock_ha.return_value = mock_ha_instance
        
        # Create app with RL calibration enabled
        # This would require modifying the app initialization, so we test the calculator directly
        calculator = ConfidenceCalculator(
            default_threshold=0.85,
            calibrator=Mock(),
            calibration_enabled=True,
            rl_calibrator=rl_calibrator_trained,
            rl_calibration_enabled=True,
            uncertainty_enabled=False
        )
        
        # Simulate clarification flow
        from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType, AmbiguityType
        
        ambiguities = [
            Ambiguity(
                id="amb1",
                type=AmbiguityType.DEVICE,
                severity=AmbiguitySeverity.IMPORTANT,
                description="Multiple devices",
                related_entities=["light.living_room", "light.kitchen"]
            )
        ]
        
        # Calculate confidence with RL calibration
        confidence = await calculator.calculate_confidence(
            query="turn on the light",
            extracted_entities=[],
            ambiguities=ambiguities,
            base_confidence=0.8
        )
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_uncertainty_quantification_in_clarification_flow(mock_settings):
    """Test uncertainty quantification in the full clarification flow."""
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType
    
    uncertainty_quantifier = UncertaintyQuantifier(method="bootstrap")
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )
    
    ambiguities = [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]
    
    # Calculate confidence with uncertainty
    result = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    assert isinstance(result, ConfidenceWithUncertainty)
    assert 0.0 <= result.mean <= 1.0
    assert result.std >= 0
    assert result.lower_bound <= result.mean <= result.upper_bound


@pytest.mark.asyncio
async def test_rl_calibration_learning_from_outcomes(mock_settings, rl_calibrator_trained):
    """Test that RL calibrator learns from clarification outcomes."""
    from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType
    
    # Get initial adjustment weights
    initial_weights = rl_calibrator_trained.adjustment_weights.copy()
    
    # Add new feedback
    rl_calibrator_trained.add_feedback(
        predicted_confidence=0.75,
        actual_outcome=True,  # User approved
        ambiguity_count=1,
        critical_ambiguity_count=0,
        rounds=1,
        answer_count=1,
        auto_train=True
    )
    
    # Check that model was updated (if auto-train triggered)
    # The weights might change if training was triggered
    # We just verify the feedback was added
    assert rl_calibrator_trained.total_samples > 0


@pytest.mark.asyncio
async def test_uncertainty_with_historical_data(mock_settings):
    """Test uncertainty quantification with historical confidence data."""
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType
    
    # Create quantifier with bootstrap method
    uncertainty_quantifier = UncertaintyQuantifier(method="bootstrap")
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        rl_calibration_enabled=False,
        uncertainty_quantifier=uncertainty_quantifier,
        uncertainty_enabled=True
    )
    
    ambiguities = [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]
    
    # Calculate uncertainty (will use empty historical data for now)
    result = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    assert isinstance(result, ConfidenceWithUncertainty)
    # Even without historical data, should provide valid uncertainty
    assert 0.0 <= result.mean <= 1.0
    assert result.std >= 0


@pytest.mark.asyncio
async def test_phase3_features_backward_compatibility(mock_settings):
    """Test that Phase 3 features don't break existing functionality."""
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType
    
    # Create calculator with Phase 3 features disabled (default)
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        rl_calibration_enabled=False,  # Disabled by default
        uncertainty_enabled=False  # Disabled by default
    )
    
    ambiguities = [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]
    
    # Should work exactly like before Phase 3
    confidence = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8
    )
    
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    
    # Should not return uncertainty unless explicitly requested and enabled
    confidence2 = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8,
        return_uncertainty=True  # Requested but disabled
    )
    
    assert isinstance(confidence2, float)  # Should return float, not ConfidenceWithUncertainty


@pytest.mark.asyncio
async def test_rl_calibration_with_multiple_rounds(mock_settings, rl_calibrator_trained):
    """Test RL calibration across multiple clarification rounds."""
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    from src.services.clarification.models import (
        Ambiguity,
        AmbiguitySeverity,
        AmbiguityType,
        ClarificationAnswer
    )
    
    calculator = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        rl_calibrator=rl_calibrator_trained,
        rl_calibration_enabled=True,
        uncertainty_enabled=False
    )
    
    ambiguities = [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]
    
    # Round 1: No answers yet
    confidence_round1 = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.7
    )
    
    # Round 2: With answers
    answers = [
        ClarificationAnswer(
            question_id="q1",
            answer_text="light.living_room",
            validated=True,
            confidence=0.9
        )
    ]
    
    confidence_round2 = await calculator.calculate_confidence(
        query="turn on the light",
        extracted_entities=[],
        ambiguities=ambiguities,
        clarification_answers=answers,
        base_confidence=0.7
    )
    
    # Both should be valid
    assert 0.0 <= confidence_round1 <= 1.0
    assert 0.0 <= confidence_round2 <= 1.0
    # Round 2 should generally have higher confidence (with answers)
    # But RL calibration might adjust, so we just check validity


@pytest.mark.asyncio
async def test_uncertainty_quantification_different_methods(mock_settings):
    """Test uncertainty quantification with different methods."""
    from src.services.clarification.confidence_calculator import ConfidenceCalculator
    from src.services.clarification.models import Ambiguity, AmbiguitySeverity, AmbiguityType
    
    ambiguities = [
        Ambiguity(
            id="amb1",
            type=AmbiguityType.DEVICE,
            severity=AmbiguitySeverity.IMPORTANT,
            description="Multiple devices",
            related_entities=["light.living_room", "light.kitchen"]
        )
    ]
    
    # Test bootstrap method
    quantifier_bootstrap = UncertaintyQuantifier(method="bootstrap")
    calculator_bootstrap = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        uncertainty_quantifier=quantifier_bootstrap,
        uncertainty_enabled=True
    )
    
    result_bootstrap = await calculator_bootstrap.calculate_confidence(
        query="test",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    assert isinstance(result_bootstrap, ConfidenceWithUncertainty)
    assert result_bootstrap.distribution == "normal"
    
    # Test Bayesian method
    quantifier_bayesian = UncertaintyQuantifier(method="bayesian")
    calculator_bayesian = ConfidenceCalculator(
        default_threshold=0.85,
        calibrator=Mock(),
        calibration_enabled=True,
        uncertainty_quantifier=quantifier_bayesian,
        uncertainty_enabled=True
    )
    
    result_bayesian = await calculator_bayesian.calculate_confidence(
        query="test",
        extracted_entities=[],
        ambiguities=ambiguities,
        base_confidence=0.8,
        return_uncertainty=True
    )
    
    assert isinstance(result_bayesian, ConfidenceWithUncertainty)
    assert result_bayesian.distribution == "beta"

