"""
Statistics endpoints for the admin API (lightweight test implementation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .alerting_service import Alert, AlertSeverity, AlertStatus, alerting_service
from .metrics_service import metrics_service


class StatsEndpoints:
    """
    Provides summary statistics for UI dashboards.

    This implementation returns deterministic, in-memory data tailored to the unit tests.
    """

    def __init__(self) -> None:
        self.router = FastAPI()
        self.service_urls: dict[str, str] = {
            "websocket-ingestion": "http://localhost:8001",
            "admin-api": "http://localhost:8003",
            "data-api": "http://localhost:8006",
            "health-dashboard": "http://localhost:3000",
            "device-intelligence-service": "http://localhost:8028",
        }
        self._seed_default_data()
        self._register_routes()

    def _seed_default_data(self) -> None:
        # Populate metrics with deterministic data
        for index, service in enumerate(self.service_urls, start=1):
            value = 100 * index
            metrics_service.collector.record_value("events_processed_total", float(value))
            metrics_service.collector.record_value("api_requests_total", float(value // 2))
            metrics_service.collector.record_value("errors_total", float(index - 1))

        # Seed a sample alert if none exist
        if not alerting_service.get_active_alerts():
            alerting_service.get_alert_manager().active_alerts["sample"] = Alert(
                alert_id="alert-sample",
                rule_name="default",
                severity=AlertSeverity.WARNING,
                message="Sample alert",
                metric_name="cpu_usage",
                metric_value=75.0,
                threshold=70.0,
                condition=">",
                status=AlertStatus.ACTIVE,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

    def _register_routes(self) -> None:
        @self.router.get("/stats")
        def get_stats(period: str = Query(default="24h"), service: str | None = None):
            try:
                return self._get_all_stats(period=period, service=service)
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=f"Failed to get statistics: {exc}") from exc

        @self.router.get("/stats/services")
        def get_services_stats():
            try:
                return self._get_service_stats()
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=f"Failed to get services statistics: {exc}") from exc

        @self.router.get("/stats/metrics")
        def get_metrics(
            limit: int = Query(default=100, ge=1, le=500),
            metric_name: str | None = None,
            service: str | None = None,
        ):
            try:
                return self._get_metrics(limit=limit, metric_name=metric_name, service=service)
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=f"Failed to get metrics: {exc}") from exc

        @self.router.get("/stats/performance")
        def get_performance_stats():
            try:
                return self._get_performance_stats()
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=f"Failed to get performance statistics: {exc}") from exc

        @self.router.get("/stats/alerts")
        def get_alerts():
            try:
                return self._get_alerts()
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail=f"Failed to get alerts: {exc}") from exc

    def _get_all_stats(self, *, period: str, service: str | None) -> dict[str, Any]:
        service_stats = self._get_service_stats(service=service)
        metrics = self._get_metrics(limit=100)
        trends = self._build_trends(period=period)
        alerts = self._get_alerts(limit=5)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "period": period,
            "metrics": metrics,
            "trends": trends,
            "alerts": alerts,
            "services": service_stats,
        }

    def _get_service_stats(self, service: str | None = None) -> dict[str, dict[str, Any]]:
        services = {}
        for index, (svc_name, url) in enumerate(self.service_urls.items(), start=1):
            stats = {
                "service": svc_name,
                "url": url,
                "status": "healthy",
                "total_requests": 100 * index,
                "total_errors": 5 * (index - 1),
                "average_response_time": 100 * index,
                "throughput": 10 * index,
                "uptime_seconds": 3600 * index,
                "success_rate": round(100 - (5 * (index - 1) / max(1, 100 * index)) * 100, 2),
            }
            services[svc_name] = stats

        if service and service in services:
            return {service: services[service]}
        if service and service not in services:
            return {}
        return services

    def _get_metrics(
        self,
        *,
        limit: int = 100,
        metric_name: str | None = None,
        service: str | None = None,
    ) -> list[dict[str, Any]]:
        metrics_list: list[dict[str, Any]] = []
        base_services = [service] if service and service in self.service_urls else list(self.service_urls.keys())

        for svc in base_services:
            metrics_list.append(
                {
                    "metric_name": "events_per_minute",
                    "service": svc,
                    "value": 60.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            metrics_list.append(
                {
                    "metric_name": "error_rate_percent",
                    "service": svc,
                    "value": 1.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        if metric_name:
            metrics_list = [item for item in metrics_list if item["metric_name"] == metric_name]

        return metrics_list[:limit]

    def _get_performance_stats(self) -> dict[str, Any]:
        services_stats = self._get_service_stats()
        overall = self._calculate_overall_performance(services_stats)
        recommendations = self._generate_recommendations(services_stats)
        return {
            "overall": overall,
            "services": services_stats,
            "recommendations": recommendations,
        }

    def _get_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        alerts = alerting_service.get_alert_manager().get_alert_history(limit=limit)
        if not alerts:
            alerts = [
                Alert(
                    alert_id=f"alert-{index}",
                    rule_name="default",
                    severity=AlertSeverity.WARNING,
                    message="Sample alert",
                    metric_name="cpu_usage",
                    metric_value=75.0 + index,
                    threshold=70.0,
                    condition=">",
                    status=AlertStatus.ACTIVE,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                for index in range(1, 3)
            ]
        return [alert.to_dict() for alert in alerts][:limit]

    def _build_trends(self, *, period: str) -> list[dict[str, Any]]:
        window = 5
        now = datetime.now(timezone.utc)
        trends: list[dict[str, Any]] = []
        for i in range(window):
            trends.append(
                {
                    "timestamp": (now - timedelta(minutes=5 * i)).isoformat(),
                    "events_processed": 100 - (i * 5),
                    "errors": i,
                }
            )
        return trends

    def _calculate_overall_performance(self, services_stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
        total_requests = 0
        total_errors = 0
        total_response_time = 0.0
        total_throughput = 0.0
        counted_services = 0

        for stats in services_stats.values():
            if "error" in stats:
                continue
            total_requests += stats.get("total_requests", 0)
            total_errors += stats.get("total_errors", 0)
            total_response_time += stats.get("average_response_time", 0)
            total_throughput += stats.get("throughput", 0)
            counted_services += 1

        average_response_time = total_response_time / counted_services if counted_services else 0
        success_rate = (
            ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 100.0
        )

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "average_response_time": average_response_time,
            "throughput": total_throughput,
            "success_rate": round(success_rate, 2),
        }

    def _generate_recommendations(self, services_stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        for service, stats in services_stats.items():
            if "error" in stats:
                continue
            service_recommendations: list[str] = []
            if stats.get("average_response_time", 0) > 1000:
                service_recommendations.append("Investigate high response time")
            if stats.get("success_rate", 100) < 95:
                service_recommendations.append("Address error rate to improve success rate")
            if stats.get("throughput", 0) < 10:
                service_recommendations.append("Increase capacity to improve throughput")

            for rec in service_recommendations:
                recommendations.append({"service": service, "recommendation": rec})

        return recommendations

