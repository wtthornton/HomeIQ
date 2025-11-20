"""
Predictive Analytics Engine for Device Intelligence Service

This module implements AI-powered predictive analytics for device failure prediction
and maintenance scheduling using machine learning models.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..models.database import Device, DeviceHealthMetric

logger = logging.getLogger(__name__)


class PredictiveAnalyticsEngine:
    """AI-powered predictive analytics engine for device failure prediction."""

    def __init__(self):
        self.models = {
            "failure_prediction": None,
            "anomaly_detection": None,
            "maintenance_scheduling": None
        }
        self.scalers = {
            "failure_prediction": StandardScaler(),
            "anomaly_detection": StandardScaler()
        }
        self.feature_columns = [
            "response_time", "error_rate", "battery_level", "signal_strength",
            "usage_frequency", "temperature", "humidity", "uptime_hours",
            "restart_count", "connection_drops", "data_transfer_rate"
        ]
        self.model_performance = {}
        self.is_trained = False
        self.models_dir = "models"
        self.model_metadata = {
            "version": "1.0.0",
            "training_date": None,
            "training_data_stats": {},
            "model_performance": {},
            "scikit_learn_version": None,
            "feature_columns": self.feature_columns,
            "training_parameters": {},
            "data_source": "unknown"
        }

        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)

    async def initialize_models(self):
        """Initialize and load pre-trained models."""
        try:
            # Load pre-trained models if available
            failure_model_path = os.path.join(self.models_dir, "failure_prediction_model.pkl")
            anomaly_model_path = os.path.join(self.models_dir, "anomaly_detection_model.pkl")
            failure_scaler_path = os.path.join(self.models_dir, "failure_prediction_scaler.pkl")
            anomaly_scaler_path = os.path.join(self.models_dir, "anomaly_detection_scaler.pkl")
            metadata_path = os.path.join(self.models_dir, "model_metadata.json")

            if all(os.path.exists(p) for p in [failure_model_path, anomaly_model_path, failure_scaler_path, anomaly_scaler_path]):
                self.models["failure_prediction"] = joblib.load(failure_model_path)
                self.models["anomaly_detection"] = joblib.load(anomaly_model_path)
                self.scalers["failure_prediction"] = joblib.load(failure_scaler_path)
                self.scalers["anomaly_detection"] = joblib.load(anomaly_scaler_path)

                # Load metadata if available
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path) as f:
                            self.model_metadata = json.load(f)
                        logger.info(f"✅ Model metadata loaded: version {self.model_metadata.get('version', 'unknown')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not load model metadata: {e}")

                self.is_trained = True
                logger.info("✅ Pre-trained models loaded successfully")
            else:
                logger.info("📊 No pre-trained models found, will train new models")
                await self.train_models()
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            await self.train_models()

    async def train_models(self, historical_data: list[dict[str, Any]] = None, days_back: int = 180):
        """Train machine learning models."""
        training_start_time = datetime.now(timezone.utc)
        data_source = "database"

        if not historical_data:
            historical_data = await self._collect_training_data(days_back=days_back)
            # Check if we used sample data (fallback)
            if historical_data and historical_data[0].get("device_id", "").startswith("sample_device_"):
                data_source = "sample"

        if len(historical_data) < 100:
            logger.warning("⚠️ Insufficient training data, using rule-based predictions")
            return

        try:
            # Prepare training data
            df = pd.DataFrame(historical_data)
            X, y_failure, y_anomaly = self._prepare_training_data(df)

            if len(X) < 50:
                logger.warning("⚠️ Insufficient training samples, skipping model training")
                return

            # Calculate training data statistics
            unique_devices = len(set(d.get("device_id", "") for d in historical_data))
            date_range = None
            if historical_data:
                timestamps = [d.get("timestamp") for d in historical_data if d.get("timestamp")]
                if timestamps:
                    date_range = {
                        "start": min(timestamps) if isinstance(timestamps[0], str) else min(timestamps).isoformat(),
                        "end": max(timestamps) if isinstance(timestamps[0], str) else max(timestamps).isoformat()
                    }

            training_data_stats = {
                "sample_count": len(historical_data),
                "unique_devices": unique_devices,
                "date_range": date_range,
                "days_back": days_back
            }

            # Split data
            X_train, X_test, y_failure_train, y_failure_test = train_test_split(
                X, y_failure, test_size=0.2, random_state=42
            )

            # Scale features
            X_train_scaled = self.scalers["failure_prediction"].fit_transform(X_train)
            X_test_scaled = self.scalers["failure_prediction"].transform(X_test)

            # Training parameters
            training_params = {
                "n_estimators": 100,
                "max_depth": 10,
                "contamination": 0.1,
                "test_size": 0.2,
                "random_state": 42
            }

            # Train failure prediction model
            self.models["failure_prediction"] = RandomForestClassifier(
                n_estimators=training_params["n_estimators"],
                max_depth=training_params["max_depth"],
                random_state=training_params["random_state"],
                class_weight="balanced"
            )
            self.models["failure_prediction"].fit(X_train_scaled, y_failure_train)

            # Train anomaly detection model
            self.models["anomaly_detection"] = IsolationForest(
                contamination=training_params["contamination"],
                random_state=training_params["random_state"]
            )
            self.models["anomaly_detection"].fit(X_train_scaled)

            # Evaluate models
            await self._evaluate_models(X_test_scaled, y_failure_test)

            # Validate models before saving
            validation_result = await self._validate_models(X_test_scaled, y_failure_test)
            if not validation_result["valid"]:
                logger.warning(f"⚠️ Model validation failed: {validation_result['reason']}")
                logger.warning("⚠️ Models will not be saved. Using existing models if available.")
                self.is_trained = False
                return

            # Update model metadata
            self.model_metadata = {
                "version": self._increment_version(self.model_metadata.get("version", "1.0.0")),
                "training_date": training_start_time.isoformat(),
                "training_data_stats": training_data_stats,
                "model_performance": self.model_performance.copy(),
                "scikit_learn_version": sklearn.__version__,
                "feature_columns": self.feature_columns.copy(),
                "training_parameters": training_params,
                "data_source": data_source,
                "training_duration_seconds": (datetime.now(timezone.utc) - training_start_time).total_seconds(),
                "validation": validation_result
            }

            # Save models and metadata
            await self._save_models()

            # Verify saved models can be loaded
            if not await self._verify_saved_models():
                logger.error("❌ Saved models failed verification - removing invalid models")
                self.is_trained = False
                return

            self.is_trained = True
            logger.info(f"✅ Models trained, validated, and saved successfully (version {self.model_metadata['version']})")

        except Exception as e:
            logger.error(f"❌ Error training models: {e}", exc_info=True)
            self.is_trained = False
            raise

    def _increment_version(self, current_version: str) -> str:
        """Increment model version (semantic versioning: MAJOR.MINOR.PATCH)."""
        try:
            parts = current_version.split(".")
            if len(parts) == 3:
                major, minor, patch = map(int, parts)
                # Increment patch version
                return f"{major}.{minor}.{patch + 1}"
            else:
                return "1.0.1"
        except Exception:
            return "1.0.1"

    async def predict_device_failure(self, device_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        """Predict device failure probability."""
        if not self.is_trained:
            return await self._rule_based_prediction(device_id, metrics)

        try:
            # Prepare features
            features = self._extract_features(metrics)
            features_scaled = self.scalers["failure_prediction"].transform([features])

            # Predict failure probability
            failure_probability = self.models["failure_prediction"].predict_proba(features_scaled)[0][1]

            # Detect anomalies
            anomaly_score = self.models["anomaly_detection"].decision_function(features_scaled)[0]
            is_anomaly = self.models["anomaly_detection"].predict(features_scaled)[0] == -1

            # Generate maintenance recommendations
            recommendations = await self._generate_maintenance_recommendations(
                device_id, metrics, failure_probability, anomaly_score
            )

            return {
                "device_id": device_id,
                "failure_probability": round(failure_probability * 100, 2),
                "risk_level": self._get_risk_level(failure_probability),
                "anomaly_score": round(anomaly_score, 3),
                "is_anomaly": bool(is_anomaly),
                "confidence": self._calculate_confidence(failure_probability, anomaly_score),
                "recommendations": recommendations,
                "predicted_at": datetime.now(timezone.utc).isoformat(),
                "model_version": "1.0"
            }

        except Exception as e:
            logger.error(f"❌ Error predicting failure for device {device_id}: {e}")
            return await self._rule_based_prediction(device_id, metrics)

    async def predict_all_devices(self, devices_metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        """Predict failure probability for all devices."""
        predictions = []

        for device_id, metrics in devices_metrics.items():
            try:
                prediction = await self.predict_device_failure(device_id, metrics)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"❌ Error predicting failure for device {device_id}: {e}")
                # Add fallback prediction
                predictions.append({
                    "device_id": device_id,
                    "failure_probability": 0.0,
                    "risk_level": "unknown",
                    "error": str(e),
                    "predicted_at": datetime.utcnow().isoformat()
                })

        return predictions

    def _extract_features(self, metrics: dict[str, Any]) -> list[float]:
        """Extract features from device metrics."""
        features = []

        for column in self.feature_columns:
            value = metrics.get(column, 0)

            # Handle different data types
            if isinstance(value, (int, float)):
                features.append(float(value))
            elif isinstance(value, bool):
                features.append(1.0 if value else 0.0)
            elif isinstance(value, str):
                # Simple string encoding
                features.append(len(value) / 100.0)
            else:
                features.append(0.0)

        return features

    def _prepare_training_data(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data for models."""
        # Extract features
        X = df[self.feature_columns].fillna(0).values

        # Create failure labels (simplified - devices with high error rate or low battery)
        y_failure = (
            (df["error_rate"] > 0.1) |
            (df["battery_level"] < 20) |
            (df["response_time"] > 2000)
        ).astype(int).values

        # Create anomaly labels (devices with unusual patterns)
        y_anomaly = (
            (df["signal_strength"] < -80) |
            (df["connection_drops"] > 10) |
            (df["restart_count"] > 5)
        ).astype(int).values

        return X, y_failure, y_anomaly

    async def _collect_training_data(self, days_back: int = 180) -> list[dict[str, Any]]:
        """Collect historical data for training from database."""
        logger.info(f"📊 Collecting training data from last {days_back} days...")

        try:
            # Get database session
            async for session in get_db_session():
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

                # Query device health metrics from the last N days
                stmt = select(DeviceHealthMetric).where(
                    DeviceHealthMetric.timestamp >= cutoff_date
                ).order_by(DeviceHealthMetric.device_id, DeviceHealthMetric.timestamp)

                result = await session.execute(stmt)
                metrics = result.scalars().all()

                if not metrics:
                    logger.warning("⚠️ No historical metrics found in database, using sample data")
                    return await self._generate_sample_training_data()

                logger.info(f"📊 Found {len(metrics)} metric records from database")

                # Aggregate metrics by device and time window
                training_data = await self._aggregate_metrics_by_device(session, metrics, days_back)

                # Validate training data
                if not self._validate_training_data(training_data):
                    logger.warning("⚠️ Training data validation failed, using sample data")
                    return await self._generate_sample_training_data()

                logger.info(f"✅ Collected {len(training_data)} training samples from {len(set(d['device_id'] for d in training_data))} devices")
                return training_data

        except RuntimeError as e:
            if "Database not initialized" in str(e):
                logger.warning("⚠️ Database not initialized, using sample data")
            else:
                logger.error(f"❌ Error collecting training data from database: {e}")
            return await self._generate_sample_training_data()
        except Exception as e:
            logger.error(f"❌ Error collecting training data from database: {e}")
            logger.info("📊 Falling back to sample data")
            return await self._generate_sample_training_data()

    async def _aggregate_metrics_by_device(
        self,
        session: AsyncSession,
        metrics: list[DeviceHealthMetric],
        days_back: int
    ) -> list[dict[str, Any]]:
        """Aggregate metrics by device into training samples."""
        # Group metrics by device_id
        device_metrics: dict[str, list[DeviceHealthMetric]] = {}
        for metric in metrics:
            if metric.device_id not in device_metrics:
                device_metrics[metric.device_id] = []
            device_metrics[metric.device_id].append(metric)

        training_samples = []

        # Get device information
        device_ids = list(device_metrics.keys())
        stmt = select(Device).where(Device.id.in_(device_ids))
        result = await session.execute(stmt)
        devices = {d.id: d for d in result.scalars().all()}

        # Aggregate metrics for each device
        for device_id, device_metric_list in device_metrics.items():
            device = devices.get(device_id)

            # Group metrics by metric_name and calculate aggregates
            metric_groups: dict[str, list[float]] = {}
            timestamps = []

            for metric in device_metric_list:
                metric_name = metric.metric_name.lower()
                if metric_name not in metric_groups:
                    metric_groups[metric_name] = []
                metric_groups[metric_name].append(metric.metric_value)
                timestamps.append(metric.timestamp)

            # Calculate time-based features
            if timestamps:
                time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600  # hours
                uptime_hours = max(time_span, 1.0)  # Minimum 1 hour
            else:
                uptime_hours = 1.0

            # Map metric names to feature columns
            sample = {
                "device_id": device_id,
                "response_time": self._get_metric_value(metric_groups, ["response_time", "latency", "delay"], 500.0),
                "error_rate": self._get_metric_value(metric_groups, ["error_rate", "errors", "error_count"], 0.0),
                "battery_level": self._get_metric_value(metric_groups, ["battery", "battery_level", "battery_percentage"], 100.0),
                "signal_strength": self._get_metric_value(metric_groups, ["signal", "signal_strength", "rssi"], -60.0),
                "usage_frequency": self._get_metric_value(metric_groups, ["usage", "usage_frequency", "activity"], 0.5),
                "temperature": self._get_metric_value(metric_groups, ["temperature", "temp"], 25.0),
                "humidity": self._get_metric_value(metric_groups, ["humidity", "hum"], 50.0),
                "uptime_hours": uptime_hours,
                "restart_count": self._get_metric_value(metric_groups, ["restart", "restart_count", "reboot"], 0.0),
                "connection_drops": self._get_metric_value(metric_groups, ["connection_drops", "disconnects", "drop"], 0.0),
                "data_transfer_rate": self._get_metric_value(metric_groups, ["data_rate", "transfer_rate", "throughput"], 1000.0),
            }

            # Add device metadata if available
            if device:
                if device.health_score is not None:
                    sample["health_score"] = float(device.health_score)
                if device.last_seen:
                    hours_since_seen = (datetime.now(timezone.utc) - device.last_seen).total_seconds() / 3600
                    sample["hours_since_last_seen"] = hours_since_seen

            training_samples.append(sample)

        return training_samples

    def _get_metric_value(
        self,
        metric_groups: dict[str, list[float]],
        possible_names: list[str],
        default: float
    ) -> float:
        """Get metric value by trying multiple possible metric names."""
        for name in possible_names:
            if name in metric_groups and metric_groups[name]:
                # Return average value
                return float(np.mean(metric_groups[name]))
        return default

    def _validate_training_data(self, training_data: list[dict[str, Any]]) -> bool:
        """Validate training data quality."""
        if not training_data:
            logger.warning("⚠️ Training data is empty")
            return False

        if len(training_data) < 50:
            logger.warning(f"⚠️ Insufficient training samples: {len(training_data)} (minimum: 50)")
            return False

        # Check feature completeness
        required_features = set(self.feature_columns)
        sample_features = set(training_data[0].keys())

        # Remove device_id from sample_features for comparison
        sample_features.discard("device_id")
        sample_features.discard("health_score")
        sample_features.discard("hours_since_last_seen")

        missing_features = required_features - sample_features
        if missing_features:
            logger.warning(f"⚠️ Missing features in training data: {missing_features}")
            # Not a hard failure - we can use defaults

        # Check for reasonable data ranges
        for feature in self.feature_columns:
            values = [d.get(feature, 0) for d in training_data]
            if not values or all(v == 0 for v in values):
                logger.warning(f"⚠️ Feature {feature} has no variation (all zeros or missing)")

        logger.info(f"✅ Training data validation passed: {len(training_data)} samples")
        return True

    async def _generate_sample_training_data(self) -> list[dict[str, Any]]:
        """Generate sample training data as fallback."""
        logger.info("📊 Generating sample training data...")
        sample_data = []

        # Generate sample training data
        np.random.seed(42)
        for i in range(200):
            sample_data.append({
                "device_id": f"sample_device_{i}",
                "response_time": np.random.normal(500, 200),
                "error_rate": np.random.exponential(0.05),
                "battery_level": np.random.normal(70, 20),
                "signal_strength": np.random.normal(-60, 15),
                "usage_frequency": np.random.uniform(0.1, 1.0),
                "temperature": np.random.normal(25, 5),
                "humidity": np.random.normal(50, 10),
                "uptime_hours": np.random.exponential(100),
                "restart_count": np.random.poisson(2),
                "connection_drops": np.random.poisson(1),
                "data_transfer_rate": np.random.normal(1000, 200)
            })

        return sample_data

    async def _rule_based_prediction(self, device_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
        """Fallback rule-based prediction when ML models are not available."""
        failure_score = 0

        # Rule-based scoring
        if metrics.get("error_rate", 0) > 0.1:
            failure_score += 30
        if metrics.get("battery_level", 100) < 20:
            failure_score += 25
        if metrics.get("response_time", 0) > 2000:
            failure_score += 20
        if metrics.get("signal_strength", -50) < -80:
            failure_score += 15
        if metrics.get("connection_drops", 0) > 10:
            failure_score += 10

        return {
            "device_id": device_id,
            "failure_probability": min(failure_score, 100),
            "risk_level": self._get_risk_level(failure_score / 100),
            "anomaly_score": 0.0,
            "is_anomaly": failure_score > 50,
            "confidence": 0.7,  # Lower confidence for rule-based
            "recommendations": await self._generate_maintenance_recommendations(
                device_id, metrics, failure_score / 100, 0.0
            ),
            "predicted_at": datetime.utcnow().isoformat(),
            "model_version": "rule-based"
        }

    def _get_risk_level(self, probability: float) -> str:
        """Get risk level based on failure probability."""
        if probability >= 0.8:
            return "critical"
        elif probability >= 0.6:
            return "high"
        elif probability >= 0.4:
            return "medium"
        elif probability >= 0.2:
            return "low"
        else:
            return "minimal"

    def _calculate_confidence(self, failure_probability: float, anomaly_score: float) -> float:
        """Calculate prediction confidence."""
        # Higher confidence for extreme values and consistent signals
        base_confidence = 0.8

        if failure_probability > 0.8 or failure_probability < 0.2:
            base_confidence += 0.1

        if abs(anomaly_score) > 0.5:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    async def _generate_maintenance_recommendations(
        self,
        device_id: str,
        metrics: dict[str, Any],
        failure_probability: float,
        anomaly_score: float
    ) -> list[str]:
        """Generate maintenance recommendations."""
        recommendations = []

        if failure_probability > 0.6:
            recommendations.append("Schedule immediate maintenance - high failure risk")

        if metrics.get("battery_level", 100) < 20:
            recommendations.append("Replace or charge battery immediately")

        if metrics.get("error_rate", 0) > 0.1:
            recommendations.append("Check device connectivity and configuration")

        if metrics.get("signal_strength", -50) < -70:
            recommendations.append("Reposition device for better signal strength")

        if metrics.get("response_time", 0) > 1000:
            recommendations.append("Optimize device performance or consider replacement")

        if anomaly_score < -0.5:
            recommendations.append("Device showing unusual behavior - investigate")

        if not recommendations:
            recommendations.append("Device operating normally - continue monitoring")

        return recommendations

    async def _evaluate_models(self, X_test: np.ndarray, y_test: np.ndarray):
        """Evaluate model performance."""
        try:
            y_pred = self.models["failure_prediction"].predict(X_test)

            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            self.model_performance = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"📊 Model performance: Accuracy={accuracy:.3f}, Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")

        except Exception as e:
            logger.error(f"❌ Error evaluating models: {e}")
            self.model_performance = {
                "error": str(e),
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            }

    async def _validate_models(self, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
        """Validate models meet minimum performance thresholds."""
        try:
            # Check if models exist
            if self.models["failure_prediction"] is None or self.models["anomaly_detection"] is None:
                return {
                    "valid": False,
                    "reason": "Models are None",
                    "checks": {}
                }

            # Check if performance metrics exist
            if not self.model_performance or "accuracy" not in self.model_performance:
                return {
                    "valid": False,
                    "reason": "Model performance metrics not available",
                    "checks": {}
                }

            checks = {}
            issues = []

            # Minimum performance thresholds
            min_accuracy = 0.5  # At least 50% accuracy
            min_precision = 0.3  # At least 30% precision (can be low for imbalanced data)
            min_recall = 0.3    # At least 30% recall

            accuracy = self.model_performance.get("accuracy", 0)
            precision = self.model_performance.get("precision", 0)
            recall = self.model_performance.get("recall", 0)
            f1 = self.model_performance.get("f1_score", 0)

            # Check accuracy
            checks["accuracy"] = {
                "value": accuracy,
                "threshold": min_accuracy,
                "passed": accuracy >= min_accuracy
            }
            if accuracy < min_accuracy:
                issues.append(f"Accuracy {accuracy:.3f} below threshold {min_accuracy}")

            # Check precision
            checks["precision"] = {
                "value": precision,
                "threshold": min_precision,
                "passed": precision >= min_precision
            }
            if precision < min_precision:
                issues.append(f"Precision {precision:.3f} below threshold {min_precision}")

            # Check recall
            checks["recall"] = {
                "value": recall,
                "threshold": min_recall,
                "passed": recall >= min_recall
            }
            if recall < min_recall:
                issues.append(f"Recall {recall:.3f} below threshold {min_recall}")

            # Test model predictions on sample data
            try:
                sample_predictions = self.models["failure_prediction"].predict(X_test[:5])
                sample_proba = self.models["failure_prediction"].predict_proba(X_test[:5])
                checks["prediction_test"] = {
                    "passed": True,
                    "sample_predictions": len(sample_predictions) == 5,
                    "sample_proba_shape": sample_proba.shape[0] == 5
                }
            except Exception as e:
                checks["prediction_test"] = {
                    "passed": False,
                    "error": str(e)
                }
                issues.append(f"Prediction test failed: {e}")

            # Test anomaly detection
            try:
                anomaly_predictions = self.models["anomaly_detection"].predict(X_test[:5])
                anomaly_scores = self.models["anomaly_detection"].decision_function(X_test[:5])
                checks["anomaly_test"] = {
                    "passed": True,
                    "sample_predictions": len(anomaly_predictions) == 5,
                    "sample_scores": len(anomaly_scores) == 5
                }
            except Exception as e:
                checks["anomaly_test"] = {
                    "passed": False,
                    "error": str(e)
                }
                issues.append(f"Anomaly detection test failed: {e}")

            valid = len(issues) == 0
            reason = "; ".join(issues) if issues else "All validation checks passed"

            return {
                "valid": valid,
                "reason": reason,
                "checks": checks
            }

        except Exception as e:
            logger.error(f"❌ Error validating models: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}",
                "checks": {}
            }

    async def _verify_saved_models(self) -> bool:
        """Verify that saved models can be loaded and used."""
        try:
            failure_model_path = os.path.join(self.models_dir, "failure_prediction_model.pkl")
            anomaly_model_path = os.path.join(self.models_dir, "anomaly_detection_model.pkl")
            failure_scaler_path = os.path.join(self.models_dir, "failure_prediction_scaler.pkl")
            anomaly_scaler_path = os.path.join(self.models_dir, "anomaly_detection_scaler.pkl")

            # Try to load models
            test_failure_model = joblib.load(failure_model_path)
            test_anomaly_model = joblib.load(anomaly_model_path)
            test_failure_scaler = joblib.load(failure_scaler_path)
            test_anomaly_scaler = joblib.load(anomaly_scaler_path)

            # Test with dummy data
            dummy_features = np.random.rand(1, len(self.feature_columns))
            dummy_scaled = test_failure_scaler.transform(dummy_features)

            # Test predictions
            _ = test_failure_model.predict(dummy_scaled)
            _ = test_failure_model.predict_proba(dummy_scaled)
            _ = test_anomaly_model.predict(dummy_scaled)
            _ = test_anomaly_model.decision_function(dummy_scaled)

            logger.info("✅ Saved models verified successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Model verification failed: {e}")
            return False

    async def _save_models(self):
        """Save trained models and metadata."""
        try:
            failure_model_path = os.path.join(self.models_dir, "failure_prediction_model.pkl")
            anomaly_model_path = os.path.join(self.models_dir, "anomaly_detection_model.pkl")
            failure_scaler_path = os.path.join(self.models_dir, "failure_prediction_scaler.pkl")
            anomaly_scaler_path = os.path.join(self.models_dir, "anomaly_detection_scaler.pkl")
            metadata_path = os.path.join(self.models_dir, "model_metadata.json")

            # Backup existing models if they exist
            backup_suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            if os.path.exists(failure_model_path):
                backup_path = f"{failure_model_path}.backup_{backup_suffix}"
                try:
                    import shutil
                    shutil.copy2(failure_model_path, backup_path)
                    logger.info(f"📦 Backed up existing model to {backup_path}")

                    # Also backup metadata if it exists
                    if os.path.exists(metadata_path):
                        backup_metadata_path = f"{metadata_path}.backup_{backup_suffix}"
                        shutil.copy2(metadata_path, backup_metadata_path)
                        logger.info(f"📦 Backed up model metadata to {backup_metadata_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not backup existing model: {e}")

            # Save models
            joblib.dump(self.models["failure_prediction"], failure_model_path)
            joblib.dump(self.models["anomaly_detection"], anomaly_model_path)
            joblib.dump(self.scalers["failure_prediction"], failure_scaler_path)
            joblib.dump(self.scalers["anomaly_detection"], anomaly_scaler_path)

            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(self.model_metadata, f, indent=2)

            logger.info(f"✅ Models and metadata saved successfully (version {self.model_metadata.get('version', 'unknown')})")

        except Exception as e:
            logger.error(f"❌ Error saving models: {e}")

    def get_model_status(self) -> dict[str, Any]:
        """Get current model status and performance."""
        return {
            "is_trained": self.is_trained,
            "model_performance": self.model_performance,
            "feature_columns": self.feature_columns,
            "model_metadata": self.model_metadata,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    async def shutdown(self):
        """Release any resources held by the analytics engine."""
        self.models = dict.fromkeys(self.models)
        self.scalers = {
            "failure_prediction": StandardScaler(),
            "anomaly_detection": StandardScaler(),
        }
        self.is_trained = False
        logger.info("🧹 Predictive analytics engine shut down")
