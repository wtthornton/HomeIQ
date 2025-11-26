"""
AutoML Correlation Optimizer

Epic 37, Story 37.5: AutoML Optimizer Foundation
Uses Optuna for hyperparameter optimization of correlation analysis components.

Single-home NUC optimized:
- Memory: <10MB (study storage)
- Optimization: <5 minutes per trial
- Lightweight Optuna configuration (pruning, early stopping)
"""

import logging
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, asdict
import json
from datetime import datetime

import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler

from shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class HyperparameterConfig:
    """Hyperparameter configuration for correlation components."""
    
    # TabPFN hyperparameters
    tabpfn_threshold: float = 0.5
    tabpfn_ensemble_size: int = 4
    
    # Streaming tracker hyperparameters
    streaming_window_hours: int = 24
    streaming_cache_ttl_seconds: int = 300
    streaming_min_correlation: float = 0.3
    
    # Feature extractor weights (normalized 0.0-1.0)
    feature_weight_domain: float = 0.2
    feature_weight_spatial: float = 0.3
    feature_weight_temporal: float = 0.2
    feature_weight_usage: float = 0.15
    feature_weight_external: float = 0.15
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HyperparameterConfig':
        """Create from dictionary."""
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate hyperparameter ranges."""
        # TabPFN
        if not 0.0 <= self.tabpfn_threshold <= 1.0:
            return False
        if not 1 <= self.tabpfn_ensemble_size <= 16:
            return False
        
        # Streaming tracker
        if not 1 <= self.streaming_window_hours <= 168:  # Max 1 week
            return False
        if not 60 <= self.streaming_cache_ttl_seconds <= 3600:  # 1 min to 1 hour
            return False
        if not 0.0 <= self.streaming_min_correlation <= 1.0:
            return False
        
        # Feature weights (should sum to ~1.0, but allow flexibility)
        weights = [
            self.feature_weight_domain,
            self.feature_weight_spatial,
            self.feature_weight_temporal,
            self.feature_weight_usage,
            self.feature_weight_external
        ]
        if any(w < 0.0 or w > 1.0 for w in weights):
            return False
        
        return True


class AutoMLCorrelationOptimizer:
    """
    AutoML optimizer for correlation analysis hyperparameters.
    
    Uses Optuna for Bayesian optimization:
    - TPE (Tree-structured Parzen Estimator) sampler
    - Median pruner for early stopping
    - Multi-objective optimization (precision, recall, F1)
    
    Single-home NUC optimization:
    - Lightweight study storage (<10MB)
    - Fast trials (<5 minutes each)
    - Pruning to avoid wasted computation
    """
    
    def __init__(
        self,
        storage: Optional[str] = None,
        study_name: str = "correlation_optimization",
        n_trials: int = 50,
        timeout_seconds: Optional[int] = None
    ):
        """
        Initialize AutoML optimizer.
        
        Args:
            storage: Optional Optuna storage URL (None = in-memory)
            study_name: Study name for Optuna
            n_trials: Number of optimization trials (default: 50)
            timeout_seconds: Optional timeout for optimization (None = no timeout)
        """
        self.storage = storage
        self.study_name = study_name
        self.n_trials = n_trials
        self.timeout_seconds = timeout_seconds
        
        # Optuna study (created on first optimize call)
        self.study: Optional[optuna.Study] = None
        
        # Best hyperparameters found
        self.best_config: Optional[HyperparameterConfig] = None
        self.best_value: Optional[float] = None
        
        logger.info(
            "AutoMLCorrelationOptimizer initialized (study=%s, n_trials=%d)",
            study_name, n_trials
        )
    
    def create_study(
        self,
        direction: str = "maximize",
        load_if_exists: bool = True
    ) -> optuna.Study:
        """
        Create or load Optuna study.
        
        Args:
            direction: Optimization direction ("maximize" or "minimize")
            load_if_exists: Whether to load existing study if it exists
        
        Returns:
            Optuna study
        """
        sampler = TPESampler(seed=42)  # Reproducible
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        
        self.study = optuna.create_study(
            study_name=self.study_name,
            storage=self.storage,
            sampler=sampler,
            pruner=pruner,
            direction=direction,
            load_if_exists=load_if_exists
        )
        
        logger.info("Optuna study created/loaded: %s", self.study_name)
        
        return self.study
    
    def suggest_hyperparameters(self, trial: optuna.Trial) -> HyperparameterConfig:
        """
        Suggest hyperparameters for a trial.
        
        Args:
            trial: Optuna trial
        
        Returns:
            HyperparameterConfig with suggested values
        """
        # TabPFN hyperparameters
        tabpfn_threshold = trial.suggest_float(
            "tabpfn_threshold", 0.1, 0.9, step=0.05
        )
        tabpfn_ensemble_size = trial.suggest_int(
            "tabpfn_ensemble_size", 1, 8, step=1
        )
        
        # Streaming tracker hyperparameters
        streaming_window_hours = trial.suggest_int(
            "streaming_window_hours", 6, 168, step=6  # 6h to 1 week
        )
        streaming_cache_ttl_seconds = trial.suggest_int(
            "streaming_cache_ttl_seconds", 60, 1800, step=60  # 1 min to 30 min
        )
        streaming_min_correlation = trial.suggest_float(
            "streaming_min_correlation", 0.1, 0.7, step=0.05
        )
        
        # Feature weights (normalized)
        feature_weight_domain = trial.suggest_float(
            "feature_weight_domain", 0.05, 0.4, step=0.05
        )
        feature_weight_spatial = trial.suggest_float(
            "feature_weight_spatial", 0.1, 0.5, step=0.05
        )
        feature_weight_temporal = trial.suggest_float(
            "feature_weight_temporal", 0.05, 0.4, step=0.05
        )
        feature_weight_usage = trial.suggest_float(
            "feature_weight_usage", 0.05, 0.3, step=0.05
        )
        feature_weight_external = trial.suggest_float(
            "feature_weight_external", 0.05, 0.3, step=0.05
        )
        
        # Normalize feature weights to sum to 1.0
        total_weight = (
            feature_weight_domain +
            feature_weight_spatial +
            feature_weight_temporal +
            feature_weight_usage +
            feature_weight_external
        )
        if total_weight > 0:
            feature_weight_domain /= total_weight
            feature_weight_spatial /= total_weight
            feature_weight_temporal /= total_weight
            feature_weight_usage /= total_weight
            feature_weight_external /= total_weight
        
        config = HyperparameterConfig(
            tabpfn_threshold=tabpfn_threshold,
            tabpfn_ensemble_size=tabpfn_ensemble_size,
            streaming_window_hours=streaming_window_hours,
            streaming_cache_ttl_seconds=streaming_cache_ttl_seconds,
            streaming_min_correlation=streaming_min_correlation,
            feature_weight_domain=feature_weight_domain,
            feature_weight_spatial=feature_weight_spatial,
            feature_weight_temporal=feature_weight_temporal,
            feature_weight_usage=feature_weight_usage,
            feature_weight_external=feature_weight_external
        )
        
        return config
    
    def optimize(
        self,
        objective_func: Callable[[optuna.Trial, HyperparameterConfig], float],
        n_trials: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> HyperparameterConfig:
        """
        Run hyperparameter optimization.
        
        Args:
            objective_func: Function that takes (trial, config) and returns objective value
            n_trials: Number of trials (default: self.n_trials)
            timeout: Timeout in seconds (default: self.timeout_seconds)
        
        Returns:
            Best HyperparameterConfig found
        """
        if self.study is None:
            self.create_study()
        
        n_trials = n_trials or self.n_trials
        timeout = timeout or self.timeout_seconds
        
        logger.info("Starting hyperparameter optimization (%d trials)", n_trials)
        
        def objective(trial: optuna.Trial) -> float:
            """Optuna objective function."""
            config = self.suggest_hyperparameters(trial)
            
            if not config.validate():
                # Invalid config, return worst possible value
                return float('-inf') if self.study.direction == optuna.study.StudyDirection.MAXIMIZE else float('inf')
            
            try:
                # Call user-provided objective function
                value = objective_func(trial, config)
                return value
            except Exception as e:
                logger.warning("Trial failed: %s", e)
                # Return worst possible value on error
                return float('-inf') if self.study.direction == optuna.study.StudyDirection.MAXIMIZE else float('inf')
        
        # Run optimization
        self.study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True
        )
        
        # Get best hyperparameters
        if self.study.best_trial:
            best_params = self.study.best_trial.params
            self.best_config = HyperparameterConfig(
                tabpfn_threshold=best_params.get("tabpfn_threshold", 0.5),
                tabpfn_ensemble_size=best_params.get("tabpfn_ensemble_size", 4),
                streaming_window_hours=best_params.get("streaming_window_hours", 24),
                streaming_cache_ttl_seconds=best_params.get("streaming_cache_ttl_seconds", 300),
                streaming_min_correlation=best_params.get("streaming_min_correlation", 0.3),
                feature_weight_domain=best_params.get("feature_weight_domain", 0.2),
                feature_weight_spatial=best_params.get("feature_weight_spatial", 0.3),
                feature_weight_temporal=best_params.get("feature_weight_temporal", 0.2),
                feature_weight_usage=best_params.get("feature_weight_usage", 0.15),
                feature_weight_external=best_params.get("feature_weight_external", 0.15)
            )
            self.best_value = self.study.best_value
            
            logger.info(
                "Optimization complete: best_value=%.4f, n_trials=%d",
                self.best_value, len(self.study.trials)
            )
        else:
            logger.warning("No successful trials in optimization")
            self.best_config = HyperparameterConfig()  # Default config
        
        return self.best_config
    
    def get_best_config(self) -> Optional[HyperparameterConfig]:
        """Get best hyperparameter configuration found."""
        return self.best_config
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        Get optimization history.
        
        Returns:
            List of trial results
        """
        if self.study is None:
            return []
        
        history = []
        for trial in self.study.trials:
            history.append({
                "number": trial.number,
                "value": trial.value,
                "params": trial.params,
                "state": trial.state.name,
                "datetime": trial.datetime_start.isoformat() if trial.datetime_start else None
            })
        
        return history
    
    def save_config(self, filepath: str) -> None:
        """
        Save best configuration to file.
        
        Args:
            filepath: Path to save JSON file
        """
        if self.best_config is None:
            logger.warning("No best config to save")
            return
        
        data = {
            "config": self.best_config.to_dict(),
            "best_value": self.best_value,
            "study_name": self.study_name,
            "n_trials": len(self.study.trials) if self.study else 0,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Saved best config to %s", filepath)
    
    def load_config(self, filepath: str) -> HyperparameterConfig:
        """
        Load configuration from file.
        
        Args:
            filepath: Path to JSON file
        
        Returns:
            HyperparameterConfig
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config = HyperparameterConfig.from_dict(data["config"])
        self.best_config = config
        self.best_value = data.get("best_value")
        
        logger.info("Loaded config from %s (best_value=%.4f)", filepath, self.best_value or 0.0)
        
        return config
    
    def get_memory_usage_mb(self) -> float:
        """Get approximate memory usage in MB."""
        if self.study is None:
            return 0.1  # Minimal
        
        # Rough estimate: ~100KB per trial
        n_trials = len(self.study.trials)
        return n_trials * 0.0001  # 100KB per trial

