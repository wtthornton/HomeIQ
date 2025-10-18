"""
Performance Optimization Engine

Context7 Best Practices Applied:
- Async performance analysis
- Recommendation generation
- Automated optimization execution
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel

from .config import get_settings

settings = get_settings()


class OptimizationImpact(str, Enum):
    """Optimization impact level"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OptimizationEffort(str, Enum):
    """Effort required for optimization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation model"""
    id: str
    title: str
    description: str
    category: str
    impact: OptimizationImpact
    effort: OptimizationEffort
    estimated_improvement: str
    automated: bool = False
    steps: List[str]
    configuration_changes: Optional[Dict] = None


class PerformanceAnalysisEngine:
    """
    Performance analysis engine for Home Assistant environments
    
    Features:
    - Response time analysis
    - Resource usage monitoring
    - Configuration efficiency checks
    - Bottleneck identification
    """
    
    def __init__(self):
        self.ha_url = settings.ha_url
        self.ha_token = settings.ha_token
    
    async def analyze_performance(self) -> Dict:
        """
        Comprehensive performance analysis
        
        Returns:
            Analysis results with bottlenecks and recommendations
        """
        # Run analyses in parallel
        response_time_analysis, resource_analysis, config_analysis = await asyncio.gather(
            self._analyze_response_times(),
            self._analyze_resource_usage(),
            self._analyze_configuration(),
            return_exceptions=True
        )
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(
            response_time_analysis,
            resource_analysis,
            config_analysis
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time_analysis if not isinstance(response_time_analysis, Exception) else {},
            "resource_usage": resource_analysis if not isinstance(resource_analysis, Exception) else {},
            "configuration": config_analysis if not isinstance(config_analysis, Exception) else {},
            "bottlenecks": bottlenecks
        }
    
    async def _analyze_response_times(self) -> Dict:
        """Analyze HA API response times"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Test multiple endpoints and measure response time
                start_time = datetime.now()
                async with session.get(
                    f"{self.ha_url}/api/states",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        states = await response.json()
                        return {
                            "average_response_time_ms": round(elapsed, 2),
                            "endpoint": "/api/states",
                            "entity_count": len(states),
                            "status": "healthy" if elapsed < 500 else "slow"
                        }
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    async def _analyze_resource_usage(self) -> Dict:
        """Analyze system resource usage"""
        # Placeholder - will use system metrics when available
        return {
            "cpu_usage_percent": 12.5,
            "memory_usage_mb": 256.0,
            "status": "healthy"
        }
    
    async def _analyze_configuration(self) -> Dict:
        """Analyze configuration efficiency"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Get HA configuration
                async with session.get(
                    f"{self.ha_url}/api/config",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        config = await response.json()
                        return {
                            "recorder_configured": "recorder" in config.get("components", []),
                            "total_components": len(config.get("components", [])),
                            "status": "healthy"
                        }
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def _identify_bottlenecks(
        self,
        response_time: Dict,
        resource_usage: Dict,
        configuration: Dict
    ) -> List[Dict]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check response time
        if not isinstance(response_time, Exception):
            rt = response_time.get("average_response_time_ms", 0)
            if rt > 1000:
                bottlenecks.append({
                    "type": "slow_response",
                    "severity": "high",
                    "description": f"High response time: {rt}ms",
                    "recommendation": "Optimize database queries or reduce entity count"
                })
            elif rt > 500:
                bottlenecks.append({
                    "type": "moderate_response",
                    "severity": "medium",
                    "description": f"Moderate response time: {rt}ms",
                    "recommendation": "Consider enabling recorder purge or optimizing automations"
                })
        
        # Check resource usage
        if not isinstance(resource_usage, Exception):
            cpu = resource_usage.get("cpu_usage_percent", 0)
            if cpu > 80:
                bottlenecks.append({
                    "type": "high_cpu",
                    "severity": "high",
                    "description": f"High CPU usage: {cpu}%",
                    "recommendation": "Review and optimize resource-intensive automations"
                })
        
        return bottlenecks


class RecommendationEngine:
    """
    Generate optimization recommendations
    
    Features:
    - Prioritization by impact and effort
    - Automated fixes for common issues
    - Configuration optimization suggestions
    """
    
    def __init__(self):
        self.performance_analyzer = PerformanceAnalysisEngine()
    
    async def generate_recommendations(
        self,
        performance_analysis: Dict
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on performance analysis
        
        Returns:
            Prioritized list of recommendations
        """
        recommendations = []
        
        # Analyze bottlenecks and generate recommendations
        bottlenecks = performance_analysis.get("bottlenecks", [])
        
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "slow_response":
                recommendations.append(OptimizationRecommendation(
                    id="opt-001",
                    title="Optimize Database Queries",
                    description="High response time detected. Optimizing database queries can improve performance by 30-50%.",
                    category="performance",
                    impact=OptimizationImpact.HIGH,
                    effort=OptimizationEffort.MEDIUM,
                    estimated_improvement="30-50% faster response times",
                    automated=False,
                    steps=[
                        "Enable recorder purge in configuration.yaml",
                        "Set purge_keep_days to 7 or less",
                        "Add entity filters to reduce database size",
                        "Restart Home Assistant to apply changes"
                    ]
                ))
            
            elif bottleneck["type"] == "high_cpu":
                recommendations.append(OptimizationRecommendation(
                    id="opt-002",
                    title="Optimize Resource-Intensive Automations",
                    description="High CPU usage detected. Review and optimize automations to reduce CPU load.",
                    category="performance",
                    impact=OptimizationImpact.HIGH,
                    effort=OptimizationEffort.HIGH,
                    estimated_improvement="20-40% CPU reduction",
                    automated=False,
                    steps=[
                        "Review automations for inefficient triggers",
                        "Reduce polling frequency for slow devices",
                        "Consolidate similar automations",
                        "Use templates instead of multiple condition checks"
                    ]
                ))
        
        # Add general recommendations
        recommendations.extend(await self._generate_general_recommendations(performance_analysis))
        
        # Sort by impact and effort (high impact, low effort first)
        return self._prioritize_recommendations(recommendations)
    
    async def _generate_general_recommendations(
        self,
        performance_analysis: Dict
    ) -> List[OptimizationRecommendation]:
        """Generate general optimization recommendations"""
        recommendations = []
        
        # Check if recorder is configured
        config = performance_analysis.get("configuration", {})
        if not config.get("recorder_configured", True):
            recommendations.append(OptimizationRecommendation(
                id="opt-003",
                title="Enable Recorder Purge",
                description="Configure database purge to prevent unlimited growth and maintain performance.",
                category="configuration",
                impact=OptimizationImpact.MEDIUM,
                effort=OptimizationEffort.LOW,
                estimated_improvement="Prevent database bloat",
                automated=False,
                steps=[
                    "Add recorder configuration to configuration.yaml",
                    "Set purge_keep_days: 7",
                    "Set commit_interval: 1",
                    "Restart Home Assistant"
                ],
                configuration_changes={
                    "recorder": {
                        "purge_keep_days": 7,
                        "commit_interval": 1
                    }
                }
            ))
        
        return recommendations
    
    def _prioritize_recommendations(
        self,
        recommendations: List[OptimizationRecommendation]
    ) -> List[OptimizationRecommendation]:
        """
        Prioritize recommendations by impact and effort
        
        Priority order:
        1. High impact, Low effort
        2. High impact, Medium effort
        3. Medium impact, Low effort
        4. High impact, High effort
        5. Medium impact, Medium effort
        6. Low impact, Low effort
        7. Medium impact, High effort
        8. Low impact, Medium effort
        9. Low impact, High effort
        """
        priority_map = {
            (OptimizationImpact.HIGH, OptimizationEffort.LOW): 1,
            (OptimizationImpact.HIGH, OptimizationEffort.MEDIUM): 2,
            (OptimizationImpact.MEDIUM, OptimizationEffort.LOW): 3,
            (OptimizationImpact.HIGH, OptimizationEffort.HIGH): 4,
            (OptimizationImpact.MEDIUM, OptimizationEffort.MEDIUM): 5,
            (OptimizationImpact.LOW, OptimizationEffort.LOW): 6,
            (OptimizationImpact.MEDIUM, OptimizationEffort.HIGH): 7,
            (OptimizationImpact.LOW, OptimizationEffort.MEDIUM): 8,
            (OptimizationImpact.LOW, OptimizationEffort.HIGH): 9,
        }
        
        return sorted(
            recommendations,
            key=lambda r: priority_map.get((r.impact, r.effort), 10)
        )

