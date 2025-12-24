# Story DI-3.2: Device Health Scoring Algorithm

**Story ID:** DI-3.2  
**Epic:** DI-3 (Advanced Device Intelligence Features)  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 13  
**Complexity:** High  

---

## Story Description

Create a comprehensive device health scoring algorithm that analyzes multiple factors including response time, error rate, battery level, signal strength, and usage patterns to generate a 0-100 health score for each device. This story implements the core intelligence feature that will drive optimization recommendations and predictive analytics.

## User Story

**As a** system administrator  
**I want** a health score for each device that indicates its overall performance and reliability  
**So that** I can quickly identify devices that need attention or maintenance  

## Acceptance Criteria

### AC1: Health Score Algorithm
- [ ] Multi-factor health scoring algorithm (0-100 scale)
- [ ] Response time factor analysis
- [ ] Error rate factor analysis
- [ ] Battery level factor analysis
- [ ] Signal strength factor analysis
- [ ] Usage pattern factor analysis

### AC2: Health Score Calculation
- [ ] Weighted scoring algorithm
- [ ] Historical trend analysis
- [ ] Comparative analysis with similar devices
- [ ] Real-time score updates
- [ ] Score persistence and history

### AC3: Health Score API
- [ ] `GET /api/health/scores` - Get all device health scores
- [ ] `GET /api/health/scores/{device_id}` - Get specific device health score
- [ ] `GET /api/health/trends/{device_id}` - Get device health trends
- [ ] `GET /api/health/comparison` - Compare device health scores

### AC4: Health Score Monitoring
- [ ] Real-time health score updates
- [ ] Health score change notifications
- [ ] Health score threshold alerts
- [ ] Health score trend analysis
- [ ] Health score reporting

## Technical Requirements

