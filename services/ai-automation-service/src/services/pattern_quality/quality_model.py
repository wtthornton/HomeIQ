"""
Pattern Quality Model

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.2: Pattern Quality Model Training

RandomForest classifier for pattern quality prediction.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
import joblib

from .feature_extractor import PatternFeatureExtractor
from .features import PatternFeatures

logger = logging.getLogger(__name__)


class PatternQualityModel:
    """
    RandomForest classifier for pattern quality prediction.
    
    Predicts probability that a pattern is "good" (approved by users).
    """
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        random_state: int = 42
    ):
        """
        Initialize RandomForest classifier.
        
        Args:
            n_estimators: Number of trees in forest
            max_depth: Maximum depth of trees
            random_state: Random seed for reproducibility
        """
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight='balanced',  # Handle class imbalance
            n_jobs=-1  # Use all CPU cores
        )
        self.feature_extractor = PatternFeatureExtractor()
        self.version = "1.0.0"
        self.trained_at: datetime | None = None
        self.metrics: dict[str, float] = {}
        self.feature_importance: dict[str, float] | None = None
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validation_split: float = 0.2
    ) -> dict[str, float]:
        """
        Train model on features and labels.
        
        Args:
            X: Feature array (n_samples, n_features)
            y: Labels (0=rejected, 1=approved)
            validation_split: Fraction for validation set
        
        Returns:
            Dictionary with training metrics
        """
        if len(X) == 0:
            raise ValueError("No training data provided")
        
        if len(np.unique(y)) < 2:
            logger.warning("Only one class in training data, model may not train properly")
        
        # Train/test split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            random_state=42,
            stratify=y if len(np.unique(y)) > 1 else None
        )
        
        logger.info(f"Training model on {len(X_train)} samples, validating on {len(X_val)} samples")
        
        # Train model
        self.model.fit(X_train, y_train)
        
        # Evaluate on validation set
        y_pred = self.model.predict(X_val)
        y_pred_proba = self.model.predict_proba(X_val)[:, 1] if len(np.unique(y_val)) > 1 else np.zeros(len(y_val))
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'precision': precision_score(y_val, y_pred, zero_division=0),
            'recall': recall_score(y_val, y_pred, zero_division=0),
            'f1': f1_score(y_val, y_pred, zero_division=0),
        }
        
        # ROC AUC (only if both classes present)
        if len(np.unique(y_val)) > 1:
            metrics['roc_auc'] = roc_auc_score(y_val, y_pred_proba)
        else:
            metrics['roc_auc'] = 0.0
        
        # Confusion matrix
        cm = confusion_matrix(y_val, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        metrics['true_positives'] = int(cm[1, 1]) if cm.shape == (2, 2) else 0
        metrics['true_negatives'] = int(cm[0, 0]) if cm.shape == (2, 2) else 0
        metrics['false_positives'] = int(cm[0, 1]) if cm.shape == (2, 2) else 0
        metrics['false_negatives'] = int(cm[1, 0]) if cm.shape == (2, 2) else 0
        
        # Feature importance
        feature_names = PatternFeatures.feature_names()
        importances = self.model.feature_importances_
        self.feature_importance = dict(zip(feature_names, importances.tolist()))
        
        self.metrics = metrics
        self.trained_at = datetime.now(timezone.utc)
        
        logger.info(f"Model training complete. Accuracy: {metrics['accuracy']:.3f}, F1: {metrics['f1']:.3f}")
        
        return metrics
    
    def predict_quality(
        self,
        pattern: Any  # Pattern model or dict[str, Any]
    ) -> float:
        """
        Predict quality score for a pattern.
        
        Args:
            pattern: Pattern model or dict
        
        Returns:
            Quality score (0.0-1.0, probability of being good)
        """
        if not hasattr(self.model, 'classes_'):
            logger.warning("Model not trained, returning default quality score")
            return 0.5
        
        # Extract features
        features = self.feature_extractor.extract_features(pattern)
        feature_array = self.feature_extractor.to_numpy_array(features)
        
        # Predict probability
        proba = self.model.predict_proba(feature_array)[0]
        
        # Return probability of class 1 (approved)
        if len(proba) > 1:
            return float(proba[1])
        else:
            return float(proba[0])
    
    def predict_quality_batch(
        self,
        patterns: list[Any]  # list[Pattern] | list[dict[str, Any]]
    ) -> list[float]:
        """
        Predict quality scores for multiple patterns.
        
        Args:
            patterns: List of Pattern models or dicts
        
        Returns:
            List of quality scores
        """
        if not hasattr(self.model, 'classes_'):
            logger.warning("Model not trained, returning default quality scores")
            return [0.5] * len(patterns)
        
        # Extract features for all patterns
        features_list = self.feature_extractor.extract_features_batch(patterns)
        feature_array = self.feature_extractor.to_numpy_array(features_list)
        
        # Predict probabilities
        proba = self.model.predict_proba(feature_array)
        
        # Return probability of class 1 (approved) for each pattern
        if proba.shape[1] > 1:
            return proba[:, 1].tolist()
        else:
            return proba[:, 0].tolist()
    
    def save(self, model_path: Path) -> None:
        """
        Save model to disk.
        
        Args:
            model_path: Path to save model file
        """
        model_data = {
            'model': self.model,
            'version': self.version,
            'trained_at': self.trained_at,
            'metrics': self.metrics,
            'feature_extractor': self.feature_extractor,
            'feature_importance': self.feature_importance
        }
        
        # Ensure directory exists
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")
    
    @classmethod
    def load(cls, model_path: Path) -> 'PatternQualityModel':
        """
        Load model from disk.
        
        Args:
            model_path: Path to model file
        
        Returns:
            Loaded PatternQualityModel instance
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model_data = joblib.load(model_path)
        
        instance = cls()
        instance.model = model_data['model']
        instance.version = model_data.get('version', '1.0.0')
        instance.trained_at = model_data.get('trained_at')
        instance.metrics = model_data.get('metrics', {})
        instance.feature_extractor = model_data.get('feature_extractor', PatternFeatureExtractor())
        instance.feature_importance = model_data.get('feature_importance')
        
        logger.info(f"Model loaded from {model_path} (version {instance.version})")
        
        return instance
    
    def get_feature_importance(self, top_n: int = 10) -> dict[str, float]:
        """
        Get top N most important features.
        
        Args:
            top_n: Number of top features to return
        
        Returns:
            Dictionary of feature names to importance scores
        """
        if self.feature_importance is None:
            return {}
        
        # Sort by importance
        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return dict(sorted_features[:top_n])

