"""
ML Model Metrics Tracking

Tracks model performance metrics over time for monitoring and alerting.
2025 improvement: Enhanced metrics tracking for new model types.
"""

import json
import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MLMetricsTracker:
    """
    Track ML model performance metrics over time.
    
    Metrics tracked:
    - Model accuracy, precision, recall, F1
    - Training time
    - Inference time
    - Model version
    - Data source
    """
    
    def __init__(self, metrics_dir: str = "models/metrics"):
        """
        Initialize metrics tracker.
        
        Args:
            metrics_dir: Directory to store metrics history
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        # Use bounded deque to prevent unbounded memory growth (HIGH-3)
        self.metrics_history: deque[dict[str, Any]] = deque(maxlen=10_000)
        
    def record_training(
        self,
        model_type: str,
        model_version: str,
        performance: dict[str, float],
        training_time: float,
        data_source: str,
        sample_count: int
    ):
        """
        Record training metrics.
        
        Args:
            model_type: Type of model (randomforest, lightgbm, tabpfn, incremental)
            model_version: Model version string
            performance: Performance metrics dict (accuracy, precision, recall, f1_score)
            training_time: Training time in seconds
            data_source: Data source (database, sample)
            sample_count: Number of training samples
        """
        metric_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "training",
            "model_type": model_type,
            "model_version": model_version,
            "performance": performance,
            "training_time_seconds": training_time,
            "data_source": data_source,
            "sample_count": sample_count
        }
        
        self.metrics_history.append(metric_entry)
        self._save_metrics()
        
        logger.info("Training metrics recorded: %s v%s, accuracy=%.3f", model_type, model_version, performance.get('accuracy', 0))
    
    def record_incremental_update(
        self,
        samples: int,
        update_time: float,
        accuracy: float
    ):
        """
        Record incremental update metrics.
        
        Args:
            samples: Number of new samples
            update_time: Update time in seconds
            accuracy: Current model accuracy
        """
        metric_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "incremental_update",
            "samples": samples,
            "update_time_seconds": update_time,
            "accuracy": accuracy
        }
        
        self.metrics_history.append(metric_entry)
        self._save_metrics()
        
        logger.info("Incremental update recorded: %d samples, %.3fs, accuracy=%.3f", samples, update_time, accuracy)
    
    def record_inference(
        self,
        inference_time: float,
        batch_size: int = 1
    ):
        """
        Record inference metrics.
        
        Args:
            inference_time: Inference time in seconds
            batch_size: Number of predictions made
        """
        metric_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "inference",
            "inference_time_seconds": inference_time,
            "batch_size": batch_size,
            "avg_time_per_prediction": inference_time / batch_size if batch_size > 0 else 0
        }
        
        self.metrics_history.append(metric_entry)
        self._save_metrics()
    
    def get_recent_metrics(self, hours: int = 24) -> list[dict[str, Any]]:
        """
        Get recent metrics within specified time window.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            List of metric entries
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        return [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')).timestamp() > cutoff
        ]
    
    def get_performance_trend(self) -> dict[str, Any]:
        """
        Get performance trend analysis.
        
        Returns:
            Dict with trend analysis
        """
        training_metrics = [m for m in self.metrics_history if m.get("event_type") == "training"]
        
        if len(training_metrics) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 training events for trend analysis"
            }
        
        # Get latest and previous training
        latest = training_metrics[-1]
        previous = training_metrics[-2]
        
        latest_perf = latest.get("performance", {})
        previous_perf = previous.get("performance", {})
        
        trends = {}
        for metric in ["accuracy", "precision", "recall", "f1_score"]:
            latest_val = latest_perf.get(metric, 0)
            previous_val = previous_perf.get(metric, 0)
            if previous_val > 0:
                change = latest_val - previous_val
                percent_change = (change / previous_val) * 100
                trends[metric] = {
                    "current": latest_val,
                    "previous": previous_val,
                    "change": change,
                    "percent_change": percent_change,
                    "direction": "improving" if change > 0 else "degrading" if change < 0 else "stable"
                }
        
        return {
            "status": "ok",
            "trends": trends,
            "latest_training": latest.get("timestamp"),
            "previous_training": previous.get("timestamp")
        }
    
    def check_accuracy_degradation(self, threshold: float = 0.05) -> dict[str, Any]:
        """
        Check if accuracy has degraded significantly.
        
        Args:
            threshold: Maximum acceptable accuracy drop (default: 5%)
        
        Returns:
            Dict with degradation status
        """
        training_metrics = [m for m in self.metrics_history if m.get("event_type") == "training"]
        
        if len(training_metrics) < 2:
            return {
                "degraded": False,
                "message": "Insufficient data for degradation check"
            }
        
        latest = training_metrics[-1]
        previous = training_metrics[-2]
        
        latest_acc = latest.get("performance", {}).get("accuracy", 0)
        previous_acc = previous.get("performance", {}).get("accuracy", 0)
        
        if previous_acc == 0:
            return {
                "degraded": False,
                "message": "Cannot compare - previous accuracy is 0"
            }
        
        accuracy_drop = previous_acc - latest_acc
        percent_drop = (accuracy_drop / previous_acc) * 100
        
        degraded = accuracy_drop > threshold
        
        return {
            "degraded": degraded,
            "accuracy_drop": accuracy_drop,
            "percent_drop": percent_drop,
            "latest_accuracy": latest_acc,
            "previous_accuracy": previous_acc,
            "threshold": threshold,
            "message": f"Accuracy dropped by {percent_drop:.2f}%" if degraded else "Accuracy within acceptable range"
        }
    
    def _save_metrics(self):
        """Save metrics history to file."""
        try:
            metrics_file = self.metrics_dir / "metrics_history.json"
            with open(metrics_file, 'w') as f:
                json.dump(list(self.metrics_history), f, indent=2)
        except Exception as e:
            logger.warning("Could not save metrics: %s", e)

    def load_metrics(self):
        """Load metrics history from file."""
        try:
            metrics_file = self.metrics_dir / "metrics_history.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    loaded = json.load(f)
                self.metrics_history = deque(loaded, maxlen=10_000)
                logger.info("Loaded %d metric entries", len(self.metrics_history))
        except Exception as e:
            logger.warning("Could not load metrics: %s", e)
            self.metrics_history = deque(maxlen=10_000)