### Health Scoring Algorithm
```python
# src/core/health_scorer.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics
import math

class DeviceHealthScorer:
    def __init__(self):
        self.weights = {
            "response_time": 0.25,
            "error_rate": 0.30,
            "battery_level": 0.20,
            "signal_strength": 0.15,
            "usage_pattern": 0.10
        }
        self.thresholds = {
            "response_time": {"excellent": 100, "good": 500, "fair": 1000, "poor": 2000},
            "error_rate": {"excellent": 0.01, "good": 0.05, "fair": 0.10, "poor": 0.20},
            "battery_level": {"excellent": 80, "good": 60, "fair": 40, "poor": 20},
            "signal_strength": {"excellent": -50, "good": -60, "fair": -70, "poor": -80},
            "usage_pattern": {"excellent": 0.8, "good": 0.6, "fair": 0.4, "poor": 0.2}
        }
    
    async def calculate_health_score(self, device_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive health score for device"""
        # Get historical metrics for trend analysis
        historical_metrics = await self._get_historical_metrics(device_id)
        
        # Calculate individual factor scores
        response_time_score = await self._calculate_response_time_score(metrics, historical_metrics)
        error_rate_score = await self._calculate_error_rate_score(metrics, historical_metrics)
        battery_score = await self._calculate_battery_score(metrics, historical_metrics)
        signal_score = await self._calculate_signal_score(metrics, historical_metrics)
        usage_score = await self._calculate_usage_score(metrics, historical_metrics)
        
        # Calculate weighted overall score
        overall_score = (
            response_time_score * self.weights["response_time"] +
            error_rate_score * self.weights["error_rate"] +
            battery_score * self.weights["battery_level"] +
            signal_score * self.weights["signal_strength"] +
            usage_score * self.weights["usage_pattern"]
        )
        
        # Apply trend adjustment
        trend_adjustment = await self._calculate_trend_adjustment(historical_metrics)
        adjusted_score = overall_score + trend_adjustment
        
        # Ensure score is within 0-100 range
        final_score = max(0, min(100, adjusted_score))
        
        return {
            "device_id": device_id,
            "overall_score": round(final_score, 1),
            "factor_scores": {
                "response_time": round(response_time_score, 1),
                "error_rate": round(error_rate_score, 1),
                "battery_level": round(battery_score, 1),
                "signal_strength": round(signal_score, 1),
                "usage_pattern": round(usage_score, 1)
            },
            "trend_adjustment": round(trend_adjustment, 1),
            "health_status": self._get_health_status(final_score),
            "recommendations": await self._generate_recommendations(device_id, metrics, final_score),
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    async def _calculate_response_time_score(self, metrics: Dict[str, Any], historical: List[Dict[str, Any]]) -> float:
        """Calculate response time score (0-100)"""
        current_response_time = metrics.get("response_time", 0)
        
        # Score based on current response time
        if current_response_time <= self.thresholds["response_time"]["excellent"]:
            base_score = 100
        elif current_response_time <= self.thresholds["response_time"]["good"]:
            base_score = 80
        elif current_response_time <= self.thresholds["response_time"]["fair"]:
            base_score = 60
        elif current_response_time <= self.thresholds["response_time"]["poor"]:
            base_score = 40
        else:
            base_score = 20
        
        # Apply trend analysis
        if historical:
            avg_historical = statistics.mean([m.get("response_time", 0) for m in historical[-10:]])
            if current_response_time < avg_historical * 0.9:  # 10% improvement
                base_score += 10
            elif current_response_time > avg_historical * 1.1:  # 10% degradation
                base_score -= 10
        
        return max(0, min(100, base_score))
    
    async def _calculate_error_rate_score(self, metrics: Dict[str, Any], historical: List[Dict[str, Any]]) -> float:
        """Calculate error rate score (0-100)"""
        current_error_rate = metrics.get("error_rate", 0)
        
        # Score based on current error rate
        if current_error_rate <= self.thresholds["error_rate"]["excellent"]:
            base_score = 100
        elif current_error_rate <= self.thresholds["error_rate"]["good"]:
            base_score = 80
        elif current_error_rate <= self.thresholds["error_rate"]["fair"]:
            base_score = 60
        elif current_error_rate <= self.thresholds["error_rate"]["poor"]:
            base_score = 40
        else:
            base_score = 20
        
        # Apply trend analysis
        if historical:
            avg_historical = statistics.mean([m.get("error_rate", 0) for m in historical[-10:]])
            if current_error_rate < avg_historical * 0.9:  # 10% improvement
                base_score += 10
            elif current_error_rate > avg_historical * 1.1:  # 10% degradation
                base_score -= 10
        
        return max(0, min(100, base_score))
    
    async def _calculate_battery_score(self, metrics: Dict[str, Any], historical: List[Dict[str, Any]]) -> float:
        """Calculate battery level score (0-100)"""
        current_battery = metrics.get("battery_level", 100)
        
        # Score based on current battery level
        if current_battery >= self.thresholds["battery_level"]["excellent"]:
            base_score = 100
        elif current_battery >= self.thresholds["battery_level"]["good"]:
            base_score = 80
        elif current_battery >= self.thresholds["battery_level"]["fair"]:
            base_score = 60
        elif current_battery >= self.thresholds["battery_level"]["poor"]:
            base_score = 40
        else:
            base_score = 20
        
        # Apply trend analysis for battery degradation
        if historical:
            avg_historical = statistics.mean([m.get("battery_level", 100) for m in historical[-10:]])
            if current_battery < avg_historical * 0.95:  # 5% degradation
                base_score -= 5
        
        return max(0, min(100, base_score))
    
    async def _calculate_signal_score(self, metrics: Dict[str, Any], historical: List[Dict[str, Any]]) -> float:
        """Calculate signal strength score (0-100)"""
        current_signal = metrics.get("signal_strength", -50)
        
        # Score based on current signal strength (dBm)
        if current_signal >= self.thresholds["signal_strength"]["excellent"]:
            base_score = 100
        elif current_signal >= self.thresholds["signal_strength"]["good"]:
            base_score = 80
        elif current_signal >= self.thresholds["signal_strength"]["fair"]:
            base_score = 60
        elif current_signal >= self.thresholds["signal_strength"]["poor"]:
            base_score = 40
        else:
            base_score = 20
        
        # Apply trend analysis
        if historical:
            avg_historical = statistics.mean([m.get("signal_strength", -50) for m in historical[-10:]])
            if current_signal > avg_historical + 5:  # 5dB improvement
                base_score += 10
            elif current_signal < avg_historical - 5:  # 5dB degradation
                base_score -= 10
        
        return max(0, min(100, base_score))
    
    async def _calculate_usage_score(self, metrics: Dict[str, Any], historical: List[Dict[str, Any]]) -> float:
        """Calculate usage pattern score (0-100)"""
        current_usage = metrics.get("usage_frequency", 0.5)
        
        # Score based on usage frequency (0-1 scale)
        if current_usage >= self.thresholds["usage_pattern"]["excellent"]:
            base_score = 100
        elif current_usage >= self.thresholds["usage_pattern"]["good"]:
            base_score = 80
        elif current_usage >= self.thresholds["usage_pattern"]["fair"]:
            base_score = 60
        elif current_usage >= self.thresholds["usage_pattern"]["poor"]:
            base_score = 40
        else:
            base_score = 20
        
        # Apply trend analysis
        if historical:
            avg_historical = statistics.mean([m.get("usage_frequency", 0.5) for m in historical[-10:]])
            if current_usage > avg_historical * 1.1:  # 10% increase
                base_score += 10
            elif current_usage < avg_historical * 0.9:  # 10% decrease
                base_score -= 10
        
        return max(0, min(100, base_score))
    
    async def _calculate_trend_adjustment(self, historical: List[Dict[str, Any]]) -> float:
        """Calculate trend adjustment based on historical data"""
        if len(historical) < 5:
            return 0
        
        # Calculate trend for last 5 data points
        recent_scores = [self._calculate_historical_score(m) for m in historical[-5:]]
        
        # Simple linear trend calculation
        if len(recent_scores) >= 2:
            trend = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
            return trend * 5  # Apply trend adjustment
        
        return 0
    
    def _get_health_status(self, score: float) -> str:
        """Get health status based on score"""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"
    
    async def _generate_recommendations(self, device_id: str, metrics: Dict[str, Any], score: float) -> List[str]:
        """Generate recommendations based on health score and metrics"""
        recommendations = []
        
        if score < 60:
            recommendations.append("Device requires immediate attention")
        
        if metrics.get("response_time", 0) > 1000:
            recommendations.append("Consider optimizing device response time")
        
        if metrics.get("error_rate", 0) > 0.1:
            recommendations.append("High error rate detected - check device connectivity")
        
        if metrics.get("battery_level", 100) < 20:
            recommendations.append("Low battery - consider replacing or charging")
        
        if metrics.get("signal_strength", -50) < -70:
            recommendations.append("Weak signal strength - consider repositioning device")
        
        return recommendations
```

