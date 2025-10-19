"""
Health monitoring service implementation

Context7 Best Practices Applied:
- Async/await for all I/O operations
- Proper exception handling
- Type hints throughout
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import get_settings
from .models import EnvironmentHealth, IntegrationHealth, PerformanceMetric
from .schemas import (
    EnvironmentHealthResponse,
    IntegrationHealthDetail,
    PerformanceMetrics,
    HealthStatus,
    IntegrationStatus
)
from .scoring_algorithm import HealthScoringAlgorithm
from .integration_checker import IntegrationHealthChecker

settings = get_settings()


class HealthMonitoringService:
    """
    Core health monitoring service
    
    Implements Context7 async patterns for Home Assistant health checks
    """
    
    def __init__(self):
        self.ha_url = settings.ha_url
        self.ha_token = settings.ha_token
        self.data_api_url = settings.data_api_url
        self.admin_api_url = settings.admin_api_url
        self.scoring_algorithm = HealthScoringAlgorithm()  # Enhanced scoring
    
    async def check_environment_health(
        self,
        db: AsyncSession
    ) -> EnvironmentHealthResponse:
        """
        Comprehensive environment health check
        
        Args:
            db: Async database session
            
        Returns:
            EnvironmentHealthResponse with complete health status
        """
        # Run all health checks in parallel (Context7 best practice)
        ha_check, integrations_check, performance_check = await asyncio.gather(
            self._check_ha_core(),
            self._check_integrations(),
            self._check_performance(),
            return_exceptions=True
        )
        
        # Handle exceptions gracefully
        ha_status = ha_check if not isinstance(ha_check, Exception) else {"status": "error", "version": "unknown"}
        integrations = integrations_check if not isinstance(integrations_check, Exception) else []
        performance = performance_check if not isinstance(performance_check, Exception) else {
            "response_time_ms": 0,
            "cpu_usage_percent": 0,
            "memory_usage_mb": 0,
            "uptime_seconds": 0
        }
        
        # Calculate overall health score using enhanced algorithm
        health_score, component_scores = self.scoring_algorithm.calculate_score(
            ha_status,
            integrations,
            performance
        )
        
        # Detect issues
        issues = self._detect_issues(ha_status, integrations, performance)
        
        # Determine overall status
        overall_status = self._determine_overall_status(health_score, issues)
        
        # Store health metric in database
        await self._store_health_metric(
            db,
            health_score,
            overall_status,
            ha_status.get("version"),
            integrations,
            performance,
            issues
        )
        
        # Build response
        return EnvironmentHealthResponse(
            health_score=health_score,
            ha_status=HealthStatus(overall_status),
            ha_version=ha_status.get("version"),
            integrations=[
                IntegrationHealthDetail(**integration)
                for integration in integrations
            ],
            performance=PerformanceMetrics(**performance),
            issues_detected=issues,
            timestamp=datetime.now()
        )
    
    async def _check_ha_core(self) -> Dict:
        """Check Home Assistant core status"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Check HA API availability
                async with session.get(
                    f"{self.ha_url}/api/",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "version": data.get("version", "unknown")
                        }
                    else:
                        return {
                            "status": "error",
                            "version": "unknown",
                            "error": f"HTTP {response.status}"
                        }
        except asyncio.TimeoutError:
            return {"status": "error", "version": "unknown", "error": "Timeout"}
        except Exception as e:
            return {"status": "error", "version": "unknown", "error": str(e)}
    
    async def _check_integrations(self) -> List[Dict]:
        """Check all integrations status"""
        integrations = []
        
        # Check MQTT integration
        mqtt_status = await self._check_mqtt_integration()
        integrations.append(mqtt_status)
        
        # Check Zigbee2MQTT integration
        z2m_status = await self._check_zigbee2mqtt_integration()
        integrations.append(z2m_status)
        
        # Check HA Ingestor services
        data_api_status = await self._check_data_api()
        integrations.append(data_api_status)
        
        return integrations
    
    async def _check_mqtt_integration(self) -> Dict:
        """Check MQTT broker status"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Check MQTT config entry
                async with session.get(
                    f"{self.ha_url}/api/config/config_entries/entry",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        entries = await response.json()
                        mqtt_entry = next((e for e in entries if e.get('domain') == 'mqtt'), None)
                        
                        if mqtt_entry:
                            return {
                                "name": "MQTT",
                                "type": "mqtt",
                                "status": IntegrationStatus.HEALTHY.value,
                                "is_configured": True,
                                "is_connected": True,
                                "error_message": None,
                                "last_check": datetime.now()
                            }
                        else:
                            return {
                                "name": "MQTT",
                                "type": "mqtt",
                                "status": IntegrationStatus.NOT_CONFIGURED.value,
                                "is_configured": False,
                                "is_connected": False,
                                "error_message": "MQTT integration not found",
                                "last_check": datetime.now()
                            }
        except Exception as e:
            return {
                "name": "MQTT",
                "type": "mqtt",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": False,
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now()
            }
    
    async def _check_zigbee2mqtt_integration(self) -> Dict:
        """Check Zigbee2MQTT integration status using integration checker"""
        try:
            # Use the integration checker to get real Zigbee2MQTT status
            integration_checker = IntegrationHealthChecker(
                ha_url=self.ha_url,
                ha_token=self.ha_token
            )
            result = await integration_checker.check_zigbee2mqtt_integration()
            
            return {
                "name": result.integration_name,
                "type": result.integration_type,
                "status": result.status.value,
                "is_configured": result.is_configured,
                "is_connected": result.is_connected,
                "error_message": result.error_message,
                "check_details": result.check_details,
                "last_check": result.last_check
            }
        except Exception as e:
            # Fallback if integration checker fails
            return {
                "name": "Zigbee2MQTT",
                "type": "zigbee2mqtt",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": False,
                "is_connected": False,
                "error_message": f"Integration check failed: {str(e)}",
                "check_details": {"error_type": type(e).__name__},
                "last_check": datetime.now()
            }
    
    async def _check_data_api(self) -> Dict:
        """Check HA Ingestor Data API status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.data_api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return {
                            "name": "Data API",
                            "type": "homeiq",
                            "status": IntegrationStatus.HEALTHY.value,
                            "is_configured": True,
                            "is_connected": True,
                            "error_message": None,
                            "last_check": datetime.now()
                        }
        except Exception as e:
            return {
                "name": "Data API",
                "type": "homeiq",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": True,
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now()
            }
    
    async def _check_performance(self) -> Dict:
        """Check system performance metrics"""
        # Placeholder - will be enhanced in Epic 30
        return {
            "response_time_ms": 45.2,
            "cpu_usage_percent": 12.5,
            "memory_usage_mb": 256.0,
            "uptime_seconds": 86400
        }
    
    def _calculate_health_score(
        self,
        ha_status: Dict,
        integrations: List[Dict],
        performance: Dict
    ) -> int:
        """
        Calculate overall health score (0-100)
        
        Weighting:
        - HA Core: 40%
        - Integrations: 40%
        - Performance: 20%
        """
        score = 0
        
        # HA Core score (40 points)
        if ha_status.get("status") == "healthy":
            score += 40
        elif ha_status.get("status") == "warning":
            score += 20
        
        # Integrations score (40 points)
        if integrations:
            healthy_count = sum(1 for i in integrations if i.get("status") == IntegrationStatus.HEALTHY.value)
            integration_score = (healthy_count / len(integrations)) * 40
            score += int(integration_score)
        
        # Performance score (20 points)
        response_time = performance.get("response_time_ms", 0)
        if response_time < 100:
            score += 20
        elif response_time < 500:
            score += 10
        elif response_time < 1000:
            score += 5
        
        return min(100, max(0, score))
    
    def _detect_issues(
        self,
        ha_status: Dict,
        integrations: List[Dict],
        performance: Dict
    ) -> List[str]:
        """Detect and list issues"""
        issues = []
        
        if ha_status.get("status") != "healthy":
            issues.append(f"Home Assistant core status: {ha_status.get('status')}")
        
        for integration in integrations:
            if integration.get("status") != IntegrationStatus.HEALTHY.value:
                issues.append(
                    f"{integration.get('name')} integration: {integration.get('status')} "
                    f"({integration.get('error_message', 'No details')})"
                )
        
        response_time = performance.get("response_time_ms", 0)
        if response_time > 1000:
            issues.append(f"High response time: {response_time}ms")
        
        return issues
    
    def _determine_overall_status(self, health_score: int, issues: List[str]) -> str:
        """Determine overall health status"""
        if health_score >= 80 and not issues:
            return HealthStatus.HEALTHY.value
        elif health_score >= 50:
            return HealthStatus.WARNING.value
        else:
            return HealthStatus.CRITICAL.value
    
    async def _store_health_metric(
        self,
        db: AsyncSession,
        health_score: int,
        status: str,
        ha_version: Optional[str],
        integrations: List[Dict],
        performance: Dict,
        issues: List[str]
    ):
        """Store health metric in database"""
        try:
            health_metric = EnvironmentHealth(
                health_score=health_score,
                ha_status=status,
                ha_version=ha_version,
                integrations_status=[
                    {
                        "name": i.get("name"),
                        "status": i.get("status"),
                        "is_connected": i.get("is_connected")
                    }
                    for i in integrations
                ],
                performance_metrics=performance,
                issues_detected=issues
            )
            
            db.add(health_metric)
            await db.commit()
            await db.refresh(health_metric)
            
        except Exception as e:
            await db.rollback()
            # Log error but don't fail the health check
            print(f"Error storing health metric: {e}")

