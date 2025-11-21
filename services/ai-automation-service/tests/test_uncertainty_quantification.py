"""
Unit tests for Uncertainty Quantification (Phase 3)

Tests confidence intervals and probability distributions.
"""

import numpy as np
import pytest
from src.services.clarification.uncertainty_quantification import (
    ConfidenceWithUncertainty,
    UncertaintyQuantifier,
)


@pytest.fixture
def quantifier_bootstrap():
    """Create bootstrap uncertainty quantifier."""
    return UncertaintyQuantifier(method="bootstrap")


@pytest.fixture
def quantifier_bayesian():
    """Create Bayesian uncertainty quantifier."""
    return UncertaintyQuantifier(method="bayesian")


@pytest.fixture
def sample_historical_data():
    """Create sample historical confidence data."""
    # Simulate historical confidence scores
    return np.array([0.7, 0.75, 0.8, 0.85, 0.9, 0.75, 0.8, 0.85, 0.9, 0.95])


def test_confidence_with_uncertainty_init():
    """Test ConfidenceWithUncertainty initialization."""
    uncertainty = ConfidenceWithUncertainty(
        mean=0.8,
        std=0.1,
        lower_bound=0.7,
        upper_bound=0.9,
        distribution="normal",
        confidence_level=0.90,
    )

    assert uncertainty.mean == 0.8
    assert uncertainty.std == 0.1
    assert uncertainty.lower_bound == 0.7
    assert uncertainty.upper_bound == 0.9
    assert uncertainty.distribution == "normal"
    assert uncertainty.confidence_level == 0.90


def test_confidence_with_uncertainty_bounds_validation():
    """Test that bounds are validated and clamped."""
    # Test clamping to [0, 1]
    uncertainty = ConfidenceWithUncertainty(
        mean=0.8,
        std=0.1,
        lower_bound=-0.1,  # Should be clamped to 0.0
        upper_bound=1.5,   # Should be clamped to 1.0
    )

    assert uncertainty.lower_bound == 0.0
    assert uncertainty.upper_bound == 1.0


def test_confidence_with_uncertainty_bounds_swap():
    """Test that bounds are swapped if lower > upper."""
    uncertainty = ConfidenceWithUncertainty(
        mean=0.8,
        std=0.1,
        lower_bound=0.9,  # Should be swapped
        upper_bound=0.7,
    )

    assert uncertainty.lower_bound <= uncertainty.upper_bound


def test_bootstrap_no_historical_data(quantifier_bootstrap):
    """Test bootstrap with no historical data."""
    uncertainty = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=np.array([]),
        confidence_level=0.90,
    )

    assert uncertainty.mean == 0.8
    assert uncertainty.std > 0
    assert 0.0 <= uncertainty.lower_bound <= 1.0
    assert 0.0 <= uncertainty.upper_bound <= 1.0
    assert uncertainty.lower_bound <= uncertainty.upper_bound
    assert uncertainty.distribution == "normal"


def test_bootstrap_with_historical_data(quantifier_bootstrap, sample_historical_data):
    """Test bootstrap with historical data."""
    uncertainty = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    assert 0.0 <= uncertainty.mean <= 1.0
    assert uncertainty.std >= 0
    assert 0.0 <= uncertainty.lower_bound <= 1.0
    assert 0.0 <= uncertainty.upper_bound <= 1.0
    assert uncertainty.lower_bound <= uncertainty.upper_bound
    assert uncertainty.distribution == "normal"
    assert uncertainty.confidence_level == 0.90


def test_bootstrap_confidence_intervals(quantifier_bootstrap, sample_historical_data):
    """Test that bootstrap produces valid confidence intervals."""
    uncertainty = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    # Mean should be within bounds
    assert uncertainty.lower_bound <= uncertainty.mean <= uncertainty.upper_bound

    # Bounds should be reasonable
    assert uncertainty.upper_bound - uncertainty.lower_bound > 0


def test_bayesian_no_historical_data(quantifier_bayesian):
    """Test Bayesian approach with no historical data."""
    uncertainty = quantifier_bayesian.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=np.array([]),
        confidence_level=0.90,
    )

    assert 0.0 <= uncertainty.mean <= 1.0
    assert uncertainty.std >= 0
    assert 0.0 <= uncertainty.lower_bound <= 1.0
    assert 0.0 <= uncertainty.upper_bound <= 1.0
    assert uncertainty.lower_bound <= uncertainty.upper_bound
    assert uncertainty.distribution == "beta"


def test_bayesian_with_historical_data(quantifier_bayesian, sample_historical_data):
    """Test Bayesian approach with historical data."""
    uncertainty = quantifier_bayesian.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    assert 0.0 <= uncertainty.mean <= 1.0
    assert uncertainty.std >= 0
    assert 0.0 <= uncertainty.lower_bound <= 1.0
    assert 0.0 <= uncertainty.upper_bound <= 1.0
    assert uncertainty.lower_bound <= uncertainty.upper_bound
    assert uncertainty.distribution == "beta"


def test_bayesian_confidence_intervals(quantifier_bayesian, sample_historical_data):
    """Test that Bayesian approach produces valid confidence intervals."""
    uncertainty = quantifier_bayesian.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    # Mean should be within bounds
    assert uncertainty.lower_bound <= uncertainty.mean <= uncertainty.upper_bound

    # Bounds should be reasonable
    assert uncertainty.upper_bound - uncertainty.lower_bound > 0


def test_different_confidence_levels(quantifier_bootstrap, sample_historical_data):
    """Test different confidence interval levels."""
    uncertainty_90 = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    uncertainty_95 = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.95,
    )

    # 95% CI should be wider than 90% CI
    width_90 = uncertainty_90.upper_bound - uncertainty_90.lower_bound
    width_95 = uncertainty_95.upper_bound - uncertainty_95.lower_bound

    assert width_95 >= width_90


def test_get_uncertainty_summary(quantifier_bootstrap, sample_historical_data):
    """Test human-readable summary generation."""
    uncertainty = quantifier_bootstrap.calculate_uncertainty(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        confidence_level=0.90,
    )

    summary = quantifier_bootstrap.get_uncertainty_summary(uncertainty)

    assert isinstance(summary, str)
    assert "Confidence:" in summary
    assert "CI:" in summary
    assert "std=" in summary


def test_unknown_method():
    """Test that unknown method raises error."""
    quantifier = UncertaintyQuantifier(method="unknown")  # type: ignore

    with pytest.raises(ValueError, match="Unknown method"):
        quantifier.calculate_uncertainty(0.8, np.array([]))


def test_bootstrap_n_samples(quantifier_bootstrap, sample_historical_data):
    """Test bootstrap with different sample sizes."""
    uncertainty = quantifier_bootstrap.calculate_uncertainty_bootstrap(
        raw_confidence=0.8,
        historical_data=sample_historical_data,
        n_samples=500,  # Smaller for faster tests
        confidence_level=0.90,
    )

    assert 0.0 <= uncertainty.mean <= 1.0
    assert uncertainty.std >= 0
    assert 0.0 <= uncertainty.lower_bound <= 1.0
    assert 0.0 <= uncertainty.upper_bound <= 1.0