### Health Score API
```python
# src/api/health_router.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..core.health_scorer import DeviceHealthScorer
from ..core.database import DeviceRepository

router = APIRouter(prefix="/api/health", tags=["Health"])

@router.get("/scores")
async def get_all_health_scores(
    skip: int = 0,
    limit: int = 100,
    min_score: int = 0,
    max_score: int = 100,
    health_status: str = None,
    repository: DeviceRepository = Depends(get_device_repository),
    health_scorer: DeviceHealthScorer = Depends(get_health_scorer)
):
    """Get all device health scores"""
    devices = await repository.get_devices(skip=skip, limit=limit)
    health_scores = []
    
    for device in devices:
        metrics = await repository.get_device_metrics(device.id)
        health_score = await health_scorer.calculate_health_score(device.id, metrics)
        
        # Apply filters
        if min_score <= health_score["overall_score"] <= max_score:
            if health_status is None or health_score["health_status"] == health_status:
                health_scores.append(health_score)
    
    return health_scores

@router.get("/scores/{device_id}")
async def get_device_health_score(
    device_id: str,
    repository: DeviceRepository = Depends(get_device_repository),
    health_scorer: DeviceHealthScorer = Depends(get_health_scorer)
):
    """Get specific device health score"""
    device = await repository.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    metrics = await repository.get_device_metrics(device_id)
    health_score = await health_scorer.calculate_health_score(device_id, metrics)
    
    return health_score

@router.get("/trends/{device_id}")
async def get_device_health_trends(
    device_id: str,
    days: int = 7,
    repository: DeviceRepository = Depends(get_device_repository)
):
    """Get device health trends over time"""
    device = await repository.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    trends = await repository.get_device_health_trends(device_id, days)
    return trends

@router.get("/comparison")
async def compare_device_health_scores(
    repository: DeviceRepository = Depends(get_device_repository),
    health_scorer: DeviceHealthScorer = Depends(get_health_scorer)
):
    """Compare device health scores"""
    devices = await repository.get_all_devices()
    health_scores = []
    
    for device in devices:
        metrics = await repository.get_device_metrics(device.id)
        health_score = await health_scorer.calculate_health_score(device.id, metrics)
        health_scores.append(health_score)
    
    # Calculate statistics
    scores = [hs["overall_score"] for hs in health_scores]
    avg_score = statistics.mean(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0
    
    return {
        "total_devices": len(health_scores),
        "average_score": round(avg_score, 1),
        "min_score": min_score,
        "max_score": max_score,
        "health_distribution": {
            "excellent": len([hs for hs in health_scores if hs["health_status"] == "excellent"]),
            "good": len([hs for hs in health_scores if hs["health_status"] == "good"]),
            "fair": len([hs for hs in health_scores if hs["health_status"] == "fair"]),
            "poor": len([hs for hs in health_scores if hs["health_status"] == "poor"]),
            "critical": len([hs for hs in health_scores if hs["health_status"] == "critical"])
        },
        "devices": health_scores
    }
```

