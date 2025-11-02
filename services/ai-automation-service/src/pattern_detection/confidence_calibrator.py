"""
Pattern Confidence Calibration

Uses ML-based calibration to improve confidence score reliability.
Learns from user feedback on pattern success/failure.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import pickle
import os

# Scikit-learn imports for calibration
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class PatternConfidenceCalibrator:
    """
    Calibrates pattern confidence scores using user feedback.
    
    Uses isotonic regression to map raw confidence scores to
    calibrated probabilities that match actual accuracy.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize confidence calibrator.
        
        Args:
            model_path: Optional path to save/load calibrated model
        """
        self.model_path = model_path or "pattern_calibrator.pkl"
        self.scaler = StandardScaler()
        self.calibrator: Optional[CalibratedClassifierCV] = None
        self.is_fitted = False
        
        # Training data storage
        self.features_history: List[np.ndarray] = []
        self.labels_history: List[int] = []
        
        logger.info("PatternConfidenceCalibrator initialized")
    
    def extract_features(self, pattern: Dict) -> np.ndarray:
        """
        Extract features from pattern for calibration.
        
        Features include:
        - Base confidence score
        - Occurrence count
        - Time consistency
        - ML confidence (if available)
        - Pattern age
        - Cluster size (if available)
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Feature vector as numpy array
        """
        features = []
        
        # Base confidence (0-1)
        features.append(pattern.get('confidence', 0.5))
        
        # Occurrences (normalized)
        occurrences = pattern.get('occurrences', 0)
        features.append(min(occurrences / 30.0, 1.0))  # Max at 30 occurrences
        
        # Time consistency (if available)
        time_consistency = pattern.get('time_consistency', 0.5)
        features.append(time_consistency)
        
        # ML confidence (if available)
        ml_confidence = pattern.get('ml_confidence', 0.0)
        features.append(ml_confidence)
        
        # Pattern age (days since first seen)
        created_at = pattern.get('created_at', datetime.utcnow().isoformat())
        try:
            if isinstance(created_at, str):
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                created_dt = created_at
            
            age_days = (datetime.utcnow() - created_dt.replace(tzinfo=None)).days
            features.append(min(age_days / 90.0, 1.0))  # Max at 90 days
        except:
            features.append(0.0)
        
        # Cluster size (normalized)
        cluster_size = pattern.get('cluster_size', 1)
        features.append(min(cluster_size / 20.0, 1.0))  # Max at 20 patterns per cluster
        
        # Pattern type encoding (one-hot style for common types)
        pattern_type = pattern.get('pattern_type', 'unknown')
        type_map = {
            'time_of_day': 1.0,
            'co_occurrence': 0.9,
            'sequence': 0.8,
            'session': 0.7,
            'contextual': 0.6,
            'room_based': 0.5,
            'anomaly': 0.4,
        }
        features.append(type_map.get(pattern_type, 0.5))
        
        return np.array(features, dtype=np.float32)
    
    def add_feedback(
        self, 
        pattern: Dict, 
        feedback: bool,
        save_immediately: bool = False
    ):
        """
        Add user feedback for pattern calibration.
        
        Args:
            pattern: Pattern dictionary
            feedback: True if pattern was successful/approved, False otherwise
            save_immediately: If True, retrain and save model immediately
        """
        features = self.extract_features(pattern)
        label = 1 if feedback else 0
        
        self.features_history.append(features)
        self.labels_history.append(label)
        
        logger.debug(f"Added feedback: pattern={pattern.get('pattern_id')}, feedback={feedback}")
        
        if save_immediately:
            self.train()
            self.save()
    
    def train(self, min_samples: int = 10):
        """
        Train calibration model on accumulated feedback.
        
        Args:
            min_samples: Minimum number of samples required for training
        """
        if len(self.features_history) < min_samples:
            logger.warning(f"Insufficient training data: {len(self.features_history)} < {min_samples}")
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
                    X_scaled, y, test_size=0.2, random_state=42, stratify=y
                )
            else:
                X_train, y_train = X_scaled, y
                X_val, y_val = None, None
            
            # Train base classifier
            base_classifier = LogisticRegression(random_state=42, max_iter=1000)
            
            # Calibrate using isotonic regression (best for small datasets)
            self.calibrator = CalibratedClassifierCV(
                base_classifier,
                method='isotonic',
                cv=min(5, len(X_train) // 2) if len(X_train) >= 10 else 2
            )
            
            self.calibrator.fit(X_train, y_train)
            self.is_fitted = True
            
            # Evaluate on validation set if available
            if X_val is not None:
                val_score = self.calibrator.score(X_val, y_val)
                logger.info(f"Calibration model trained: {len(X_train)} samples, validation accuracy: {val_score:.2%}")
            else:
                train_score = self.calibrator.score(X_train, y_train)
                logger.info(f"Calibration model trained: {len(X_train)} samples, training accuracy: {train_score:.2%}")
                
        except Exception as e:
            logger.error(f"Failed to train calibration model: {e}", exc_info=True)
            self.is_fitted = False
    
    def calibrate_confidence(self, pattern: Dict) -> float:
        """
        Calibrate pattern confidence score.
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        if not self.is_fitted or self.calibrator is None:
            # Return original confidence if model not trained
            return pattern.get('confidence', 0.5)
        
        try:
            # Extract features
            features = self.extract_features(pattern)
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Predict calibrated probability
            calibrated_prob = self.calibrator.predict_proba(features_scaled)[0][1]
            
            # Blend with original confidence (weighted average)
            original_confidence = pattern.get('confidence', 0.5)
            
            # Use more weight on calibrated score if we have enough training data
            weight = min(len(self.features_history) / 50.0, 0.7)  # Max 70% weight on calibrated
            calibrated_confidence = (
                weight * calibrated_prob + 
                (1 - weight) * original_confidence
            )
            
            return float(np.clip(calibrated_confidence, 0.0, 1.0))
            
        except Exception as e:
            logger.warning(f"Calibration failed for pattern {pattern.get('pattern_id')}: {e}")
            return pattern.get('confidence', 0.5)
    
    def save(self, path: Optional[str] = None):
        """Save calibrator model to disk."""
        save_path = path or self.model_path
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            
            with open(save_path, 'wb') as f:
                pickle.dump({
                    'scaler': self.scaler,
                    'calibrator': self.calibrator,
                    'is_fitted': self.is_fitted,
                    'features_history': self.features_history,
                    'labels_history': self.labels_history
                }, f)
            
            logger.info(f"Calibrator model saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save calibrator model: {e}")
    
    def load(self, path: Optional[str] = None):
        """Load calibrator model from disk."""
        load_path = path or self.model_path
        
        if not os.path.exists(load_path):
            logger.warning(f"Calibrator model not found at {load_path}")
            return False
        
        try:
            with open(load_path, 'rb') as f:
                data = pickle.load(f)
            
            self.scaler = data.get('scaler', StandardScaler())
            self.calibrator = data.get('calibrator')
            self.is_fitted = data.get('is_fitted', False)
            self.features_history = data.get('features_history', [])
            self.labels_history = data.get('labels_history', [])
            
            logger.info(f"Calibrator model loaded from {load_path}: {len(self.features_history)} training samples")
            return True
        except Exception as e:
            logger.error(f"Failed to load calibrator model: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get calibration statistics."""
        return {
            'is_fitted': self.is_fitted,
            'training_samples': len(self.features_history),
            'positive_feedback': sum(self.labels_history) if self.labels_history else 0,
            'negative_feedback': len(self.labels_history) - sum(self.labels_history) if self.labels_history else 0,
            'model_path': self.model_path
        }

