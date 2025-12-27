# Story DI-3.1: Real-Time Device Monitoring

**Story ID:** DI-3.1  
**Epic:** DI-3 (Advanced Device Intelligence Features)  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 5  
**Complexity:** Medium  

---

## Story Description

Add simple device health monitoring with periodic health checks and basic metrics collection. This story provides basic device monitoring without complex real-time features.

## User Story

**As a** system administrator  
**I want** basic device health monitoring  
**So that** I can see device status and detect obvious issues  

## Acceptance Criteria

### AC1: Basic Health Monitoring
- [ ] Periodic device health checks (every 5 minutes)
- [ ] Device online/offline status tracking
- [ ] Basic health score calculation
- [ ] Health status API endpoint

### AC2: Simple Metrics
- [ ] Device response time tracking
- [ ] Device error rate tracking
- [ ] Basic performance metrics storage

## Technical Requirements

### WebSocket Server
```python
# src/core/websocket_server.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_subscribers: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from device subscribers
        for device_id, subscribers in self.device_subscribers.items():
            if websocket in subscribers:
                subscribers.remove(websocket)
    
    async def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        """Subscribe to device updates"""
        if device_id not in self.device_subscribers:
            self.device_subscribers[device_id] = []
        self.device_subscribers[device_id].append(websocket)
    
    async def broadcast_device_update(self, device_id: str, update_data: Dict[str, Any]):
        """Broadcast device update to subscribers"""
        if device_id in self.device_subscribers:
            message = json.dumps({
                "type": "device_update",
                "device_id": device_id,
                "data": update_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            for websocket in self.device_subscribers[device_id]:
                try:
                    await websocket.send_text(message)
                except:
                    # Remove disconnected websockets
                    self.device_subscribers[device_id].remove(websocket)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        message_text = json.dumps(message)
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_text)
            except:
                self.active_connections.remove(websocket)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "subscribe_device":
                await manager.subscribe_to_device(websocket, message["device_id"])
            elif message["type"] == "unsubscribe_device":
                # Handle unsubscribe
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Device State Tracker
```python
# src/core/device_state_tracker.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

