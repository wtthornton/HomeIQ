"""
Incremental Pattern Quality Learner

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.5: Incremental Model Updates

Incremental learning for pattern quality model.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .quality_model import PatternQualityModel
from .model_trainer import PatternQualityTrainer
from .model_versioning import ModelVersionManager
from .features import PatternFeatures
from ...database.models import async_session

logger = logging.getLogger(__name__)


@dataclass
class FeedbackSample:
    """Single feedback sample for incremental learning."""
    pattern_id: int
    label: int  # 1 for approved, 0 for rejected
    features: PatternFeatures
    timestamp: datetime


class IncrementalPatternQualityLearner:
    """
    Incremental learner for pattern quality model.
    
    Collects feedback and updates model periodically.
    
    Since RandomForest doesn't support true incremental learning,
    we use a hybrid approach:
    1. Collect feedback samples
    2. When threshold reached, retrain with accumulated data
    3. Use model versioning for rollback
    """
    
    def __init__(
        self,
        model_path: Path | str,
        models_dir: Path | str | None = None,
        update_threshold: int = 100,
        min_update_samples: int = 10
    ):
        """
        Initialize incremental learner.
        
        Args:
            model_path: Path to current model file
            models_dir: Directory for model versions (default: models_dir from model_path)
            update_threshold: Number of new samples before update
            min_update_samples: Minimum samples required for update
        """
        self.model_path = Path(model_path)
        self.models_dir = Path(models_dir) if models_dir else self.model_path.parent / "versions"
        self.update_threshold = update_threshold
        self.min_update_samples = min_update_samples
        
        # Feedback buffer
        self.pending_samples: deque[FeedbackSample] = deque(maxlen=update_threshold * 2)
        
        # Version manager
        self.version_manager = ModelVersionManager(self.models_dir)
        
        # Performance tracking
        self.last_update_time: datetime | None = None
        self.update_count = 0
        self.total_update_time = 0.0
    
    async def collect_feedback(
        self,
        pattern_id: int,
        label: int,
        features: PatternFeatures
    ) -> None:
        """
        Collect feedback sample for incremental learning.
        
        Args:
            pattern_id: ID of the pattern
            label: Label (1=approved, 0=rejected)
            features: Pattern features
        """
        sample = FeedbackSample(
            pattern_id=pattern_id,
            label=label,
            features=features,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.pending_samples.append(sample)
        
        logger.debug(
            f"Collected feedback sample (pattern_id={pattern_id}, label={label}). "
            f"Pending: {len(self.pending_samples)}/{self.update_threshold}"
        )
    
    def should_update(self) -> bool:
        """
        Check if model should be updated.
        
        Returns:
            True if update threshold reached
        """
        return len(self.pending_samples) >= self.update_threshold
    
    async def update_model(
        self,
        force: bool = False
    ) -> dict[str, Any]:
        """
        Update model with accumulated feedback.
        
        Args:
            force: Force update even if threshold not reached
        
        Returns:
            Update metrics (accuracy, update_time, samples_processed, etc.)
        """
        if not force and not self.should_update():
            if len(self.pending_samples) < self.min_update_samples:
                return {
                    'status': 'skipped',
                    'reason': f'Insufficient samples: {len(self.pending_samples)} < {self.min_update_samples}',
                    'pending_samples': len(self.pending_samples)
                }
            # If we have enough samples but not at threshold, we can still update
            logger.info(f"Updating with {len(self.pending_samples)} samples (below threshold {self.update_threshold})")
        
        if len(self.pending_samples) < self.min_update_samples:
            return {
                'status': 'skipped',
                'reason': f'Insufficient samples: {len(self.pending_samples)} < {self.min_update_samples}',
                'pending_samples': len(self.pending_samples)
            }
        
        start_time = time.time()
        
        try:
            # Load current model
            current_model = PatternQualityModel.load(self.model_path)
            
            # Save current version before update
            current_version = self.version_manager.get_current_version()
            if current_version:
                # Already saved, just track
                pass
            else:
                # Save current model as version
                self.version_manager.save_version(
                    current_model,
                    metadata={'update_count': self.update_count}
                )
            
            # Prepare training data from pending samples
            X_new = np.array([sample.features.to_list() for sample in self.pending_samples])
            y_new = np.array([sample.label for sample in self.pending_samples])
            
            # Load existing training data from database
            async with async_session() as db:
                trainer = PatternQualityTrainer(db)
                X_existing, y_existing = await trainer.load_training_data()
            
            # Combine existing and new data
            if len(X_existing) > 0:
                X_combined = np.vstack([X_existing, X_new])
                y_combined = np.hstack([y_existing, y_new])
            else:
                X_combined = X_new
                y_combined = y_new
            
            # Retrain model with combined data
            logger.info(
                f"Retraining model with {len(X_combined)} samples "
                f"({len(X_existing)} existing + {len(X_new)} new)"
            )
            
            new_model = PatternQualityModel(
                n_estimators=current_model.model.n_estimators,
                max_depth=current_model.model.max_depth,
                random_state=current_model.model.random_state
            )
            
            metrics = new_model.train(X_combined, y_combined)
            
            # Save new model
            new_model.save(self.model_path)
            
            # Save as new version
            version = self.version_manager.save_version(
                new_model,
                metadata={
                    'update_count': self.update_count + 1,
                    'samples_added': len(X_new),
                    'total_samples': len(X_combined),
                    'previous_version': current_version
                }
            )
            
            # Clear pending samples
            samples_processed = len(self.pending_samples)
            self.pending_samples.clear()
            
            # Update performance tracking
            update_time = time.time() - start_time
            self.last_update_time = datetime.now(timezone.utc)
            self.update_count += 1
            self.total_update_time += update_time
            
            result = {
                'status': 'success',
                'version': version,
                'update_time': update_time,
                'samples_processed': samples_processed,
                'total_samples': len(X_combined),
                'metrics': metrics,
                'average_update_time': self.total_update_time / self.update_count
            }
            
            logger.info(
                f"✅ Model updated in {update_time:.2f}s "
                f"({samples_processed} samples, version {version})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating model: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'update_time': time.time() - start_time
            }
    
    def get_status(self) -> dict[str, Any]:
        """
        Get learner status.
        
        Returns:
            Status dictionary
        """
        return {
            'pending_samples': len(self.pending_samples),
            'update_threshold': self.update_threshold,
            'should_update': self.should_update(),
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'update_count': self.update_count,
            'average_update_time': (
                self.total_update_time / self.update_count
                if self.update_count > 0 else None
            ),
            'current_version': self.version_manager.get_current_version()
        }
    
    def rollback(self, version: str) -> bool:
        """
        Rollback to specific model version.
        
        Args:
            version: Version to rollback to
        
        Returns:
            True if successful
        """
        return self.version_manager.rollback(version, self.model_path)
    
    def list_versions(self) -> list[dict[str, Any]]:
        """
        List all model versions.
        
        Returns:
            List of version metadata
        """
        return self.version_manager.list_versions()

