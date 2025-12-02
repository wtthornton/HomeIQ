"""
Pattern Quality Model Trainer

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.2: Pattern Quality Model Training

Train RandomForest classifier for pattern quality prediction.
"""

import logging
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Pattern, Suggestion, UserFeedback
from services.pattern_quality.feature_extractor import PatternFeatureExtractor
from services.pattern_quality.quality_model import PatternQualityModel

logger = logging.getLogger(__name__)


class PatternQualityTrainer:
    """
    Train pattern quality model from user feedback.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize trainer with database session.
        
        Args:
            db_session: Async database session
        """
        self.db_session = db_session
        self.feature_extractor = PatternFeatureExtractor()
        self.model = PatternQualityModel()
    
    async def load_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Load training data from user feedback.
        
        Returns:
            Tuple of (features, labels)
            - features: numpy array (n_samples, n_features)
            - labels: numpy array (n_samples,) with 0=rejected, 1=approved
        """
        # Query patterns that have suggestions with feedback
        query = (
            select(Pattern, UserFeedback)
            .join(Suggestion, Pattern.id == Suggestion.pattern_id)
            .join(UserFeedback, Suggestion.id == UserFeedback.suggestion_id)
            .where(UserFeedback.action.in_(['approved', 'rejected']))
        )
        
        result = await self.db_session.execute(query)
        rows = result.all()
        
        if len(rows) == 0:
            logger.warning("No training data found (patterns with feedback)")
            return np.array([]), np.array([])
        
        logger.info(f"Loading training data from {len(rows)} pattern-feedback pairs")
        
        features_list = []
        labels = []
        
        for pattern, feedback in rows:
            try:
                # Extract features
                features = self.feature_extractor.extract_features(pattern)
                features_list.append(features)
                
                # Create label from feedback
                # approved=1, rejected=0
                if feedback.action == 'approved':
                    labels.append(1)
                elif feedback.action == 'rejected':
                    labels.append(0)
                else:
                    # Skip other actions (modified, etc.)
                    continue
            except Exception as e:
                logger.warning(f"Error processing pattern {pattern.id}: {e}")
                continue
        
        if len(features_list) == 0:
            logger.warning("No valid training samples after processing")
            return np.array([]), np.array([])
        
        # Convert to numpy arrays
        X = self.feature_extractor.to_numpy_array(features_list)
        y = np.array(labels)
        
        logger.info(f"Loaded {len(X)} training samples ({np.sum(y)} approved, {len(y) - np.sum(y)} rejected)")
        
        return X, y
    
    async def load_blueprint_data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Load blueprint corpus data for pre-training.
        
        Returns:
            Tuple of (features, labels)
            - features: numpy array (n_samples, n_features)
            - labels: numpy array (n_samples,) with 1=blueprint-validated
        """
        # TODO: Implement blueprint corpus loading (Epic AI-4)
        # For now, return empty arrays
        logger.info("Blueprint corpus pre-training not yet implemented (Epic AI-4)")
        return np.array([]), np.array([])
    
    async def train(self) -> dict[str, float]:
        """
        Train model on user feedback data.
        
        Returns:
            Training metrics dictionary
        """
        # Load training data
        X, y = await self.load_training_data()
        
        if len(X) == 0:
            raise ValueError("No training data available. Need patterns with user feedback.")
        
        if len(np.unique(y)) < 2:
            logger.warning("Only one class in training data. Model may not train properly.")
        
        # Train model
        metrics = self.model.train(X, y)
        
        logger.info(f"Model training complete: {metrics}")
        
        return metrics
    
    async def train_with_blueprint_pretraining(self) -> dict[str, float]:
        """
        Train model with blueprint corpus pre-training.
        
        Returns:
            Training metrics dictionary
        """
        # Step 1: Pre-train on blueprint corpus
        blueprint_features, blueprint_labels = await self.load_blueprint_data()
        
        if len(blueprint_features) > 0:
            logger.info(f"Pre-training on {len(blueprint_features)} blueprint patterns")
            self.model.train(blueprint_features, blueprint_labels, validation_split=0.2)
            logger.info("Blueprint pre-training complete")
        else:
            logger.info("Skipping blueprint pre-training (no blueprint data available)")
        
        # Step 2: Fine-tune on user feedback
        user_features, user_labels = await self.load_training_data()
        
        if len(user_features) > 0:
            logger.info(f"Fine-tuning on {len(user_features)} user feedback samples")
            # Combine with pre-trained model
            metrics = self.model.train(user_features, user_labels, validation_split=0.2)
        else:
            logger.warning("No user feedback data available")
            metrics = self.model.metrics if hasattr(self.model, 'metrics') else {}
        
        return metrics
    
    def save_model(self, model_path: str) -> None:
        """
        Save trained model to disk.
        
        Args:
            model_path: Path to save model file
        """
        from pathlib import Path
        path = Path(model_path)
        self.model.save(path)
        logger.info(f"Model saved to {model_path}")
    
    def get_model(self) -> PatternQualityModel:
        """
        Get the trained model.
        
        Returns:
            PatternQualityModel instance
        """
        return self.model

