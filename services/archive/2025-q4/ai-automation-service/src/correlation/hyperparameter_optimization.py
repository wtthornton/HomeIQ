"""
Hyperparameter Optimization Integration

Epic 37, Story 37.6: Hyperparameter Optimization
Integrates AutoML optimizer with correlation components to optimize hyperparameters.

Single-home NUC optimized:
- Evaluation: <30 seconds per trial
- Scheduled runs: Weekly optimization (background)
- Memory: <20MB during optimization
"""

import logging
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime, timedelta
import numpy as np

from .automl_optimizer import AutoMLCorrelationOptimizer, HyperparameterConfig
from .correlation_service import CorrelationService
from shared.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationHyperparameterOptimizer:
    """
    Hyperparameter optimizer for correlation analysis components.
    
    Integrates AutoML optimizer with CorrelationService to:
    - Optimize TabPFN threshold and ensemble size
    - Optimize streaming tracker window and cache TTL
    - Optimize feature extractor weights
    - Evaluate on validation data (ground truth correlations)
    
    Single-home NUC optimization:
    - Fast evaluation (<30s per trial)
    - Lightweight validation set (100-500 pairs)
    - Background optimization (scheduled weekly)
    """
    
    def __init__(
        self,
        correlation_service: CorrelationService,
        validation_data: Optional[List[Tuple[str, str, float]]] = None,
        optimizer: Optional[AutoMLCorrelationOptimizer] = None
    ):
        """
        Initialize hyperparameter optimizer.
        
        Args:
            correlation_service: CorrelationService instance to optimize
            validation_data: Optional list of (entity1_id, entity2_id, true_correlation) tuples
            optimizer: Optional AutoML optimizer (creates new one if None)
        """
        self.correlation_service = correlation_service
        self.validation_data = validation_data or []
        self.optimizer = optimizer or AutoMLCorrelationOptimizer(
            study_name="correlation_hyperparameters",
            n_trials=50
        )
        
        # Current best config
        self.current_config: Optional[HyperparameterConfig] = None
        
        logger.info(
            "CorrelationHyperparameterOptimizer initialized (validation_pairs=%d)",
            len(self.validation_data)
        )
    
    def set_validation_data(
        self,
        validation_data: List[Tuple[str, str, float]]
    ) -> None:
        """
        Set validation data for optimization.
        
        Args:
            validation_data: List of (entity1_id, entity2_id, true_correlation) tuples
        """
        self.validation_data = validation_data
        logger.info("Validation data updated (%d pairs)", len(validation_data))
    
    def apply_hyperparameters(self, config: HyperparameterConfig) -> None:
        """
        Apply hyperparameters to correlation service components.
        
        Args:
            config: HyperparameterConfig to apply
        """
        # Apply TabPFN hyperparameters
        if self.correlation_service.tabpfn_predictor:
            # Note: TabPFN ensemble size is set during training
            # Threshold is used in predict_likely_pairs calls
            # We'll store it for use in predictions
            if not hasattr(self.correlation_service, '_tabpfn_threshold'):
                self.correlation_service._tabpfn_threshold = config.tabpfn_threshold
            else:
                self.correlation_service._tabpfn_threshold = config.tabpfn_threshold
        
        # Apply streaming tracker hyperparameters
        if self.correlation_service.streaming_tracker:
            self.correlation_service.streaming_tracker.window_size_hours = config.streaming_window_hours
            self.correlation_service.streaming_tracker.cache_ttl_seconds = config.streaming_cache_ttl_seconds
            # Store optimized min_correlation for use in get_all_correlations
            self.correlation_service.streaming_tracker._optimized_min_correlation = config.streaming_min_correlation
        
        # Apply feature extractor weights (stored for use in feature extraction)
        if not hasattr(self.correlation_service, '_feature_weights'):
            self.correlation_service._feature_weights = {
                'domain': config.feature_weight_domain,
                'spatial': config.feature_weight_spatial,
                'temporal': config.feature_weight_temporal,
                'usage': config.feature_weight_usage,
                'external': config.feature_weight_external
            }
        else:
            self.correlation_service._feature_weights = {
                'domain': config.feature_weight_domain,
                'spatial': config.feature_weight_spatial,
                'temporal': config.feature_weight_temporal,
                'usage': config.feature_weight_usage,
                'external': config.feature_weight_external
            }
        
        self.current_config = config
        logger.debug("Applied hyperparameters: threshold=%.2f, window=%dh", 
                    config.tabpfn_threshold, config.streaming_window_hours)
    
    def evaluate_config(
        self,
        config: HyperparameterConfig,
        validation_data: Optional[List[Tuple[str, str, float]]] = None
    ) -> float:
        """
        Evaluate hyperparameter configuration on validation data.
        
        Args:
            config: HyperparameterConfig to evaluate
            validation_data: Optional validation data (uses self.validation_data if None)
        
        Returns:
            Objective value (higher is better for correlation accuracy)
        """
        validation_data = validation_data or self.validation_data
        
        if not validation_data:
            logger.warning("No validation data, returning default score")
            return 0.5  # Default score
        
        # Apply hyperparameters
        self.apply_hyperparameters(config)
        
        # Evaluate on validation set
        predictions = []
        true_correlations = []
        
        for entity1_id, entity2_id, true_corr in validation_data:
            # Get predicted correlation
            pred_corr = self.correlation_service.get_correlation(
                entity1_id, entity2_id, use_cache=False
            )
            
            if pred_corr is not None:
                predictions.append(pred_corr)
                true_correlations.append(true_corr)
        
        if not predictions:
            logger.warning("No valid predictions, returning default score")
            return 0.0
        
        # Calculate metrics
        predictions = np.array(predictions)
        true_correlations = np.array(true_correlations)
        
        # Mean squared error (lower is better, so we negate for maximization)
        mse = np.mean((predictions - true_correlations) ** 2)
        
        # Pearson correlation between predictions and true values (higher is better)
        if len(predictions) > 1 and np.std(predictions) > 0 and np.std(true_correlations) > 0:
            pearson_corr = np.corrcoef(predictions, true_correlations)[0, 1]
        else:
            pearson_corr = 0.0
        
        # Combined objective: maximize correlation, minimize MSE
        # Weighted combination: 70% correlation, 30% (1 - MSE)
        objective = 0.7 * pearson_corr + 0.3 * (1.0 - min(1.0, mse))
        
        logger.debug(
            "Config evaluation: mse=%.4f, pearson=%.4f, objective=%.4f",
            mse, pearson_corr, objective
        )
        
        return objective
    
    def optimize(
        self,
        n_trials: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> HyperparameterConfig:
        """
        Run hyperparameter optimization.
        
        Args:
            n_trials: Number of trials (default: optimizer default)
            timeout_seconds: Timeout in seconds (default: optimizer default)
        
        Returns:
            Best HyperparameterConfig found
        """
        if not self.validation_data:
            logger.warning("No validation data, cannot optimize")
            return HyperparameterConfig()  # Return default
        
        logger.info("Starting hyperparameter optimization (%d validation pairs)", 
                   len(self.validation_data))
        
        def objective(trial, config: HyperparameterConfig) -> float:
            """Optuna objective function."""
            return self.evaluate_config(config)
        
        # Run optimization
        best_config = self.optimizer.optimize(
            objective_func=objective,
            n_trials=n_trials,
            timeout=timeout_seconds
        )
        
        # Apply best config
        if best_config:
            self.apply_hyperparameters(best_config)
            logger.info("Optimization complete, best config applied")
        else:
            logger.warning("Optimization did not find better config")
        
        return best_config
    
    def get_best_config(self) -> Optional[HyperparameterConfig]:
        """Get current best hyperparameter configuration."""
        return self.current_config or self.optimizer.get_best_config()
    
    def save_best_config(self, filepath: str) -> None:
        """
        Save best configuration to file.
        
        Args:
            filepath: Path to save JSON file
        """
        if self.optimizer:
            self.optimizer.save_config(filepath)
        elif self.current_config:
            # Save manually if optimizer not used
            import json
            data = {
                "config": self.current_config.to_dict(),
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved config to %s", filepath)
    
    def load_config(self, filepath: str) -> HyperparameterConfig:
        """
        Load configuration from file and apply it.
        
        Args:
            filepath: Path to JSON file
        
        Returns:
            HyperparameterConfig
        """
        if self.optimizer:
            config = self.optimizer.load_config(filepath)
        else:
            # Load manually
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
            config = HyperparameterConfig.from_dict(data["config"])
        
        self.apply_hyperparameters(config)
        return config


def create_validation_data_from_correlations(
    correlation_service: CorrelationService,
    min_correlation: float = 0.3,
    max_pairs: int = 500
) -> List[Tuple[str, str, float]]:
    """
    Create validation data from existing correlations.
    
    Args:
        correlation_service: CorrelationService to get correlations from
        min_correlation: Minimum correlation to include
        max_pairs: Maximum number of pairs to include
    
    Returns:
        List of (entity1_id, entity2_id, correlation) tuples
    """
    # Get all correlations above threshold
    correlations = correlation_service.get_all_correlations(
        min_correlation=min_correlation,
        use_cache=True
    )
    
    # Convert to validation format
    validation_data = [
        (entity1_id, entity2_id, corr)
        for (entity1_id, entity2_id), corr in correlations.items()
    ]
    
    # Limit to max_pairs (random sample if needed)
    if len(validation_data) > max_pairs:
        import random
        validation_data = random.sample(validation_data, max_pairs)
    
    logger.info("Created validation data: %d pairs (min_corr=%.2f)", 
               len(validation_data), min_correlation)
    
    return validation_data

