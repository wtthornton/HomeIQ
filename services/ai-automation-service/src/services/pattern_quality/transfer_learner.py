"""
Transfer Learning from Blueprint Corpus

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.6: Transfer Learning from Blueprint Corpus

Pre-train pattern quality model on blueprint corpus, then fine-tune on user feedback.
"""

import logging
from typing import Any

import numpy as np

from .quality_model import PatternQualityModel
from .feature_extractor import PatternFeatureExtractor
from .features import PatternFeatures
# Epic AI-22 Story AI22.1: Automation miner integration removed
# from utils.miner_integration import MinerIntegration

logger = logging.getLogger(__name__)


def blueprint_to_pattern_features(blueprint: dict[str, Any]) -> PatternFeatures:
    """
    Convert blueprint to PatternFeatures.
    
    Args:
        blueprint: Blueprint metadata from automation-miner
    
    Returns:
        PatternFeatures extracted from blueprint
    """
    features = PatternFeatures()
    
    # Extract metadata
    metadata = blueprint.get('metadata', {})
    blueprint_metadata = metadata.get('_blueprint_metadata', {})
    blueprint_variables = metadata.get('_blueprint_variables', {})
    blueprint_devices = metadata.get('_blueprint_devices', [])
    
    # Device count features
    if isinstance(blueprint_devices, list):
        features.device_count_total = len(blueprint_devices)
        features.device_count_unique = len(set(blueprint_devices))
    else:
        features.device_count_total = 0
        features.device_count_unique = 0
    
    # Extract quality score (use as confidence)
    quality_score = blueprint.get('quality_score', 0.5)
    features.confidence_raw = quality_score
    features.confidence_calibrated = quality_score
    features.confidence_normalized = quality_score
    
    # Pattern type (blueprints are typically co-occurrence patterns)
    features.pattern_type_co_occurrence = 1.0
    
    # Metadata complexity
    features.metadata_complexity = len(metadata)
    
    # Check if blueprint has conditions/actions
    if blueprint_metadata:
        features.metadata_has_conditions = 1.0
        features.metadata_has_actions = 1.0
    
    # Blueprint variables complexity
    if blueprint_variables:
        features.metadata_complexity += len(blueprint_variables)
    
    # Occurrence features (blueprints are "proven" patterns)
    # High occurrence count indicates popular/validated blueprint
    views = blueprint.get('views', 0)
    features.occurrence_count_total = min(views, 1000)  # Cap at 1000
    features.occurrence_frequency = min(views / 365.0, 10.0)  # Normalize to daily frequency
    
    # Time span (blueprints are stable patterns)
    # Assume blueprints are "mature" (90+ days old)
    features.time_span_days = 90.0
    features.recency_days = 0.0  # Blueprints are current
    features.age_days = 90.0
    
    # Trend (blueprints are stable)
    features.occurrence_trend_direction = 0.0  # Stable
    features.occurrence_trend_strength = 0.5
    
    # Quality indicators
    features.is_deprecated = 0.0
    features.needs_review = 0.0
    features.calibrated = 1.0  # Blueprints are "calibrated" (community-validated)
    
    return features


