"""
Anomaly Detection Module

Phase 5: Anomaly detection for smart home devices using PyOD.
Detects unusual device behavior for security and maintenance.
"""

from .detector import AnomalyResult, DeviceAnomalyDetector

__all__ = ["DeviceAnomalyDetector", "AnomalyResult"]
