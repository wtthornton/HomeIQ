"""
Production Home Type Classifier

Classify home type using pre-trained model.
Loads model at startup, uses for inference.
"""

import logging
from pathlib import Path
from typing import Any

from .home_type_classifier import FineTunedHomeTypeClassifier

logger = logging.getLogger(__name__)


class ProductionHomeTypeClassifier:
    """
    Classify home type using pre-trained model.
    
    Loads model at startup, uses for inference.
    """
    
    def __init__(self, model_path: str | Path):
        """
        Initialize production classifier.
        
        Args:
            model_path: Path to pre-trained model file
        """
        self.classifier = FineTunedHomeTypeClassifier()
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            logger.warning(f"Model file not found: {model_path}. Model will not be loaded.")
            self.is_loaded = False
        else:
            try:
                self.classifier.load(self.model_path)
                self.is_loaded = True
                logger.info(f"✅ Model loaded from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.is_loaded = False
    
    async def classify_home(
        self,
        home_profile: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Classify home type.
        
        Args:
            home_profile: Home profile from ProductionHomeTypeProfiler
        
        Returns:
            Classification result:
            {
                'home_type': str,
                'confidence': float,
                'method': 'ml_model',
                'features_used': list[str],
                'model_version': str
            }
        """
        if not self.is_loaded:
            return {
                'home_type': 'unknown',
                'confidence': 0.0,
                'method': 'not_loaded',
                'error': 'Model not loaded'
            }
        
        try:
            prediction = self.classifier.predict(home_profile)
            logger.info(f"Classified home type: {prediction['home_type']} (confidence: {prediction['confidence']:.3f})")
            return prediction
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                'home_type': 'unknown',
                'confidence': 0.0,
                'method': 'error',
                'error': str(e)
            }
    
    def get_model_info(self) -> dict[str, Any]:
        """
        Get model metadata.
        
        Returns:
            Model information dictionary
        """
        if not self.is_loaded:
            return {
                'is_loaded': False,
                'model_path': str(self.model_path)
            }
        
        return {
            'is_loaded': True,
            'model_path': str(self.model_path),
            'model_version': self.classifier.model_version,
            'training_date': self.classifier.training_date,
            'class_names': self.classifier.class_names,
            'feature_names': self.classifier.feature_names
        }