class BlueprintTransferLearner:
    """
    Transfer learning from blueprint corpus.
    
    Pre-trains model on blueprints, then fine-tunes on user feedback.
    """
    
    def __init__(
        self,
        miner_integration=None,  # Epic AI-22 Story AI22.1: MinerIntegration removed
        feature_extractor: PatternFeatureExtractor | None = None
    ):
        """
        Initialize transfer learner.
        
        Args:
            miner_integration: REMOVED - Epic AI-22 Story AI22.1: Automation miner integration removed
            feature_extractor: Feature extractor for patterns (default: create new)
        """
        # Epic AI-22 Story AI22.1: Automation miner integration removed
        self.miner_integration = None
        self.feature_extractor = feature_extractor or PatternFeatureExtractor()
    
    async def load_blueprint_corpus(
        self,
        min_quality: float = 0.0,
        limit: int = 1000
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Load blueprint corpus and convert to training data.
        
        Args:
            min_quality: Minimum blueprint quality score
            limit: Maximum number of blueprints
        
        Returns:
            Tuple of (X, y) training data
            - X: Feature matrix (n_samples, n_features)
            - y: Labels (1 for high quality, 0 for low quality)
        """
        logger.info(f"Loading blueprint corpus (min_quality={min_quality}, limit={limit})")
        
        # Epic AI-22 Story AI22.1: Automation miner integration removed
        logger.warning("Automation miner integration removed, returning empty corpus")
        return np.array([]).reshape(0, PatternFeatures.feature_count()), np.array([])
        
        # Removed: Load blueprints from miner
        # if not await self.miner_integration.is_available():
        #     logger.warning("Automation miner not available, returning empty corpus")
        #     return np.array([]).reshape(0, PatternFeatures.feature_count()), np.array([])
        # blueprints = await self.miner_integration.search_blueprints(
        #     min_quality=min_quality,
        #     limit=limit
        # )
        
        if not blueprints:
            logger.warning(f"No blueprints found (min_quality={min_quality}, limit={limit})")
            return np.array([]).reshape(0, PatternFeatures.feature_count()), np.array([])
        
        logger.info(f"Loaded {len(blueprints)} blueprints")
        
        # Convert blueprints to features
        X_list = []
        y_list = []
        
        for blueprint in blueprints:
            try:
                # Convert blueprint to features
                features = blueprint_to_pattern_features(blueprint)
                
                # Convert to numpy array
                X_list.append(features.to_list())
                
                # Use quality score as label (threshold: >0.7 = high quality)
                quality_score = blueprint.get('quality_score', 0.5)
                label = 1 if quality_score > 0.7 else 0
                y_list.append(label)
                
            except Exception as e:
                logger.warning(f"Error converting blueprint to features: {e}")
                continue
        
        if not X_list:
            logger.warning("No blueprints successfully converted to features")
            return np.array([]).reshape(0, PatternFeatures.feature_count()), np.array([])
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        logger.info(
            f"Converted {len(X)} blueprints to training data "
            f"(high quality: {np.sum(y)}, low quality: {len(y) - np.sum(y)})"
        )
        
        return X, y
    
    async def pre_train(
        self,
        model: PatternQualityModel,
        min_quality: float = 0.0,
        limit: int = 1000
    ) -> dict[str, Any]:
        """
        Pre-train model on blueprint corpus.
        
        Args:
            model: Model to pre-train
            min_quality: Minimum blueprint quality score
            limit: Maximum number of blueprints
        
        Returns:
            Pre-training metrics (accuracy, precision, recall, f1, etc.)
        """
        logger.info(f"Pre-training model on blueprint corpus (min_quality={min_quality}, limit={limit})")
        
        # Load blueprint corpus
        X, y = await self.load_blueprint_corpus(min_quality=min_quality, limit=limit)
        
        if len(X) == 0:
            logger.warning("No blueprint data available for pre-training")
            return {
                'status': 'skipped',
                'reason': 'No blueprint data available',
                'samples': 0
            }
        
        # Train model on blueprints
        metrics = model.train(X, y)
        
        logger.info(
            f"✅ Pre-training complete: {len(X)} samples, "
            f"accuracy={metrics.get('accuracy', 0):.3f}"
        )
        
        return {
            'status': 'success',
            'samples': len(X),
            **metrics
        }
    
    async def fine_tune(
        self,
        model: PatternQualityModel,
        X_user: np.ndarray,
        y_user: np.ndarray
    ) -> dict[str, Any]:
        """
        Fine-tune pre-trained model on user feedback.
        
        Note: RandomForest doesn't support true fine-tuning (incremental learning).
        Instead, we combine blueprint data with user data and retrain.
        
        Args:
            model: Pre-trained model
            X_user: User feedback features
            y_user: User feedback labels
        
        Returns:
            Fine-tuning metrics
        """
        logger.info(f"Fine-tuning model on {len(X_user)} user feedback samples")
        
        if len(X_user) == 0:
            logger.warning("No user feedback data available for fine-tuning")
            return {
                'status': 'skipped',
                'reason': 'No user feedback data available',
                'samples': 0
            }
        
        # Load blueprint corpus for combined training
        X_blueprint, y_blueprint = await self.load_blueprint_corpus(limit=500)
        
        # Combine blueprint and user data
        if len(X_blueprint) > 0:
            X_combined = np.vstack([X_blueprint, X_user])
            y_combined = np.hstack([y_blueprint, y_user])
            
            logger.info(
                f"Combining {len(X_blueprint)} blueprint samples with {len(X_user)} user samples"
            )
        else:
            X_combined = X_user
            y_combined = y_user
        
        # Retrain model on combined data
        metrics = model.train(X_combined, y_combined)
        
        logger.info(
            f"✅ Fine-tuning complete: {len(X_combined)} total samples, "
            f"accuracy={metrics.get('accuracy', 0):.3f}"
        )
        
        return {
            'status': 'success',
            'blueprint_samples': len(X_blueprint),
            'user_samples': len(X_user),
            'total_samples': len(X_combined),
            **metrics
        }
    
    async def compare_models(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        pre_trained_model: PatternQualityModel,
        non_pre_trained_model: PatternQualityModel | None = None
    ) -> dict[str, Any]:
        """
        Compare pre-trained vs non-pre-trained models.
        
        Args:
            X_test: Test features
            y_test: Test labels
            pre_trained_model: Pre-trained model
            non_pre_trained_model: Non-pre-trained model (if None, create new)
        
        Returns:
            Comparison metrics
        """
        logger.info("Comparing pre-trained vs non-pre-trained models")
        
        # Evaluate pre-trained model
        pre_trained_metrics = pre_trained_model.evaluate(X_test, y_test)
        
        # Create and train non-pre-trained model if needed
        if non_pre_trained_model is None:
            non_pre_trained_model = PatternQualityModel(
                n_estimators=pre_trained_model.model.n_estimators,
                max_depth=pre_trained_model.model.max_depth,
                random_state=pre_trained_model.model.random_state
            )
            # Train on test data (for comparison, though normally would use separate training set)
            non_pre_trained_model.train(X_test, y_test)
        
        # Evaluate non-pre-trained model
        non_pre_trained_metrics = non_pre_trained_model.evaluate(X_test, y_test)
        
        # Calculate improvement
        accuracy_improvement = (
            pre_trained_metrics.get('accuracy', 0) -
            non_pre_trained_metrics.get('accuracy', 0)
        )
        
        f1_improvement = (
            pre_trained_metrics.get('f1', 0) -
            non_pre_trained_metrics.get('f1', 0)
        )
        
        comparison = {
            'pre_trained': pre_trained_metrics,
            'non_pre_trained': non_pre_trained_metrics,
            'improvement': {
                'accuracy': accuracy_improvement,
                'f1': f1_improvement,
                'accuracy_pct': (accuracy_improvement / non_pre_trained_metrics.get('accuracy', 1)) * 100,
                'f1_pct': (f1_improvement / non_pre_trained_metrics.get('f1', 1)) * 100,
            }
        }
        
        logger.info(
            f"Comparison: Pre-trained accuracy={pre_trained_metrics.get('accuracy', 0):.3f}, "
            f"Non-pre-trained accuracy={non_pre_trained_metrics.get('accuracy', 0):.3f}, "
            f"Improvement={accuracy_improvement:.3f}"
        )
        
        return comparison

