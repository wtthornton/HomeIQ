"""
Statistics and Metrics Endpoints
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
import os

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from shared.influxdb_query_client import InfluxDBQueryClient as AdminAPIInfluxDBClient

# Optional metrics_tracker import (only used in admin-api)
try:
    from .metrics_tracker import get_tracker
    HAS_METRICS_TRACKER = True
except ImportError:
    HAS_METRICS_TRACKER = False
    def get_tracker():
        """Fallback if metrics_tracker not available"""
        return None

logger = logging.getLogger(__name__)


class StatisticsResponse(BaseModel):
    """Statistics response model"""
    timestamp: datetime
    period: str
    metrics: Dict[str, Any]
    trends: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    source: str = "influxdb"  # Add source indicator


class MetricData(BaseModel):
    """Metric data model"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = {}


class StatsEndpoints:
    """Statistics and metrics endpoints"""
    
    def __init__(self):
        """Initialize stats endpoints"""
        self.router = APIRouter()
        
        # InfluxDB client for querying metrics
        self.influxdb_client = AdminAPIInfluxDBClient()
        self.use_influxdb = os.getenv("USE_INFLUXDB_STATS", "true").lower() == "true"
        
        # Keep service URLs for fallback - use Docker service names for internal communication
        self.service_urls = {
            "admin-api": os.getenv("ADMIN_API_URL", "http://homeiq-admin:8004"),
            "data-api": os.getenv("DATA_API_URL", "http://homeiq-data-api:8006"),
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://homeiq-websocket:8001"),
            "sports-api": os.getenv("SPORTS_API_URL", "http://homeiq-sports-api:8005"),
            "air-quality-service": os.getenv("AIR_QUALITY_URL", "http://homeiq-air-quality:8012"),
            "calendar-service": os.getenv("CALENDAR_URL", "http://homeiq-calendar:8013"),
            "carbon-intensity-service": os.getenv("CARBON_INTENSITY_URL", "http://homeiq-carbon-intensity:8010"),
            "data-retention": os.getenv("DATA_RETENTION_URL", "http://homeiq-data-retention:8080"),
            "electricity-pricing-service": os.getenv("ELECTRICITY_PRICING_URL", "http://homeiq-electricity-pricing:8011"),
            "energy-correlator": os.getenv("ENERGY_CORRELATOR_URL", "http://homeiq-energy-correlator:8017"),
            "smart-meter-service": os.getenv("SMART_METER_URL", "http://homeiq-smart-meter:8014"),
            "log-aggregator": os.getenv("LOG_AGGREGATOR_URL", "http://homeiq-log-aggregator:8015"),
            "weather-api": os.getenv("WEATHER_SERVICE_URL", "http://homeiq-weather-api:8009")
        }
        
        self._add_routes()
    
    async def initialize(self):
        """Initialize InfluxDB connection"""
        try:
            if self.use_influxdb:
                success = await self.influxdb_client.connect()
                if not success:
                    logger.warning("InfluxDB connection failed, will use fallback")
                    self.use_influxdb = False
                else:
                    logger.info("InfluxDB client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB: {e}")
            self.use_influxdb = False
    
    async def close(self):
        """Close InfluxDB connection"""
        try:
            await self.influxdb_client.close()
        except Exception as e:
            logger.error(f"Error closing InfluxDB client: {e}")
    
    def _add_routes(self):
        """Add statistics routes"""
        
        @self.router.get("/stats", response_model=StatisticsResponse)
        async def get_statistics(
            period: str = Query("1h", description="Time period for statistics"),
            service: Optional[str] = Query(None, description="Specific service to get stats for")
        ):
            """Get comprehensive statistics from InfluxDB"""
            try:
                # Try InfluxDB first
                if self.use_influxdb and self.influxdb_client.is_connected:
                    try:
                        stats = await self._get_stats_from_influxdb(period, service)
                        return StatisticsResponse(
                            timestamp=datetime.now(),
                            period=period,
                            metrics=stats["metrics"],
                            trends=stats["trends"],
                            alerts=stats["alerts"],
                            source="influxdb"
                        )
                    except Exception as influx_error:
                        logger.warning(f"InfluxDB query failed: {influx_error}, falling back to service calls")
                
                # Fallback to direct service calls
                logger.info("Using fallback: direct service HTTP calls")
                if service and service in self.service_urls:
                    stats = await self._get_service_stats(service, period)
                else:
                    stats = await self._get_all_stats(period)
                
                return StatisticsResponse(
                    timestamp=datetime.now(),
                    period=period,
                    metrics=stats["metrics"],
                    trends=stats["trends"],
                    alerts=stats["alerts"],
                    source="services-fallback"
                )
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get statistics"
                )
        
        @self.router.get("/stats/services", response_model=Dict[str, Any])
        async def get_services_stats():
            """Get statistics for all services"""
            try:
                all_stats = {}
                
                for service_name, service_url in self.service_urls.items():
                    try:
                        stats = await self._get_service_stats(service_name, "1h")
                        all_stats[service_name] = stats
                    except Exception as e:
                        logger.warning(f"Failed to get stats for {service_name}: {e}")
                        all_stats[service_name] = {"error": str(e)}
                
                return all_stats
                
            except Exception as e:
                logger.error(f"Error getting services statistics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get services statistics"
                )
        
        @self.router.get("/stats/metrics", response_model=List[MetricData])
        async def get_metrics(
            metric_name: Optional[str] = Query(None, description="Specific metric name"),
            service: Optional[str] = Query(None, description="Specific service"),
            limit: int = Query(100, description="Maximum number of metrics to return")
        ):
            """Get specific metrics"""
            try:
                metrics = await self._get_metrics(metric_name, service, limit)
                return metrics
                
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get metrics"
                )
        
        @self.router.get("/stats/performance", response_model=Dict[str, Any])
        async def get_performance_stats():
            """Get performance statistics"""
            try:
                performance_stats = await self._get_performance_stats()
                return performance_stats
                
            except Exception as e:
                logger.error(f"Error getting performance statistics: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get performance statistics"
                )
        
        @self.router.get("/stats/alerts", response_model=List[Dict[str, Any]])
        async def get_alerts():
            """Get active alerts"""
            try:
                alerts = await self._get_alerts()
                return alerts
                
            except Exception as e:
                logger.error(f"Error getting alerts: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get alerts"
                )
        
        # Note: /real-time-metrics endpoint moved to main.py as public endpoint
        # This route is kept for backward compatibility but should not be used
        # The public endpoint in main.py handles this route without authentication
    
    async def _get_stats_from_influxdb(self, period: str, service: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all statistics from InfluxDB
        
        Args:
            period: Time period for statistics
            service: Optional specific service to query
        
        Returns:
            Dictionary with metrics, trends, and alerts
        """
        # Get event statistics
        event_stats = await self.influxdb_client.get_event_statistics(period)
        
        # Get error rate
        error_stats = await self.influxdb_client.get_error_rate(period)
        
        # Get service metrics
        if service:
            service_metrics = {service: await self.influxdb_client.get_service_metrics(service, period)}
        else:
            service_stats = await self.influxdb_client.get_all_service_statistics(period)
            service_metrics = service_stats.get("services", {})
        
        # Get trends
        trends = await self.influxdb_client.get_event_trends(period, window="5m")
        
        # Calculate alerts from metrics
        alerts = self._calculate_alerts(service_metrics, error_stats)
        
        return {
            "metrics": {
                **event_stats,
                **error_stats,
                "services": service_metrics
            },
            "trends": trends.get("trends", []),
            "alerts": alerts
        }
    
    def _calculate_alerts(self, service_metrics: Dict[str, Any], error_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate alerts from metrics
        
        Args:
            service_metrics: Service metrics dictionary
            error_stats: Error statistics dictionary
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        # High error rate alert
        error_rate = error_stats.get("error_rate_percent", 0)
        if error_rate > 5:
            alerts.append({
                "level": "error",
                "service": "system",
                "message": f"High error rate: {error_rate}%",
                "timestamp": datetime.now().isoformat()
            })
        elif error_rate > 2:
            alerts.append({
                "level": "warning",
                "service": "system",
                "message": f"Elevated error rate: {error_rate}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Service health alerts
        for service, metrics in service_metrics.items():
            if isinstance(metrics, dict):
                success_rate = metrics.get("success_rate", 100)
                if success_rate < 90:
                    alerts.append({
                        "level": "error",
                        "service": service,
                        "message": f"Critical: Low success rate: {success_rate}%",
                        "timestamp": datetime.now().isoformat()
                    })
                elif success_rate < 95:
                    alerts.append({
                        "level": "warning",
                        "service": service,
                        "message": f"Low success rate: {success_rate}%",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Check processing time
                processing_time = metrics.get("processing_time_ms", 0)
                if processing_time > 1000:  # > 1 second
                    alerts.append({
                        "level": "warning",
                        "service": service,
                        "message": f"Slow processing: {processing_time}ms",
                        "timestamp": datetime.now().isoformat()
                    })
        
        return alerts
    
    async def _get_all_stats(self, period: str) -> Dict[str, Any]:
        """Get statistics for all services (fallback method)"""
        all_stats = {
            "metrics": {},
            "trends": {},
            "alerts": []
        }
        
        for service_name, service_url in self.service_urls.items():
            try:
                service_stats = await self._get_service_stats(service_name, period)
                all_stats["metrics"][service_name] = service_stats["metrics"]
                all_stats["trends"][service_name] = service_stats["trends"]
                all_stats["alerts"].extend(service_stats["alerts"])
            except Exception as e:
                logger.warning(f"Failed to get stats for {service_name}: {e}")
                all_stats["metrics"][service_name] = {"error": str(e)}
        
        return all_stats
    
    async def _get_service_stats(self, service_name: str, period: str) -> Dict[str, Any]:
        """Get statistics for a specific service"""
        service_url = self.service_urls[service_name]
        
        try:
            # Use shorter timeout for websocket-ingestion (5s instead of 10s)
            timeout = 5 if service_name == "websocket-ingestion" else 10
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                # Use /health endpoint for all services (most reliable)
                stats_url = f"{service_url}/health"
                
                try:
                    async with session.get(stats_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Transform service data to stats format
                            if service_name == "websocket-ingestion":
                                return await self._transform_websocket_health_to_stats(data, period)
                            else:
                                # For other services, create basic stats from health data
                                return self._transform_health_to_stats(data, service_name, period)
                        else:
                            raise Exception(f"HTTP {response.status}")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout getting stats for {service_name}")
                    raise Exception(f"Timeout after {timeout}s")
        except Exception as e:
            logger.error(f"Error getting stats for {service_name}: {e}")
            return {
                "metrics": {"error": str(e)},
                "trends": {},
                "alerts": [{"service": service_name, "level": "error", "message": str(e)}]
            }
    
    async def _transform_websocket_health_to_stats(self, health_data: Dict[str, Any], period: str) -> Dict[str, Any]:
        """Transform websocket-ingestion health data to stats format"""
        try:
            # Check if health_data has an error
            if "error" in health_data and health_data["error"]:
                raise Exception(health_data["error"])
            
            # Get response time from tracker (if available)
            response_time_ms = 0
            if HAS_METRICS_TRACKER:
                tracker = get_tracker()
                if tracker:
                    websocket_stats = await tracker.get_stats("websocket-ingestion")
                    response_time_ms = round(websocket_stats.get('avg', 0), 2)
            
            metrics = {
                "events_per_minute": 0,
                "error_rate": 0,
                "response_time_ms": response_time_ms,
                "connection_attempts": 0,
                "total_events_received": 0
            }
            
            # Extract metrics from health data
            if "subscription" in health_data and isinstance(health_data["subscription"], dict):
                subscription = health_data["subscription"]
                metrics["events_per_minute"] = subscription.get("event_rate_per_minute", 0)
                metrics["total_events_received"] = subscription.get("total_events_received", 0)
            
            if "connection" in health_data:
                connection = health_data["connection"]
                metrics["connection_attempts"] = connection.get("connection_attempts", 0)
                
                # Calculate error rate based on failed connections
                total_attempts = connection.get("connection_attempts", 0)
                failed_connections = connection.get("failed_connections", 0)
                if total_attempts > 0:
                    metrics["error_rate"] = round((failed_connections / total_attempts) * 100, 2)
            
            if "weather_enrichment" in health_data:
                weather = health_data["weather_enrichment"]
                total_processed = weather.get("total_events_processed", 0)
                failed_enrichments = weather.get("failed_enrichments", 0)
                if total_processed > 0:
                    weather_error_rate = (failed_enrichments / total_processed) * 100
                    metrics["error_rate"] = max(metrics["error_rate"], weather_error_rate)
            
            return {
                "metrics": metrics,
                "trends": {
                    "events_per_minute": [{"timestamp": health_data.get("timestamp"), "value": metrics["events_per_minute"]}],
                    "error_rate": [{"timestamp": health_data.get("timestamp"), "value": metrics["error_rate"]}]
                },
                "alerts": []
            }
            
        except Exception as e:
            logger.error(f"Error transforming websocket health to stats: {e}")
            return {
                "service": "websocket-ingestion",
                "status": "error",
                "error": str(e),
                "timestamp": health_data.get("timestamp", "")
            }
    
    
    async def _get_metrics(self, metric_name: Optional[str], service: Optional[str], limit: int) -> List[MetricData]:
        """Get specific metrics"""
        metrics = []
        
        services_to_check = [service] if service else list(self.service_urls.keys())
        
        for service_name in services_to_check:
            if service_name not in self.service_urls:
                continue
                
            try:
                service_url = self.service_urls[service_name]
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    params = {"limit": limit}
                    if metric_name:
                        params["metric"] = metric_name
                    
                    async with session.get(f"{service_url}/metrics", params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            for metric in data:
                                metrics.append(MetricData(
                                    name=metric["name"],
                                    value=metric["value"],
                                    unit=metric.get("unit", ""),
                                    timestamp=datetime.fromisoformat(metric["timestamp"]),
                                    tags={**metric.get("tags", {}), "service": service_name}
                                ))
            except Exception as e:
                logger.warning(f"Failed to get metrics for {service_name}: {e}")
        
        return metrics[:limit]
    
    async def _get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        performance_stats = {
            "overall": {},
            "services": {},
            "recommendations": []
        }
        
        for service_name, service_url in self.service_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(f"{service_url}/stats/performance") as response:
                        if response.status == 200:
                            data = await response.json()
                            performance_stats["services"][service_name] = data
                        else:
                            performance_stats["services"][service_name] = {"error": f"HTTP {response.status}"}
            except Exception as e:
                logger.warning(f"Failed to get performance stats for {service_name}: {e}")
                performance_stats["services"][service_name] = {"error": str(e)}
        
        # Calculate overall performance metrics
        performance_stats["overall"] = self._calculate_overall_performance(performance_stats["services"])
        
        # Generate recommendations
        performance_stats["recommendations"] = self._generate_recommendations(performance_stats["services"])
        
        return performance_stats
    
    async def _get_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        alerts = []
        
        for service_name, service_url in self.service_urls.items():
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(f"{service_url}/alerts") as response:
                        if response.status == 200:
                            data = await response.json()
                            for alert in data:
                                alert["service"] = service_name
                                alerts.append(alert)
            except Exception as e:
                logger.warning(f"Failed to get alerts for {service_name}: {e}")
                alerts.append({
                    "service": service_name,
                    "level": "error",
                    "message": f"Failed to get alerts: {e}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Sort alerts by severity and timestamp
        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        alerts.sort(key=lambda x: (severity_order.get(x.get("level", "info"), 3), x.get("timestamp", "")))
        
        return alerts
    
    def _calculate_overall_performance(self, services_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall performance metrics"""
        overall = {
            "total_requests": 0,
            "total_errors": 0,
            "average_response_time": 0,
            "success_rate": 0,
            "throughput": 0
        }
        
        valid_services = 0
        
        for service_name, stats in services_stats.items():
            if "error" in stats:
                continue
                
            valid_services += 1
            
            # Aggregate metrics
            overall["total_requests"] += stats.get("total_requests", 0)
            overall["total_errors"] += stats.get("total_errors", 0)
            overall["average_response_time"] += stats.get("average_response_time", 0)
            overall["throughput"] += stats.get("throughput", 0)
        
        if valid_services > 0:
            overall["average_response_time"] /= valid_services
            
            if overall["total_requests"] > 0:
                overall["success_rate"] = ((overall["total_requests"] - overall["total_errors"]) / overall["total_requests"]) * 100
        
        return overall
    
    def _generate_recommendations(self, services_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance recommendations"""
        recommendations = []
        
        for service_name, stats in services_stats.items():
            if "error" in stats:
                continue
            
            # Check response time
            if stats.get("average_response_time", 0) > 1000:  # > 1 second
                recommendations.append({
                    "service": service_name,
                    "type": "performance",
                    "level": "warning",
                    "message": f"High response time: {stats.get('average_response_time', 0):.2f}ms",
                    "recommendation": "Consider optimizing database queries or increasing resources"
                })
            
            # Check error rate
            success_rate = stats.get("success_rate", 100)
            if success_rate < 95:
                recommendations.append({
                    "service": service_name,
                    "type": "reliability",
                    "level": "error",
                    "message": f"Low success rate: {success_rate:.2f}%",
                    "recommendation": "Investigate error causes and improve error handling"
                })
            
            # Check throughput
            throughput = stats.get("throughput", 0)
            if throughput < 10:  # < 10 requests per second
                recommendations.append({
                    "service": service_name,
                    "type": "capacity",
                    "level": "info",
                    "message": f"Low throughput: {throughput:.2f} req/s",
                    "recommendation": "Consider scaling up or optimizing processing"
                })
        
        return recommendations
    
    async def _get_current_event_rate(self) -> float:
        """Get current event rate from websocket-ingestion service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.service_urls['websocket-ingestion']}/api/v1/event-rate",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("events_per_second", 0.0)
                    else:
                        logger.warning(f"Failed to get event rate from websocket-ingestion: {resp.status}")
                        return 0.0
        except Exception as e:
            logger.error(f"Error getting event rate: {e}")
            return 0.0
    
    async def _get_all_api_metrics(self) -> Dict[str, Any]:
        """Get metrics from all API services with enhanced error handling"""
        api_metrics = []
        active_calls = 0
        inactive_apis = 0
        error_apis = 0
        
        # List of data-feeding API services (removed admin-api and data-api)
        api_services = [
            {"name": "websocket-ingestion", "priority": "high", "timeout": 3},
            {"name": "sports-api", "priority": "medium", "timeout": 5},
            {"name": "air-quality-service", "priority": "medium", "timeout": 5},
            {"name": "calendar-service", "priority": "medium", "timeout": 5},
            {"name": "carbon-intensity-service", "priority": "medium", "timeout": 5},
            {"name": "data-retention", "priority": "medium", "timeout": 5},
            {"name": "electricity-pricing-service", "priority": "medium", "timeout": 5},
            {"name": "energy-correlator", "priority": "medium", "timeout": 5},
            {"name": "smart-meter-service", "priority": "medium", "timeout": 5},
            {"name": "log-aggregator", "priority": "low", "timeout": 5},
            {"name": "weather-api", "priority": "low", "timeout": 5}
        ]
        
        # Get metrics from each service in parallel with individual timeouts
        tasks = []
        for service_info in api_services:
            service_name = service_info["name"]
            if service_name in self.service_urls:
                tasks.append(self._get_api_metrics_with_timeout(
                    service_name, 
                    self.service_urls[service_name],
                    service_info["timeout"]
                ))
            else:
                # Service URL not configured - create a simple async task that returns the fallback
                async def get_fallback():
                    return self._create_fallback_metric(service_name, "not_configured")
                tasks.append(get_fallback())
        
        # Wait for all tasks to complete with overall timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=15  # Overall timeout of 15 seconds
            )
        except asyncio.TimeoutError:
            logger.warning("Overall timeout reached while fetching API metrics")
            # Create fallback results for any incomplete tasks
            results = []
            for i, task in enumerate(tasks):
                if task.done():
                    try:
                        results.append(task.result())
                    except Exception as e:
                        results.append(e)
                else:
                    service_name = api_services[i]["name"]
                    results.append(self._create_fallback_metric(service_name, "timeout"))
        
        # Process results with enhanced error categorization
        for i, result in enumerate(results):
            service_name = api_services[i]["name"]
            if isinstance(result, Exception):
                logger.error(f"Error getting metrics from {service_name}: {result}")
                error_apis += 1
                # Add error metric to results
                api_metrics.append(self._create_fallback_metric(service_name, "error", str(result)))
            else:
                api_metrics.append(result)
                if result.get("status") == "active":
                    active_calls += 1
                elif result.get("status") == "error":
                    error_apis += 1
                else:
                    inactive_apis += 1
        
        return {
            "api_metrics": api_metrics,
            "active_calls": active_calls,
            "inactive_apis": inactive_apis,
            "error_apis": error_apis,
            "total_apis": len(api_services)
        }
    
    async def _get_api_metrics(self, service_name: str, service_url: str) -> Dict[str, Any]:
        """Get metrics from a specific API service"""
        start_time = datetime.now()
        try:
            async with aiohttp.ClientSession() as session:
                # Try /health endpoint first, then fall back to /api/v1/event-rate
                health_url = f"{service_url}/health"
                async with session.get(health_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract events_per_hour from health response
                        events_per_hour = 0.0
                        if "events_per_hour" in data:
                            events_per_hour = data["events_per_hour"]
                        elif "event_rate_per_minute" in data:
                            # Convert event_rate_per_minute to events_per_hour
                            events_per_hour = data["event_rate_per_minute"] * 60
                        elif "subscription" in data and "event_rate_per_minute" in data["subscription"]:
                            # For websocket service that has nested subscription stats
                            events_per_hour = data["subscription"]["event_rate_per_minute"] * 60
                        
                        # Extract uptime
                        uptime_seconds = 0.0
                        if "uptime_seconds" in data:
                            uptime_seconds = data["uptime_seconds"]
                        elif "uptime" in data:
                            # Parse uptime string like "1:25:24.575842" to seconds
                            uptime_str = data["uptime"]
                            try:
                                parts = uptime_str.split(":")
                                if len(parts) == 3:
                                    hours, minutes, seconds = parts
                                    uptime_seconds = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                            except (ValueError, AttributeError):
                                pass
                        
                        # Extract basic health info and set metrics
                        return {
                            "service": service_name,
                            "events_per_hour": events_per_hour,
                            "uptime_seconds": uptime_seconds,
                            "status": "active",
                            "response_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                            "last_success": datetime.now().isoformat(),
                            "error_message": None,
                            "is_fallback": False
                        }
                    else:
                        logger.warning(f"Failed to get health from {service_name}: {resp.status}")
                        return {
                            "service": service_name,
                            "events_per_hour": 0.0,
                            "uptime_seconds": 0.0,
                            "status": "inactive",
                            "response_time_ms": None,
                            "last_success": None,
                            "error_message": f"HTTP {resp.status}",
                            "is_fallback": True
                        }
        except Exception as e:
            logger.error(f"Error getting health from {service_name}: {e}")
            return {
                "service": service_name,
                "events_per_hour": 0.0,
                "uptime_seconds": 0.0,
                "status": "error",
                "response_time_ms": None,
                "last_success": None,
                "error_message": str(e),
                "is_fallback": True
            }
    
    async def _get_active_data_sources(self) -> List[str]:
        """
        Get list of active data sources from InfluxDB.
        Story 24.1: Query InfluxDB for measurements with recent activity instead of hardcoded list.
        
        Returns:
            List of active measurement names (data sources)
        """
        try:
            if not self.use_influxdb or not self.influxdb_client.is_connected:
                logger.warning("InfluxDB not available for data source discovery")
                return []
            
            # Query InfluxDB for all measurements (data sources)
            query = '''
            import "influxdata/influxdb/schema"
            schema.measurements(bucket: "home_assistant_events")
            '''
            
            result = await self.influxdb_client.query(query)
            
            # Extract measurement names
            measurements = []
            for table in result:
                for record in table.records:
                    measurement = record.values.get("_value")
                    if measurement:
                        measurements.append(measurement)
            
            logger.info(f"Discovered {len(measurements)} active data sources from InfluxDB")
            return measurements
            
        except Exception as e:
            logger.error(f"Error querying active data sources from InfluxDB: {e}")
            # Return empty list instead of hardcoded fallback
            return []
    
    async def _get_api_metrics_with_timeout(self, service_name: str, service_url: str, timeout: int) -> Dict[str, Any]:
        """Get metrics from a specific API service with individual timeout"""
        start_time = datetime.now()
        try:
            async with aiohttp.ClientSession() as session:
                # Use /health endpoint for all services
                health_url = f"{service_url}/health"
                async with session.get(health_url, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract events_per_hour from health response
                        events_per_hour = 0.0
                        if "events_per_hour" in data:
                            events_per_hour = data["events_per_hour"]
                        elif "event_rate_per_minute" in data:
                            # Convert event_rate_per_minute to events_per_hour
                            events_per_hour = data["event_rate_per_minute"] * 60
                        elif "subscription" in data and "event_rate_per_minute" in data["subscription"]:
                            # For websocket service that has nested subscription stats
                            events_per_hour = data["subscription"]["event_rate_per_minute"] * 60
                        
                        # Special handling for specific services to extract real metrics
                        if service_name == "weather-api":
                            # Get weather API request metrics from websocket-ingestion service
                            try:
                                websocket_url = self.service_urls.get("websocket-ingestion", "http://homeiq-websocket:8001")
                                async with aiohttp.ClientSession() as ws_session:
                                    async with ws_session.get(f"{websocket_url}/health", timeout=timeout) as ws_resp:
                                        if ws_resp.status == 200:
                                            ws_data = await ws_resp.json()
                                            if "weather_enrichment" in ws_data and "weather_client_stats" in ws_data["weather_enrichment"]:
                                                weather_stats = ws_data["weather_enrichment"]["weather_client_stats"]
                                                total_requests = weather_stats.get("total_requests", 0)
                                                
                                                # Calculate hourly rate based on uptime
                                                uptime_str = ws_data.get("uptime", "0:0:0")
                                                try:
                                                    parts = uptime_str.split(":")
                                                    if len(parts) == 3:
                                                        hours, minutes, seconds = parts
                                                        uptime_hours = float(hours) + float(minutes)/60 + float(seconds)/3600
                                                        if uptime_hours > 0:
                                                            events_per_hour = total_requests / uptime_hours
                                                except (ValueError, AttributeError):
                                                    # Fallback: assume 1 hour if parsing fails
                                                    events_per_hour = total_requests
                            except Exception as e:
                                logger.warning(f"Could not get weather API stats from websocket-ingestion: {e}")
                                events_per_hour = 0.0
                        
                        elif service_name in ["sports-api", "air-quality-service", "calendar-service", "carbon-intensity-service", 
                                            "electricity-pricing-service", "energy-correlator", "smart-meter-service"]:
                            # These services typically don't process events but provide data
                            # Set to 0 as they are data providers, not event processors
                            events_per_hour = 0.0
                        
                        elif service_name == "data-retention":
                            # Data retention service manages data cleanup, not event processing
                            events_per_hour = 0.0
                        
                        elif service_name == "log-aggregator":
                            # Log aggregator processes logs, not HA events
                            events_per_hour = 0.0
                        
                        # Extract uptime
                        uptime_seconds = 0.0
                        if "uptime_seconds" in data:
                            uptime_seconds = data["uptime_seconds"]
                        elif "uptime" in data:
                            # Parse uptime string like "1:25:24.575842" to seconds
                            uptime_str = data["uptime"]
                            try:
                                parts = uptime_str.split(":")
                                if len(parts) == 3:
                                    hours, minutes, seconds = parts
                                    uptime_seconds = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                            except (ValueError, AttributeError):
                                pass
                        
                        return {
                            "service": service_name,
                            "events_per_hour": events_per_hour,
                            "uptime_seconds": uptime_seconds,
                            "status": "active",
                            "response_time_ms": (datetime.now() - start_time).total_seconds() * 1000,  # Could be calculated if needed
                            "last_success": datetime.now().isoformat()
                        }
                    else:
                        logger.warning(f"Failed to get metrics from {service_name}: {resp.status}")
                        return self._create_fallback_metric(service_name, "inactive", f"HTTP {resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting metrics from {service_name} after {timeout}s")
            return self._create_fallback_metric(service_name, "timeout", f"Timeout after {timeout}s")
        except Exception as e:
            logger.error(f"Error getting metrics from {service_name}: {e}")
            return self._create_fallback_metric(service_name, "error", str(e))
    
    def _transform_health_to_stats(self, health_data: Dict[str, Any], service_name: str, period: str) -> Dict[str, Any]:
        """Transform health data to stats format for services without dedicated stats endpoints"""
        try:
            # Extract basic metrics from health data
            status = health_data.get("status", "unknown")
            uptime_seconds = 0.0
            
            if "uptime_seconds" in health_data:
                uptime_seconds = health_data["uptime_seconds"]
            elif "uptime" in health_data:
                # Parse uptime string like "1:25:24.575842" to seconds
                uptime_str = health_data["uptime"]
                try:
                    parts = uptime_str.split(":")
                    if len(parts) == 3:
                        hours, minutes, seconds = parts
                        uptime_seconds = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                except (ValueError, AttributeError):
                    pass
            
            # Create basic stats structure
            return {
                "metrics": {
                    "status": status,
                    "uptime_seconds": uptime_seconds,
                    "healthy": status == "healthy"
                },
                "trends": {},
                "alerts": [] if status == "healthy" else [{
                    "service": service_name,
                    "level": "error" if status == "unhealthy" else "warning",
                    "message": f"Service status: {status}"
                }]
            }
        except Exception as e:
            logger.error(f"Error transforming health data for {service_name}: {e}")
            return {
                "metrics": {"error": str(e)},
                "trends": {},
                "alerts": [{
                    "service": service_name,
                    "level": "error",
                    "message": f"Failed to transform health data: {str(e)}"
                }]
            }
    
    def _create_fallback_metric(self, service_name: str, status: str, error_message: str = None) -> Dict[str, Any]:
        """Create a fallback metric when service is unavailable"""
        return {
            "service": service_name,
            "events_per_hour": 0.0,
            "uptime_seconds": 0.0,
            "status": status,
            "response_time_ms": None,
            "last_success": None,
            "error_message": error_message,
            "is_fallback": True
        }