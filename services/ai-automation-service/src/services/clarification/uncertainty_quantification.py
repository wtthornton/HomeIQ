"""
Uncertainty Quantification for Confidence Scores

Provides confidence intervals and probability distributions instead of single point estimates.
Uses bootstrap sampling and statistical methods for uncertainty estimation.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Dataclasses for type-safe data structures
- Literal types for distribution names
- NumPy and SciPy for statistical operations
"""

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceWithUncertainty:
    """
    Confidence score with uncertainty quantification.

    Uses 2025 best practices: type hints, Literal types, dataclasses.
    """
    mean: float  # Expected confidence
    std: float  # Standard deviation
    lower_bound: float  # Confidence interval lower bound
    upper_bound: float  # Confidence interval upper bound
    distribution: Literal["normal", "beta", "gamma"] = "normal"  # Type-safe distribution
    confidence_level: float = 0.90  # Confidence interval level (e.g., 0.90 for 90% CI)

    def __post_init__(self):
        """Validate bounds after initialization."""
        # Ensure bounds are in valid range
        self.lower_bound = max(0.0, min(1.0, self.lower_bound))
        self.upper_bound = max(0.0, min(1.0, self.upper_bound))
        # Ensure lower <= upper
        if self.lower_bound > self.upper_bound:
            self.lower_bound, self.upper_bound = self.upper_bound, self.lower_bound


