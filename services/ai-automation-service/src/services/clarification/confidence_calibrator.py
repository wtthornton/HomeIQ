"""
Clarification Confidence Calibration

Uses ML-based calibration to improve clarification confidence score reliability.
Learns from user feedback on clarification outcomes (proceeded, suggestion approved).

2025 Best Practices:
- scikit-learn 1.5.0+ CalibratedClassifierCV with isotonic regression
- Full type hints (PEP 484/526)
- NumPy 1.26.0+ for numerical operations
"""

import logging
import os
import pickle
from typing import Any

import numpy as np

# Scikit-learn imports for calibration (2025 best practices)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class ClarificationConfidenceCalibrator:
    """
    Calibrates clarification confidence scores using user feedback.

    Uses scikit-learn 1.5+ CalibratedClassifierCV with isotonic regression
    for 2025 best-practice confidence calibration.

    Maps raw confidence scores to calibrated probabilities that match actual accuracy.
    """

    def __init__(self, model_path: str | None = None) -> None:
        """
        Initialize confidence calibrator.

        Args:
            model_path: Optional path to save/load calibrated model
        """
        self.model_path = model_path or "clarification_calibrator.pkl"
        self.scaler = StandardScaler()
        self.calibrator: CalibratedClassifierCV | None = None
        self.is_fitted: bool = False

        # Training data storage
        self.features_history: list[np.ndarray] = []
        self.labels_history: list[int] = []

        logger.info("ClarificationConfidenceCalibrator initialized")

    def extract_features(
        self,
        raw_confidence: float,
        ambiguity_count: int = 0,
        critical_ambiguity_count: int = 0,
        rounds: int = 0,
        answer_count: int = 0,
    ) -> np.ndarray:
        """
        Extract features from clarification context for calibration.

        Features include:
        - Raw confidence score
        - Ambiguity count
        - Critical ambiguity count
        - Clarification rounds
        - Answer count

        Args:
            raw_confidence: Raw confidence score (0.0-1.0)
            ambiguity_count: Total number of ambiguities
            critical_ambiguity_count: Number of critical ambiguities
            rounds: Number of clarification rounds
            answer_count: Number of answers provided

        Returns:
            Feature vector as numpy array
        """
        features = []

        # Raw confidence (0-1)
        features.append(raw_confidence)

        # Ambiguity count (normalized)
        features.append(min(ambiguity_count / 5.0, 1.0))  # Max at 5 ambiguities

        # Critical ambiguity count (normalized)
        features.append(min(critical_ambiguity_count / 3.0, 1.0))  # Max at 3 critical

        # Clarification rounds (normalized)
        features.append(min(rounds / 3.0, 1.0))  # Max at 3 rounds

        # Answer count (normalized)
        features.append(min(answer_count / 5.0, 1.0))  # Max at 5 answers

        return np.array(features, dtype=np.float32)

    def add_feedback(
        self,
        raw_confidence: float,
        actually_proceeded: bool,
        suggestion_approved: bool | None = None,
        ambiguity_count: int = 0,
        critical_ambiguity_count: int = 0,
        rounds: int = 0,
        answer_count: int = 0,
        save_immediately: bool = False,
    ) -> None:
        """
        Add user feedback for clarification calibration.

        Args:
            raw_confidence: Raw confidence score before calibration
            actually_proceeded: True if user proceeded after clarification (confidence >= threshold)
            suggestion_approved: True if suggestion was approved, False if rejected, None if unknown
            ambiguity_count: Total number of ambiguities
            critical_ambiguity_count: Number of critical ambiguities
            rounds: Number of clarification rounds
            answer_count: Number of answers provided
            save_immediately: If True, retrain and save model immediately
        """
        # Use suggestion_approved if available, otherwise use actually_proceeded
        # A successful outcome is when user proceeded AND (suggestion approved OR unknown)
        outcome = actually_proceeded and (suggestion_approved is not False)

        features = self.extract_features(
            raw_confidence=raw_confidence,
            ambiguity_count=ambiguity_count,
            critical_ambiguity_count=critical_ambiguity_count,
            rounds=rounds,
            answer_count=answer_count,
        )
        label = 1 if outcome else 0

        self.features_history.append(features)
        self.labels_history.append(label)

        logger.debug(
            f"Added clarification feedback: confidence={raw_confidence:.2f}, "
            f"proceeded={actually_proceeded}, approved={suggestion_approved}, outcome={outcome}",
        )

        # Auto-retrain if we have enough samples (Phase 1.1)
        min_samples = 10  # Minimum samples for training
        if len(self.features_history) >= min_samples and len(self.features_history) % 50 == 0:
            # Retrain every 50 new samples
            logger.info(f"Auto-retraining calibration model with {len(self.features_history)} samples")
            self.train(min_samples=min_samples)
            self.save()
        elif save_immediately:
            self.train()
            self.save()

    def train(self, min_samples: int = 10) -> None:
        """
        Train calibration model on accumulated feedback.

        Uses scikit-learn 1.5+ best practices: 5-fold cross-validation for isotonic regression.

        Args:
            min_samples: Minimum number of samples required for training
        """
        if len(self.features_history) < min_samples:
            logger.warning(
                f"Insufficient training data: {len(self.features_history)} < {min_samples}",
            )
            return

        try:
            # Convert to numpy arrays
            X = np.array(self.features_history)
            y = np.array(self.labels_history)

            # Scale features
            X_scaled = self.scaler.fit_transform(X)

            # Split for validation (80/20)
            if len(X) >= 20:
                X_train, X_val, y_train, y_val = train_test_split(
                    X_scaled, y, test_size=0.2, random_state=42, stratify=y,
                )
            else:
                X_train, y_train = X_scaled, y
                X_val, y_val = None, None

            # Train base classifier (2025 best practice: max_iter=1000, random_state for reproducibility)
            base_classifier = LogisticRegression(random_state=42, max_iter=1000)

            # Calibrate using isotonic regression (2025 best practice: 5-fold CV for small datasets)
            # scikit-learn 1.5+ recommends 5-fold CV for isotonic regression
            cv_folds = min(5, len(X_train) // 2) if len(X_train) >= 10 else 2
            self.calibrator = CalibratedClassifierCV(
                base_classifier,
                method="isotonic",  # Best for small datasets (< 1000 samples)
                cv=cv_folds,
            )

            self.calibrator.fit(X_train, y_train)
            self.is_fitted = True

            # Evaluate on validation set if available
            if X_val is not None:
                val_score = self.calibrator.score(X_val, y_val)
                logger.info(
                    f"Clarification calibration model trained: {len(X_train)} samples, "
                    f"validation accuracy: {val_score:.2%}",
                )
            else:
                train_score = self.calibrator.score(X_train, y_train)
                logger.info(
                    f"Clarification calibration model trained: {len(X_train)} samples, "
                    f"training accuracy: {train_score:.2%}",
                )

        except Exception as e:
            logger.error(f"Failed to train clarification calibration model: {e}", exc_info=True)
            self.is_fitted = False

    def calibrate(
        self,
        raw_confidence: float,
        ambiguity_count: int = 0,
        critical_ambiguity_count: int = 0,
        rounds: int = 0,
        answer_count: int = 0,
    ) -> float:
        """
        Calibrate clarification confidence score.

        Args:
            raw_confidence: Raw confidence score (0.0-1.0)
            ambiguity_count: Total number of ambiguities
            critical_ambiguity_count: Number of critical ambiguities
            rounds: Number of clarification rounds
            answer_count: Number of answers provided

        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        if not self.is_fitted or self.calibrator is None:
            # Return original confidence if model not trained
            logger.debug("Calibration model not fitted, using raw confidence")
            return raw_confidence

        try:
            # Extract features
            features = self.extract_features(
                raw_confidence=raw_confidence,
                ambiguity_count=ambiguity_count,
                critical_ambiguity_count=critical_ambiguity_count,
                rounds=rounds,
                answer_count=answer_count,
            )
            features_scaled = self.scaler.transform(features.reshape(1, -1))

            # Predict calibrated probability
            calibrated_prob = self.calibrator.predict_proba(features_scaled)[0][1]

            # Blend with original confidence (weighted average)
            # Use more weight on calibrated score if we have enough training data
            weight = min(len(self.features_history) / 50.0, 0.7)  # Max 70% weight on calibrated
            calibrated_confidence = (
                weight * calibrated_prob +
                (1 - weight) * raw_confidence
            )

            return float(np.clip(calibrated_confidence, 0.0, 1.0))

        except Exception as e:
            logger.warning(f"Calibration failed for confidence {raw_confidence:.2f}: {e}")
            return raw_confidence

    def save(self, path: str | None = None) -> None:
        """Save calibrator model to disk."""
        save_path = path or self.model_path

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)

            with open(save_path, "wb") as f:
                pickle.dump({
                    "scaler": self.scaler,
                    "calibrator": self.calibrator,
                    "is_fitted": self.is_fitted,
                    "features_history": self.features_history,
                    "labels_history": self.labels_history,
                }, f)

            logger.info(f"Clarification calibrator model saved to {save_path}")
        except Exception as e:
            logger.exception(f"Failed to save clarification calibrator model: {e}")

    def load(self, path: str | None = None) -> bool:
        """
        Load calibrator model from disk.

        Returns:
            True if model loaded successfully, False otherwise
        """
        load_path = path or self.model_path

        if not os.path.exists(load_path):
            logger.warning(f"Clarification calibrator model not found at {load_path}")
            return False

        try:
            with open(load_path, "rb") as f:
                data = pickle.load(f)

            self.scaler = data.get("scaler", StandardScaler())
            self.calibrator = data.get("calibrator")
            self.is_fitted = data.get("is_fitted", False)
            self.features_history = data.get("features_history", [])
            self.labels_history = data.get("labels_history", [])

            logger.info(
                f"Clarification calibrator model loaded from {load_path}: "
                f"{len(self.features_history)} training samples",
            )
            return True
        except Exception as e:
            logger.exception(f"Failed to load clarification calibrator model: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get calibration statistics."""
        return {
            "is_fitted": self.is_fitted,
            "training_samples": len(self.features_history),
            "positive_feedback": sum(self.labels_history) if self.labels_history else 0,
            "negative_feedback": len(self.labels_history) - sum(self.labels_history) if self.labels_history else 0,
            "model_path": self.model_path,
        }

