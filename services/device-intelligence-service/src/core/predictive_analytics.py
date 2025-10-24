"""
Predictive Analytics Engine for Device Intelligence Service

This module implements AI-powered predictive analytics for device failure prediction
and maintenance scheduling using machine learning models.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib

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
            
            if all(os.path.exists(p) for p in [failure_model_path, anomaly_model_path, failure_scaler_path, anomaly_scaler_path]):
                self.models["failure_prediction"] = joblib.load(failure_model_path)
                self.models["anomaly_detection"] = joblib.load(anomaly_model_path)
                self.scalers["failure_prediction"] = joblib.load(failure_scaler_path)
                self.scalers["anomaly_detection"] = joblib.load(anomaly_scaler_path)
                self.is_trained = True
                logger.info("✅ Pre-trained models loaded successfully")
            else:
                logger.info("📊 No pre-trained models found, will train new models")
                await self.train_models()
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            await self.train_models()
    
    async def train_models(self, historical_data: List[Dict[str, Any]] = None):
        """Train machine learning models."""
        if not historical_data:
            historical_data = await self._collect_training_data()
        
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
            
            # Split data
            X_train, X_test, y_failure_train, y_failure_test = train_test_split(
                X, y_failure, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scalers["failure_prediction"].fit_transform(X_train)
            X_test_scaled = self.scalers["failure_prediction"].transform(X_test)
            
            # Train failure prediction model
            self.models["failure_prediction"] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight="balanced"
            )
            self.models["failure_prediction"].fit(X_train_scaled, y_failure_train)
            
            # Train anomaly detection model
            self.models["anomaly_detection"] = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            self.models["anomaly_detection"].fit(X_train_scaled)
            
            # Evaluate models
            await self._evaluate_models(X_test_scaled, y_failure_test)
            
            # Save models
            await self._save_models()
            
            self.is_trained = True
            logger.info("✅ Models trained and saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training models: {e}")
            self.is_trained = False
    
    async def predict_device_failure(self, device_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
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
                "predicted_at": datetime.utcnow().isoformat(),
                "model_version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"❌ Error predicting failure for device {device_id}: {e}")
            return await self._rule_based_prediction(device_id, metrics)
    
    async def predict_all_devices(self, devices_metrics: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def _extract_features(self, metrics: Dict[str, Any]) -> List[float]:
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
    
    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
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
    
    async def _collect_training_data(self) -> List[Dict[str, Any]]:
        """Collect historical data for training."""
        # This would typically query the database for historical metrics
        # For now, return sample data for demonstration
        sample_data = []
        
        # Generate sample training data
        np.random.seed(42)
        for i in range(200):
            sample_data.append({
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
    
    async def _rule_based_prediction(self, device_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
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
        metrics: Dict[str, Any], 
        failure_probability: float, 
        anomaly_score: float
    ) -> List[str]:
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
                "evaluated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📊 Model performance: Accuracy={accuracy:.3f}, Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error evaluating models: {e}")
            self.model_performance = {
                "error": str(e),
                "evaluated_at": datetime.utcnow().isoformat()
            }
    
    async def _save_models(self):
        """Save trained models."""
        try:
            failure_model_path = os.path.join(self.models_dir, "failure_prediction_model.pkl")
            anomaly_model_path = os.path.join(self.models_dir, "anomaly_detection_model.pkl")
            failure_scaler_path = os.path.join(self.models_dir, "failure_prediction_scaler.pkl")
            anomaly_scaler_path = os.path.join(self.models_dir, "anomaly_detection_scaler.pkl")
            
            joblib.dump(self.models["failure_prediction"], failure_model_path)
            joblib.dump(self.models["anomaly_detection"], anomaly_model_path)
            joblib.dump(self.scalers["failure_prediction"], failure_scaler_path)
            joblib.dump(self.scalers["anomaly_detection"], anomaly_scaler_path)
            
            logger.info("✅ Models saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error saving models: {e}")
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and performance."""
        return {
            "is_trained": self.is_trained,
            "model_performance": self.model_performance,
            "feature_columns": self.feature_columns,
            "last_updated": datetime.utcnow().isoformat()
        }
