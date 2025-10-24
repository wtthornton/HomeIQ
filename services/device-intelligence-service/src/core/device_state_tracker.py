"""
Device Intelligence Service - Device State Tracker

Tracks device states, metrics, and detects anomalies for real-time monitoring.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import deque
import statistics

from .websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class DeviceStateTracker:
    """Tracks device states and detects anomalies."""
    
    def __init__(self, max_history: int = 1000):
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.device_metrics: Dict[str, deque] = {}
        self.device_history: Dict[str, deque] = {}
        self.max_history = max_history
        self.anomaly_thresholds = {
            "response_time": 1000,  # ms
            "error_rate": 0.1,      # 10%
            "battery_level": 20,    # %
            "signal_strength": -80  # dBm
        }
    
    async def update_device_state(self, device_id: str, state_data: Dict[str, Any]):
        """Update device state and track metrics."""
        current_time = datetime.now(timezone.utc)
        
        # Update device state
        self.device_states[device_id] = {
            **state_data,
            "last_updated": current_time,
            "online": True
        }
        
        # Track metrics
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = deque(maxlen=self.max_history)
        
        metric_entry = {
            "timestamp": current_time,
            "response_time": state_data.get("response_time", 0),
            "error_rate": state_data.get("error_rate", 0),
            "battery_level": state_data.get("battery_level"),
            "signal_strength": state_data.get("signal_strength"),
            "cpu_usage": state_data.get("cpu_usage"),
            "memory_usage": state_data.get("memory_usage"),
            "temperature": state_data.get("temperature"),
            "uptime": state_data.get("uptime")
        }
        
        self.device_metrics[device_id].append(metric_entry)
        
        # Track device history
        if device_id not in self.device_history:
            self.device_history[device_id] = deque(maxlen=self.max_history)
        
        self.device_history[device_id].append({
            "timestamp": current_time,
            "state": state_data
        })
        
        # Check for anomalies
        await self._check_anomalies(device_id, state_data)
        
        # Broadcast update to WebSocket subscribers
        await websocket_manager.broadcast_device_update(device_id, {
            "state": state_data,
            "metrics": metric_entry,
            "health_score": await self._calculate_basic_health_score(device_id, state_data)
        })
        
        logger.debug(f"Updated device state for {device_id}")
    
    async def mark_device_offline(self, device_id: str):
        """Mark device as offline."""
        if device_id in self.device_states:
            self.device_states[device_id]["online"] = False
            self.device_states[device_id]["last_updated"] = datetime.now(timezone.utc)
            
            # Broadcast offline status
            await websocket_manager.broadcast_device_update(device_id, {
                "state": {"online": False},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Device {device_id} marked as offline")
    
    async def _check_anomalies(self, device_id: str, state_data: Dict[str, Any]):
        """Check for device anomalies."""
        anomalies_detected = []
        
        # Check response time
        response_time = state_data.get("response_time", 0)
        if response_time > self.anomaly_thresholds["response_time"]:
            anomalies_detected.append({
                "type": "high_response_time",
                "value": response_time,
                "threshold": self.anomaly_thresholds["response_time"],
                "severity": "warning"
            })
        
        # Check error rate
        error_rate = state_data.get("error_rate", 0)
        if error_rate > self.anomaly_thresholds["error_rate"]:
            anomalies_detected.append({
                "type": "high_error_rate",
                "value": error_rate,
                "threshold": self.anomaly_thresholds["error_rate"],
                "severity": "critical"
            })
        
        # Check battery level
        battery_level = state_data.get("battery_level")
        if battery_level is not None and battery_level < self.anomaly_thresholds["battery_level"]:
            anomalies_detected.append({
                "type": "low_battery",
                "value": battery_level,
                "threshold": self.anomaly_thresholds["battery_level"],
                "severity": "warning"
            })
        
        # Check signal strength
        signal_strength = state_data.get("signal_strength")
        if signal_strength is not None and signal_strength < self.anomaly_thresholds["signal_strength"]:
            anomalies_detected.append({
                "type": "weak_signal",
                "value": signal_strength,
                "threshold": self.anomaly_thresholds["signal_strength"],
                "severity": "warning"
            })
        
        # Check for performance degradation trends
        if device_id in self.device_metrics and len(self.device_metrics[device_id]) >= 5:
            await self._check_performance_trends(device_id, anomalies_detected)
        
        # Broadcast anomalies if any detected
        if anomalies_detected:
            await websocket_manager.broadcast_health_alert(device_id, "anomalies_detected", {
                "anomalies": anomalies_detected,
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.warning(f"Anomalies detected for device {device_id}: {len(anomalies_detected)} issues")
    
    async def _check_performance_trends(self, device_id: str, anomalies: List[Dict[str, Any]]):
        """Check for performance degradation trends."""
        metrics = list(self.device_metrics[device_id])
        if len(metrics) < 5:
            return
        
        # Check response time trend
        recent_response_times = [m["response_time"] for m in metrics[-5:]]
        if len(recent_response_times) >= 3:
            trend = self._calculate_trend(recent_response_times)
            if trend > 0.2:  # 20% increase
                anomalies.append({
                    "type": "response_time_degradation",
                    "trend": trend,
                    "severity": "warning"
                })
        
        # Check error rate trend
        recent_error_rates = [m["error_rate"] for m in metrics[-5:]]
        if len(recent_error_rates) >= 3:
            trend = self._calculate_trend(recent_error_rates)
            if trend > 0.1:  # 10% increase
                anomalies.append({
                    "type": "error_rate_increase",
                    "trend": trend,
                    "severity": "critical"
                })
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend percentage."""
        if len(values) < 2:
            return 0
        
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        if not first_half or not second_half:
            return 0
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        if avg_first == 0:
            return 0
        
        return (avg_second - avg_first) / avg_first
    
    async def _calculate_basic_health_score(self, device_id: str, state_data: Dict[str, Any]) -> float:
        """Calculate basic health score (0-100)."""
        score = 100.0
        
        # Deduct points for response time
        response_time = state_data.get("response_time", 0)
        if response_time > 1000:
            score -= min(30, (response_time - 1000) / 100)
        
        # Deduct points for error rate
        error_rate = state_data.get("error_rate", 0)
        score -= min(40, error_rate * 400)
        
        # Deduct points for battery level
        battery_level = state_data.get("battery_level")
        if battery_level is not None and battery_level < 20:
            score -= (20 - battery_level) * 2
        
        # Deduct points for signal strength
        signal_strength = state_data.get("signal_strength")
        if signal_strength is not None and signal_strength < -70:
            score -= min(20, abs(signal_strength + 70) * 0.5)
        
        return max(0, min(100, score))
    
    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current device state."""
        return self.device_states.get(device_id)
    
    def get_device_metrics(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get device metrics history."""
        if device_id not in self.device_metrics:
            return []
        
        metrics = list(self.device_metrics[device_id])
        return metrics[-limit:] if limit else metrics
    
    def get_device_history(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get device state history."""
        if device_id not in self.device_history:
            return []
        
        history = list(self.device_history[device_id])
        return history[-limit:] if limit else history
    
    def get_all_device_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all device states."""
        return self.device_states.copy()
    
    def get_online_devices(self) -> List[str]:
        """Get list of online device IDs."""
        return [
            device_id for device_id, state in self.device_states.items()
            if state.get("online", False)
        ]
    
    def get_offline_devices(self) -> List[str]:
        """Get list of offline device IDs."""
        return [
            device_id for device_id, state in self.device_states.items()
            if not state.get("online", False)
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get device state tracker statistics."""
        total_devices = len(self.device_states)
        online_devices = len(self.get_online_devices())
        offline_devices = len(self.get_offline_devices())
        
        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "total_metrics_points": sum(len(metrics) for metrics in self.device_metrics.values()),
            "anomaly_thresholds": self.anomaly_thresholds
        }


# Global device state tracker instance
device_state_tracker = DeviceStateTracker()
