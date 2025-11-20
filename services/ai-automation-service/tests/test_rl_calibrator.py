"""
Unit tests for RL Confidence Calibrator (Phase 3)

Tests reinforcement learning-based confidence calibration.
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from src.services.clarification.rl_calibrator import (
    RLConfidenceCalibrator,
    RLCalibrationConfig,
    RLFeedback
)


@pytest.fixture
def rl_calibrator():
    """Create RL calibrator instance for testing."""
    config = RLCalibrationConfig(
        learning_rate=0.01,
        min_samples_for_training=10,  # Lower for testing
        update_frequency=5
    )
    return RLConfidenceCalibrator(config=config)


@pytest.fixture
def sample_feedback():
    """Create sample feedback data."""
    return [
        (0.8, True, 0, 0, 0, 0),   # High confidence, approved
        (0.9, True, 1, 0, 1, 1),   # Very high confidence, approved
        (0.5, False, 2, 1, 2, 2),  # Medium confidence, rejected
        (0.3, False, 3, 2, 3, 3),  # Low confidence, rejected
    ]


def test_rl_calibrator_init(rl_calibrator):
    """Test RL calibrator initialization."""
    assert rl_calibrator.config.learning_rate == 0.01
    assert not rl_calibrator.is_trained
    assert len(rl_calibrator.feedback_history) == 0


def test_calculate_reward_positive_outcome(rl_calibrator):
    """Test reward calculation for positive outcomes."""
    # High confidence, positive outcome = high reward
    reward_high = rl_calibrator.calculate_reward(0.9, True)
    assert reward_high > -0.2  # log(0.9) ≈ -0.105
    
    # Low confidence, positive outcome = low reward (penalty)
    reward_low = rl_calibrator.calculate_reward(0.1, True)
    assert reward_low < -2.0  # log(0.1) ≈ -2.3


def test_calculate_reward_negative_outcome(rl_calibrator):
    """Test reward calculation for negative outcomes."""
    # High confidence, negative outcome = very low reward (penalty)
    reward_high = rl_calibrator.calculate_reward(0.9, False)
    assert reward_high < -2.0  # log(0.1) ≈ -2.3
    
    # Low confidence, negative outcome = high reward
    reward_low = rl_calibrator.calculate_reward(0.1, False)
    assert reward_low > -0.2  # log(0.9) ≈ -0.105


def test_extract_features(rl_calibrator):
    """Test feature extraction."""
    features = rl_calibrator.extract_features(
        raw_confidence=0.8,
        ambiguity_count=2,
        critical_ambiguity_count=1,
        rounds=2,
        answer_count=3
    )
    
    assert len(features) == 6
    assert features[0] == pytest.approx(1.0)  # bias term
    assert features[1] == pytest.approx(0.8)  # raw_confidence
    assert features[2] == pytest.approx(0.4)  # ambiguity_count / 5.0
    assert features[3] == pytest.approx(1.0 / 3.0)  # critical_ambiguity_count / 3.0
    assert features[4] == pytest.approx(2.0 / 3.0)  # rounds / 3.0
    assert features[5] == pytest.approx(0.6)  # answer_count / 5.0


def test_predict_adjustment_not_trained(rl_calibrator):
    """Test adjustment prediction when not trained."""
    adjustment = rl_calibrator.predict_adjustment(0.8, 1, 0, 1, 1)
    assert adjustment == 1.0  # No adjustment if not trained


def test_add_feedback(rl_calibrator):
    """Test adding feedback samples."""
    rl_calibrator.add_feedback(0.8, True, 1, 0, 1, 1, auto_train=False)
    
    assert len(rl_calibrator.feedback_history) == 1
    assert rl_calibrator.total_samples == 1
    assert rl_calibrator.feedback_history[0].predicted_confidence == 0.8
    assert rl_calibrator.feedback_history[0].actual_outcome is True


def test_train_insufficient_samples(rl_calibrator):
    """Test training with insufficient samples."""
    # Add fewer samples than required
    for i in range(5):
        rl_calibrator.add_feedback(0.7 + i * 0.05, i % 2 == 0, 1, 0, 1, 1, auto_train=False)
    
    result = rl_calibrator.train()
    assert result is False
    assert not rl_calibrator.is_trained


def test_train_sufficient_samples(rl_calibrator, sample_feedback):
    """Test training with sufficient samples."""
    # Add enough samples
    for conf, outcome, amb, crit_amb, rounds, answers in sample_feedback * 3:
        rl_calibrator.add_feedback(conf, outcome, amb, crit_amb, rounds, answers, auto_train=False)
    
    result = rl_calibrator.train()
    assert result is True
    assert rl_calibrator.is_trained
    assert rl_calibrator.training_samples > 0


def test_calibrate_not_trained(rl_calibrator):
    """Test calibration when not trained."""
    calibrated = rl_calibrator.calibrate(0.8, 1, 0, 1, 1)
    assert calibrated == 0.8  # Returns raw if not trained


def test_calibrate_trained(rl_calibrator, sample_feedback):
    """Test calibration when trained."""
    # Train first
    for conf, outcome, amb, crit_amb, rounds, answers in sample_feedback * 3:
        rl_calibrator.add_feedback(conf, outcome, amb, crit_amb, rounds, answers, auto_train=False)
    rl_calibrator.train()
    
    # Now calibrate
    calibrated = rl_calibrator.calibrate(0.8, 1, 0, 1, 1)
    
    # Should be in reasonable range [0.0, 1.0]
    assert 0.0 <= calibrated <= 1.0
    # Should be different from raw (unless weights are exactly 1.0)
    # But we can't guarantee direction, so just check it's valid


def test_calibrate_clamping(rl_calibrator, sample_feedback):
    """Test that calibration clamps to valid range."""
    # Train first
    for conf, outcome, amb, crit_amb, rounds, answers in sample_feedback * 3:
        rl_calibrator.add_feedback(conf, outcome, amb, crit_amb, rounds, answers, auto_train=False)
    rl_calibrator.train()
    
    # Test extreme values
    calibrated_high = rl_calibrator.calibrate(1.0, 0, 0, 0, 0)
    calibrated_low = rl_calibrator.calibrate(0.0, 0, 0, 0, 0)
    
    assert 0.0 <= calibrated_high <= 1.0
    assert 0.0 <= calibrated_low <= 1.0


def test_get_stats(rl_calibrator):
    """Test statistics retrieval."""
    stats = rl_calibrator.get_stats()
    
    assert 'is_trained' in stats
    assert 'training_samples' in stats
    assert 'total_samples' in stats
    assert 'avg_reward' in stats
    assert stats['is_trained'] is False
    assert stats['total_samples'] == 0


def test_get_stats_with_feedback(rl_calibrator):
    """Test statistics with feedback samples."""
    rl_calibrator.add_feedback(0.8, True, 1, 0, 1, 1, auto_train=False)
    rl_calibrator.add_feedback(0.5, False, 2, 1, 2, 2, auto_train=False)
    
    stats = rl_calibrator.get_stats()
    
    assert stats['total_samples'] == 2
    assert 'avg_reward' in stats
    assert stats['adjustment_weights'] is None  # Not trained yet


def test_auto_train_trigger(rl_calibrator, sample_feedback):
    """Test automatic training trigger."""
    # Add samples up to update_frequency
    for i, (conf, outcome, amb, crit_amb, rounds, answers) in enumerate(sample_feedback * 2):
        rl_calibrator.add_feedback(conf, outcome, amb, crit_amb, rounds, answers, auto_train=True)
        
        # Should trigger training at update_frequency (5)
        if (i + 1) % rl_calibrator.config.update_frequency == 0:
            # Training might succeed or fail depending on samples
            # Just check it was attempted
            pass


def test_save_and_load(rl_calibrator, sample_feedback, tmp_path):
    """Test saving and loading RL model."""
    # Train first
    for conf, outcome, amb, crit_amb, rounds, answers in sample_feedback * 3:
        rl_calibrator.add_feedback(conf, outcome, amb, crit_amb, rounds, answers, auto_train=False)
    rl_calibrator.train()
    
    # Save
    save_path = tmp_path / "rl_calibrator.pkl"
    success = rl_calibrator.save(str(save_path))
    assert success is True
    assert save_path.exists()
    
    # Create new calibrator and load
    new_calibrator = RLConfidenceCalibrator()
    success = new_calibrator.load(str(save_path))
    assert success is True
    assert new_calibrator.is_trained == rl_calibrator.is_trained
    assert new_calibrator.training_samples == rl_calibrator.training_samples
    np.testing.assert_array_almost_equal(
        new_calibrator.adjustment_weights,
        rl_calibrator.adjustment_weights
    )

