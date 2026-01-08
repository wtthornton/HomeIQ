"""
Device Anomaly Detector using PyOD

Phase 5: Anomaly Detection Implementation
Goal: Detect unusual device behavior for security and maintenance.

Uses ensemble approach with Isolation Forest and ECOD for robust detection.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from pyod.models.iforest import IForest
from pyod.models.ecod import ECOD
from pyod.models.lof import LOF

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Result of anomaly detection for a device."""
    
    device_id: str
    device_name: str | None = None
    is_anomaly: bool = False
    anomaly_type: str = "behavior"  # behavior, energy, availability
    severity: str = "low"  # low, medium, high
    score: float = 0.0  # Anomaly score (0-1, higher = more anomalous)
    description: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    feature_contributions: dict[str, float] = field(default_factory=dict)
    raw_scores: dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "is_anomaly": self.is_anomaly,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "score": self.score,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
            "feature_contributions": self.feature_contributions,
        }


class DeviceAnomalyDetector:
    """
    Anomaly detection for smart home devices using PyOD.
    
    Uses an ensemble of algorithms for robust detection:
    - Isolation Forest: Good for multivariate data, identifies outliers
    - ECOD: Fast, unsupervised, empirical cumulative distribution
    - LOF: Local outlier factor for density-based detection
    
    Consensus voting reduces false positives.
    """
    
    # Feature names for different anomaly types
    BEHAVIOR_FEATURES = [
        "state_change_frequency",
        "time_since_last_change",
        "hour_of_day",
        "day_of_week",
        "change_duration_avg",
    ]
    
    ENERGY_FEATURES = [
        "power_consumption",
        "consumption_vs_baseline",
        "temperature_delta",
        "runtime_minutes",
        "cycle_count",
    ]
    
    AVAILABILITY_FEATURES = [
        "availability_ratio",
        "response_time_ms",
        "error_rate",
        "reconnect_count",
        "message_loss_rate",
    ]
    
    def __init__(
        self,
        contamination: float = 0.05,
        use_ensemble: bool = True,
        min_samples_train: int = 100,
    ):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of outliers (0.01-0.1)
            use_ensemble: Use ensemble voting (more robust, slower)
            min_samples_train: Minimum samples required for training
        """
        self.contamination = contamination
        self.use_ensemble = use_ensemble
        self.min_samples_train = min_samples_train
        
        # Initialize models
        self._init_models()
        
        # Track training state per device
        self.device_models: dict[str, dict] = {}
        self.is_fitted: dict[str, bool] = {}
        
        logger.info(
            f"DeviceAnomalyDetector initialized with contamination={contamination}, "
            f"ensemble={use_ensemble}"
        )
    
    def _init_models(self) -> dict[str, Any]:
        """Initialize PyOD models."""
        return {
            "iforest": IForest(
                contamination=self.contamination,
                n_estimators=100,
                max_samples="auto",
                random_state=42,
                n_jobs=-1,  # Use all CPUs
            ),
            "ecod": ECOD(
                contamination=self.contamination,
            ),
            "lof": LOF(
                contamination=self.contamination,
                n_neighbors=20,
                n_jobs=-1,
            ),
        }
    
    def fit(
        self,
        device_id: str,
        normal_patterns: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> bool:
        """
        Train on normal device behavior patterns.
        
        Args:
            device_id: Unique device identifier
            normal_patterns: Training data (n_samples, n_features)
            feature_names: Optional feature names for interpretability
            
        Returns:
            True if training successful, False otherwise
        """
        if len(normal_patterns) < self.min_samples_train:
            logger.warning(
                f"Insufficient training data for {device_id}: "
                f"{len(normal_patterns)} < {self.min_samples_train}"
            )
            return False
        
        try:
            models = self._init_models()
            
            # Train each model
            for name, model in models.items():
                logger.debug(f"Training {name} for device {device_id}")
                model.fit(normal_patterns)
            
            # Store trained models
            self.device_models[device_id] = {
                "models": models,
                "feature_names": feature_names or [f"feature_{i}" for i in range(normal_patterns.shape[1])],
                "training_samples": len(normal_patterns),
                "trained_at": datetime.utcnow(),
            }
            self.is_fitted[device_id] = True
            
            logger.info(
                f"Successfully trained anomaly detector for {device_id} "
                f"with {len(normal_patterns)} samples"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to train anomaly detector for {device_id}: {e}")
            return False
    
    def predict(
        self,
        device_id: str,
        new_data: np.ndarray,
        device_name: str | None = None,
        anomaly_type: str = "behavior",
    ) -> list[AnomalyResult]:
        """
        Detect anomalies in new data.
        
        Args:
            device_id: Device identifier
            new_data: Data to check (n_samples, n_features)
            device_name: Human-readable device name
            anomaly_type: Type of anomaly (behavior, energy, availability)
            
        Returns:
            List of AnomalyResult for each sample
        """
        if device_id not in self.device_models:
            logger.warning(f"No trained model for device {device_id}")
            return []
        
        device_info = self.device_models[device_id]
        models = device_info["models"]
        feature_names = device_info["feature_names"]
        
        results = []
        
        for i, sample in enumerate(new_data):
            sample_2d = sample.reshape(1, -1)
            
            # Get predictions from each model
            raw_scores = {}
            labels = {}
            
            for name, model in models.items():
                try:
                    labels[name] = model.predict(sample_2d)[0]
                    raw_scores[name] = float(model.decision_function(sample_2d)[0])
                except Exception as e:
                    logger.error(f"Error predicting with {name}: {e}")
                    labels[name] = 0
                    raw_scores[name] = 0.0
            
            # Ensemble voting (majority vote)
            if self.use_ensemble:
                is_anomaly = sum(labels.values()) >= 2  # At least 2 models agree
            else:
                is_anomaly = labels.get("iforest", 0) == 1
            
            # Calculate ensemble score (average of decision functions)
            if raw_scores:
                ensemble_score = np.mean(list(raw_scores.values()))
            else:
                # All models failed - use default score
                ensemble_score = 0.0
            
            # Normalize score to 0-1 range
            normalized_score = self._normalize_score(ensemble_score)
            
            # Determine severity based on score
            severity = self._score_to_severity(normalized_score)
            
            # Calculate feature contributions
            iforest_model = models.get("iforest")
            contributions = self._calculate_feature_contributions(
                sample, feature_names, iforest_model
            ) if iforest_model else {}
            
            # Generate description
            description = self._generate_description(
                device_name or device_id,
                anomaly_type,
                severity,
                contributions,
            )
            
            result = AnomalyResult(
                device_id=device_id,
                device_name=device_name,
                is_anomaly=is_anomaly,
                anomaly_type=anomaly_type,
                severity=severity,
                score=normalized_score,
                description=description,
                feature_contributions=contributions,
                raw_scores=raw_scores,
            )
            results.append(result)
        
        # Log anomalies
        anomalies = [r for r in results if r.is_anomaly]
        if anomalies:
            logger.info(
                f"Detected {len(anomalies)} anomalies for device {device_id}"
            )
        
        return results
    
    def _normalize_score(self, score: float) -> float:
        """Normalize anomaly score to 0-1 range using sigmoid."""
        # PyOD scores can be negative (normal) or positive (anomalous)
        # Use sigmoid to map to 0-1
        return 1 / (1 + np.exp(-score))
    
    def _score_to_severity(self, score: float) -> str:
        """Convert normalized score to severity level."""
        if score >= 0.85:
            return "high"
        elif score >= 0.70:
            return "medium"
        else:
            return "low"
    
    def _calculate_feature_contributions(
        self,
        sample: np.ndarray,
        feature_names: list[str],
        model: IForest | None,
    ) -> dict[str, float]:
        """
        Calculate feature contributions to anomaly score.
        
        Uses feature importance from Isolation Forest paths.
        """
        contributions = {}
        
        try:
            # Get feature importance based on deviation from mean
            # This is a simplified approach; more sophisticated methods exist
            sample_2d = sample.reshape(1, -1)
            
            # Calculate z-scores for each feature
            if hasattr(model, '_scaler'):
                z_scores = np.abs((sample - model._scaler.mean_) / model._scaler.scale_)
            else:
                z_scores = np.abs(sample)
            
            # Normalize contributions to sum to 1
            total = z_scores.sum() or 1.0
            
            for i, name in enumerate(feature_names):
                if i < len(z_scores):
                    contributions[name] = float(z_scores[i] / total)
                    
        except Exception as e:
            logger.debug(f"Could not calculate feature contributions: {e}")
            # Fallback: equal contributions
            if feature_names and len(feature_names) > 0:
                for name in feature_names:
                    contributions[name] = 1.0 / len(feature_names)
            else:
                logger.warning("Cannot calculate feature contributions: feature_names is empty")
        
        return contributions
    
    def _generate_description(
        self,
        device_name: str,
        anomaly_type: str,
        severity: str,
        contributions: dict[str, float],
    ) -> str:
        """Generate human-readable anomaly description."""
        # Find top contributing features
        top_features = sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        feature_str = ", ".join([f[0].replace("_", " ") for f in top_features])
        
        templates = {
            ("behavior", "high"): f"Critical behavioral anomaly detected - unusual {feature_str}",
            ("behavior", "medium"): f"Unusual activity pattern detected - {feature_str}",
            ("behavior", "low"): f"Minor behavioral deviation in {feature_str}",
            ("energy", "high"): f"Critical energy anomaly - abnormal {feature_str}",
            ("energy", "medium"): f"Higher than expected energy consumption in {feature_str}",
            ("energy", "low"): f"Slight energy deviation in {feature_str}",
            ("availability", "high"): f"Critical connectivity issue - {feature_str}",
            ("availability", "medium"): f"Device showing intermittent connectivity - {feature_str}",
            ("availability", "low"): f"Minor connectivity fluctuation in {feature_str}",
        }
        
        return templates.get(
            (anomaly_type, severity),
            f"Anomaly detected in {device_name}: {feature_str}"
        )
    
    def get_model_info(self, device_id: str) -> dict[str, Any] | None:
        """Get information about a trained model."""
        if device_id not in self.device_models:
            return None
        
        info = self.device_models[device_id]
        return {
            "device_id": device_id,
            "feature_names": info["feature_names"],
            "training_samples": info["training_samples"],
            "trained_at": info["trained_at"].isoformat(),
            "models": list(info["models"].keys()),
        }
    
    def list_trained_devices(self) -> list[str]:
        """List all devices with trained models."""
        return list(self.device_models.keys())


class AnomalyAlertManager:
    """
    Manages anomaly alerts and integrates with HomeIQ services.
    
    Provides:
    - Alert storage and retrieval
    - Alert filtering by severity
    - Integration with health dashboard
    """
    
    def __init__(self, max_alerts: int = 1000):
        """Initialize the alert manager."""
        self.alerts: list[AnomalyResult] = []
        self.max_alerts = max_alerts
        self.acknowledged_alerts: set[str] = set()
    
    def add_alert(self, alert: AnomalyResult) -> None:
        """Add a new alert, maintaining max size."""
        if alert.is_anomaly:
            self.alerts.append(alert)
            
            # Trim old alerts
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
    
    def get_alerts(
        self,
        min_severity: str = "low",
        anomaly_type: str | None = None,
        limit: int = 50,
        include_acknowledged: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get alerts with filtering.
        
        Args:
            min_severity: Minimum severity level (low, medium, high)
            anomaly_type: Filter by type (behavior, energy, availability)
            limit: Maximum alerts to return
            include_acknowledged: Include acknowledged alerts
            
        Returns:
            List of alert dictionaries
        """
        severity_order = {"low": 0, "medium": 1, "high": 2}
        min_level = severity_order.get(min_severity, 0)
        
        filtered = []
        for alert in reversed(self.alerts):  # Most recent first
            # Check severity
            if severity_order.get(alert.severity, 0) < min_level:
                continue
            
            # Check type
            if anomaly_type and alert.anomaly_type != anomaly_type:
                continue
            
            # Check acknowledged
            alert_key = f"{alert.device_id}_{alert.detected_at.isoformat()}"
            if not include_acknowledged and alert_key in self.acknowledged_alerts:
                continue
            
            filtered.append(alert.to_dict())
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def acknowledge_alert(self, device_id: str, timestamp: str) -> bool:
        """Acknowledge an alert."""
        alert_key = f"{device_id}_{timestamp}"
        self.acknowledged_alerts.add(alert_key)
        return True
    
    def clear_old_alerts(self, hours: int = 24) -> int:
        """Clear alerts older than specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        original_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.detected_at > cutoff]
        return original_count - len(self.alerts)
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        type_counts = {"behavior": 0, "energy": 0, "availability": 0}
        
        for alert in self.alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            type_counts[alert.anomaly_type] = type_counts.get(alert.anomaly_type, 0) + 1
        
        return {
            "total_alerts": len(self.alerts),
            "acknowledged": len(self.acknowledged_alerts),
            "by_severity": severity_counts,
            "by_type": type_counts,
        }