## Implementation Tasks

### Task 1: Health Scoring Algorithm
- [ ] Implement multi-factor health scoring algorithm
- [ ] Add weighted scoring system
- [ ] Implement factor-specific scoring
- [ ] Add trend analysis
- [ ] Test scoring algorithm

### Task 2: Health Score Calculation
- [ ] Implement health score calculation
- [ ] Add historical trend analysis
- [ ] Implement comparative analysis
- [ ] Add score persistence
- [ ] Test score calculation

### Task 3: Health Score API
- [ ] Create health score endpoints
- [ ] Implement score querying
- [ ] Add trend analysis endpoints
- [ ] Implement comparison endpoints
- [ ] Test API endpoints

### Task 4: Health Score Monitoring
- [ ] Implement real-time score updates
- [ ] Add score change notifications
- [ ] Implement threshold alerts
- [ ] Add trend analysis
- [ ] Test monitoring features

### Task 5: Health Score Persistence
- [ ] Implement score storage
- [ ] Add score history tracking
- [ ] Implement score retrieval
- [ ] Add score archiving
- [ ] Test persistence

### Task 6: Testing & Validation
- [ ] Create health scoring tests
- [ ] Test score calculation accuracy
- [ ] Test API endpoints
- [ ] Test monitoring features
- [ ] Validate scoring algorithm

## Dependencies

- **Prerequisites**: Story DI-3.1 (Real-Time Device Monitoring) completed
- **External**: Device metrics data
- **Internal**: Device Intelligence Service, Redis, InfluxDB
- **Infrastructure**: Docker environment

## Definition of Done

- [ ] Health scoring algorithm operational
- [ ] Health score calculation working
- [ ] Health score API functional
- [ ] Health score monitoring operational
- [ ] Health score persistence working
- [ ] All tests passing
- [ ] Performance targets met
- [ ] Documentation updated

## Notes

This story implements the core health scoring algorithm that will drive all advanced device intelligence features. The algorithm should be designed for accuracy, performance, and maintainability with comprehensive testing and validation.

---

**Created**: January 24, 2025  
**Last Updated**: January 24, 2025  
**Author**: BMAD Product Manager  
**Reviewers**: System Architect, QA Lead