class DeviceStateTracker:
    def __init__(self):
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.device_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.anomaly_detector = AnomalyDetector()
    
    async def update_device_state(self, device_id: str, state_data: Dict[str, Any]):
        """Update device state and track metrics"""
        current_time = datetime.utcnow()
        
        # Update device state
        self.device_states[device_id] = {
            **state_data,
            "last_updated": current_time,
            "online": True
        }
        
        # Track metrics
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = []
        
        self.device_metrics[device_id].append({
            "timestamp": current_time,
            "state": state_data,
            "response_time": state_data.get("response_time"),
            "error_rate": state_data.get("error_rate"),
            "battery_level": state_data.get("battery_level"),
            "signal_strength": state_data.get("signal_strength")
        })
        
        # Keep only last 1000 metrics per device
        if len(self.device_metrics[device_id]) > 1000:
            self.device_metrics[device_id] = self.device_metrics[device_id][-1000:]
        
        # Check for anomalies
        await self._check_anomalies(device_id, state_data)
        
        # Broadcast update
        await self._broadcast_update(device_id, state_data)
    
    async def _check_anomalies(self, device_id: str, state_data: Dict[str, Any]):
        """Check for device anomalies"""
        if device_id in self.device_metrics:
            recent_metrics = self.device_metrics[device_id][-10:]  # Last 10 metrics
            
            # Check for performance degradation
            if len(recent_metrics) >= 5:
                avg_response_time = sum(m.get("response_time", 0) for m in recent_metrics) / len(recent_metrics)
                if avg_response_time > 1000:  # > 1 second
                    await self._trigger_anomaly_alert(device_id, "performance_degradation", {
                        "avg_response_time": avg_response_time
                    })
            
            # Check for error rate spike
            error_rate = state_data.get("error_rate", 0)
            if error_rate > 0.1:  # > 10% error rate
                await self._trigger_anomaly_alert(device_id, "error_rate_spike", {
                    "error_rate": error_rate
                })
            
            # Check for battery level
            battery_level = state_data.get("battery_level")
            if battery_level is not None and battery_level < 20:  # < 20% battery
                await self._trigger_anomaly_alert(device_id, "low_battery", {
                    "battery_level": battery_level
                })
    
    async def _trigger_anomaly_alert(self, device_id: str, anomaly_type: str, data: Dict[str, Any]):
        """Trigger anomaly alert"""
        alert = {
            "type": "anomaly_alert",
            "device_id": device_id,
            "anomaly_type": anomaly_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all subscribers
        await manager.broadcast_to_all(alert)
        
        # Log anomaly
        logger.warning(f"Device anomaly detected: {device_id} - {anomaly_type}")
```

### Performance Metrics Collector
```python
# src/core/performance_collector.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import statistics

class PerformanceCollector:
    def __init__(self):
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {}
        self.aggregated_metrics: Dict[str, Dict[str, Any]] = {}
    
    async def collect_device_metrics(self, device_id: str, metrics: Dict[str, Any]):
        """Collect device performance metrics"""
        current_time = datetime.utcnow()
        
        if device_id not in self.metrics_history:
            self.metrics_history[device_id] = []
        
        self.metrics_history[device_id].append({
            "timestamp": current_time,
            "metrics": metrics
        })
        
        # Keep only last 24 hours of metrics
        cutoff_time = current_time - timedelta(hours=24)
        self.metrics_history[device_id] = [
            m for m in self.metrics_history[device_id]
            if m["timestamp"] > cutoff_time
        ]
        
        # Update aggregated metrics
        await self._update_aggregated_metrics(device_id)
    
    async def _update_aggregated_metrics(self, device_id: str):
        """Update aggregated metrics for device"""
        if device_id not in self.metrics_history:
            return
        
        metrics_list = self.metrics_history[device_id]
        if not metrics_list:
            return
        
        # Calculate aggregated metrics
        response_times = [m["metrics"].get("response_time", 0) for m in metrics_list if m["metrics"].get("response_time")]
        error_rates = [m["metrics"].get("error_rate", 0) for m in metrics_list if m["metrics"].get("error_rate")]
        battery_levels = [m["metrics"].get("battery_level", 100) for m in metrics_list if m["metrics"].get("battery_level")]
        signal_strengths = [m["metrics"].get("signal_strength", 0) for m in metrics_list if m["metrics"].get("signal_strength")]
        
        self.aggregated_metrics[device_id] = {
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "avg_error_rate": statistics.mean(error_rates) if error_rates else 0,
            "avg_battery_level": statistics.mean(battery_levels) if battery_levels else 100,
            "avg_signal_strength": statistics.mean(signal_strengths) if signal_strengths else 0,
            "total_requests": len(metrics_list),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def get_device_performance_summary(self, device_id: str) -> Dict[str, Any]:
        """Get device performance summary"""
        return self.aggregated_metrics.get(device_id, {})
```

## Implementation Tasks

### Task 1: WebSocket Server Implementation
- [ ] Create WebSocket manager
- [ ] Implement connection handling
- [ ] Implement subscription management
- [ ] Add message broadcasting
- [ ] Test WebSocket functionality

### Task 2: Device State Tracking
- [ ] Implement device state tracker
- [ ] Add state update handling
- [ ] Implement metrics collection
- [ ] Add state persistence
- [ ] Test state tracking

### Task 3: Performance Metrics Collection
- [ ] Implement performance collector
- [ ] Add metrics aggregation
- [ ] Implement metrics storage
- [ ] Add metrics querying
- [ ] Test metrics collection

### Task 4: Anomaly Detection
- [ ] Implement anomaly detector
- [ ] Add anomaly detection algorithms
- [ ] Implement alerting system
- [ ] Add anomaly logging
- [ ] Test anomaly detection

### Task 5: Real-Time Updates
- [ ] Implement real-time update broadcasting
- [ ] Add update filtering
- [ ] Implement update batching
- [ ] Add update persistence
- [ ] Test real-time updates

### Task 6: Testing & Validation
- [ ] Create WebSocket tests
- [ ] Test device state tracking
- [ ] Test performance metrics
- [ ] Test anomaly detection
- [ ] Test real-time updates

## Dependencies

- **Prerequisites**: Epic DI-1 and DI-2 completed
- **External**: Home Assistant WebSocket API, Zigbee2MQTT bridge
- **Internal**: Device Intelligence Service, Redis, InfluxDB
- **Infrastructure**: Docker environment

## Definition of Done

- [ ] WebSocket server operational
- [ ] Device state tracking functional
- [ ] Performance metrics collection working
- [ ] Anomaly detection operational
- [ ] Real-time updates broadcasting
- [ ] All tests passing
- [ ] Performance targets met
- [ ] Documentation updated

## Notes

This story implements the real-time monitoring foundation that will be used by all advanced device intelligence features. The WebSocket server should be designed for high performance and reliability with proper connection management.

---

**Created**: January 24, 2025  
**Last Updated**: January 24, 2025  
**Author**: BMAD Product Manager  
**Reviewers**: System Architect, QA Lead