class UncertaintyQuantifier:
    """
    Quantify uncertainty in confidence scores.

    Provides confidence intervals and probability distributions using
    bootstrap sampling or Bayesian methods.

    Uses 2025 best practices: type hints, numpy/scipy for statistics.
    """

    def __init__(self, method: Literal["bootstrap", "bayesian"] = "bootstrap"):
        """
        Initialize uncertainty quantifier.

        Args:
            method: Method for uncertainty quantification
                - "bootstrap": Bootstrap sampling (simpler, faster)
                - "bayesian": Bayesian approach (more sophisticated)
        """
        self.method = method

    def calculate_uncertainty_bootstrap(
        self,
        raw_confidence: float,
        historical_data: np.ndarray,
        n_samples: int = 1000,
        confidence_level: float = 0.90,
    ) -> ConfidenceWithUncertainty:
        """
        Calculate uncertainty using bootstrap sampling.

        Bootstrap method:
        1. Resample historical confidence scores
        2. Calculate statistics on resampled data
        3. Estimate confidence intervals

        Args:
            raw_confidence: Raw confidence score
            historical_data: Historical confidence scores for uncertainty estimation
            n_samples: Number of bootstrap samples
            confidence_level: Confidence interval level (0.90 for 90% CI)

        Returns:
            ConfidenceWithUncertainty with mean, std, and confidence intervals
        """
        if len(historical_data) == 0:
            # No historical data - return point estimate with default uncertainty
            std_estimate = 0.1  # Default uncertainty
            return ConfidenceWithUncertainty(
                mean=raw_confidence,
                std=std_estimate,
                lower_bound=max(0.0, raw_confidence - 1.645 * std_estimate),  # 90% CI
                upper_bound=min(1.0, raw_confidence + 1.645 * std_estimate),
                distribution="normal",
                confidence_level=confidence_level,
            )

        # Bootstrap sampling
        bootstrap_samples: list[float] = []

        for _ in range(n_samples):
            # Resample with replacement
            resampled = np.random.choice(historical_data, size=len(historical_data), replace=True)
            # Calculate mean of resampled data
            bootstrap_samples.append(float(np.mean(resampled)))

        bootstrap_array = np.array(bootstrap_samples)

        # Calculate statistics
        mean = float(np.mean(bootstrap_array))
        std = float(np.std(bootstrap_array))

        # Calculate confidence intervals
        alpha = 1.0 - confidence_level
        lower_bound = float(np.percentile(bootstrap_array, 100 * alpha / 2))
        upper_bound = float(np.percentile(bootstrap_array, 100 * (1 - alpha / 2)))

        return ConfidenceWithUncertainty(
            mean=mean,
            std=std,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            distribution="normal",
            confidence_level=confidence_level,
        )

    def calculate_uncertainty_bayesian(
        self,
        raw_confidence: float,
        historical_data: np.ndarray,
        confidence_level: float = 0.90,
    ) -> ConfidenceWithUncertainty:
        """
        Calculate uncertainty using Bayesian approach.

        Uses Beta distribution (conjugate prior for binomial) to model confidence.

        Args:
            raw_confidence: Raw confidence score
            historical_data: Historical confidence scores for uncertainty estimation
            confidence_level: Confidence interval level (0.90 for 90% CI)

        Returns:
            ConfidenceWithUncertainty with mean, std, and confidence intervals
        """
        if len(historical_data) == 0:
            # No historical data - use uniform prior
            alpha, beta = 1.0, 1.0
        else:
            # Estimate Beta distribution parameters from historical data
            # Beta distribution is bounded [0, 1], perfect for confidence scores
            mean_hist = np.mean(historical_data)
            var_hist = np.var(historical_data)

            # Method of moments for Beta distribution
            # mean = alpha / (alpha + beta)
            # var = alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1))
            if var_hist > 0 and mean_hist > 0 and mean_hist < 1:
                alpha = mean_hist * (mean_hist * (1 - mean_hist) / var_hist - 1)
                beta = (1 - mean_hist) * (mean_hist * (1 - mean_hist) / var_hist - 1)

                # Ensure positive parameters
                alpha = max(0.1, alpha)
                beta = max(0.1, beta)
            else:
                # Fallback to uniform
                alpha, beta = 1.0, 1.0

        # Update with current observation
        # Treat raw_confidence as a sample from Beta(alpha, beta)
        # For simplicity, we add it as a weighted observation
        alpha_posterior = alpha + raw_confidence * 10  # Weight current observation
        beta_posterior = beta + (1 - raw_confidence) * 10

        # Calculate statistics from Beta distribution
        mean = alpha_posterior / (alpha_posterior + beta_posterior)
        var = (alpha_posterior * beta_posterior) / (
            (alpha_posterior + beta_posterior) ** 2 * (alpha_posterior + beta_posterior + 1)
        )
        std = np.sqrt(var)

        # Calculate confidence intervals using Beta distribution
        alpha_ci = (1.0 - confidence_level) / 2
        lower_bound = float(stats.beta.ppf(alpha_ci, alpha_posterior, beta_posterior))
        upper_bound = float(stats.beta.ppf(1 - alpha_ci, alpha_posterior, beta_posterior))

        return ConfidenceWithUncertainty(
            mean=float(mean),
            std=float(std),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            distribution="beta",
            confidence_level=confidence_level,
        )

    def calculate_uncertainty(
        self,
        raw_confidence: float,
        historical_data: np.ndarray | None = None,
        confidence_level: float = 0.90,
    ) -> ConfidenceWithUncertainty:
        """
        Calculate confidence with uncertainty bounds.

        Args:
            raw_confidence: Raw confidence score
            historical_data: Optional historical confidence scores for uncertainty estimation
            confidence_level: Confidence interval level (0.90 for 90% CI)

        Returns:
            ConfidenceWithUncertainty with mean, std, and confidence intervals
        """
        if historical_data is None:
            historical_data = np.array([])

        if self.method == "bootstrap":
            return self.calculate_uncertainty_bootstrap(
                raw_confidence, historical_data, confidence_level=confidence_level,
            )
        if self.method == "bayesian":
            return self.calculate_uncertainty_bayesian(
                raw_confidence, historical_data, confidence_level=confidence_level,
            )
        msg = f"Unknown method: {self.method}"
        raise ValueError(msg)

    def get_uncertainty_summary(self, uncertainty: ConfidenceWithUncertainty) -> str:
        """
        Get human-readable summary of uncertainty.

        Args:
            uncertainty: ConfidenceWithUncertainty object

        Returns:
            Human-readable summary string
        """
        return (
            f"Confidence: {uncertainty.mean:.2f} "
            f"({uncertainty.confidence_level*100:.0f}% CI: "
            f"[{uncertainty.lower_bound:.2f}, {uncertainty.upper_bound:.2f}], "
            f"std={uncertainty.std:.3f})"
        )

