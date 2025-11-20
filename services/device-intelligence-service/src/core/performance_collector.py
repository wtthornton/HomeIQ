"""
Device Intelligence Service - Performance Metrics Collector

Collects and aggregates device performance metrics for analysis.
"""

import asyncio
import logging
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceCollector:
    """Collects and aggregates device performance metrics."""

    def __init__(self, retention_hours: int = 24, max_points_per_device: int = 1000):
        self.metrics_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_device))
        self.aggregated_metrics: dict[str, dict[str, Any]] = {}
        self.retention_hours = retention_hours
        self.max_points_per_device = max_points_per_device
        self._cleanup_task = None

    async def start_cleanup_task(self):
        """Start the cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())

    async def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def collect_device_metrics(self, device_id: str, metrics: dict[str, Any]):
        current_time = datetime.now(timezone.utc)

        # Add timestamp to metrics
        metric_entry = {
            "timestamp": current_time,
            "device_id": device_id,
            **metrics
        }

        # Store in history
        self.metrics_history[device_id].append(metric_entry)

        # Update aggregated metrics
        await self._update_aggregated_metrics(device_id)

        logger.debug(f"Collected metrics for device {device_id}")

    async def _update_aggregated_metrics(self, device_id: str):
        """Update aggregated metrics for device."""
        if device_id not in self.metrics_history or not self.metrics_history[device_id]:
            return

        metrics_list = list(self.metrics_history[device_id])
        if not metrics_list:
            return

        # Calculate aggregated metrics
        response_times = [m.get("response_time", 0) for m in metrics_list if m.get("response_time") is not None]
        error_rates = [m.get("error_rate", 0) for m in metrics_list if m.get("error_rate") is not None]
        battery_levels = [m.get("battery_level", 100) for m in metrics_list if m.get("battery_level") is not None]
        signal_strengths = [m.get("signal_strength", -50) for m in metrics_list if m.get("signal_strength") is not None]
        cpu_usage = [m.get("cpu_usage", 0) for m in metrics_list if m.get("cpu_usage") is not None]
        memory_usage = [m.get("memory_usage", 0) for m in metrics_list if m.get("memory_usage") is not None]
        temperatures = [m.get("temperature", 25) for m in metrics_list if m.get("temperature") is not None]

        # Calculate statistics
        self.aggregated_metrics[device_id] = {
            "device_id": device_id,
            "total_measurements": len(metrics_list),
            "time_range": {
                "start": metrics_list[0]["timestamp"].isoformat(),
                "end": metrics_list[-1]["timestamp"].isoformat()
            },
            "response_time": {
                "avg": statistics.mean(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": self._percentile(response_times, 95) if response_times else 0,
                "count": len(response_times)
            },
            "error_rate": {
                "avg": statistics.mean(error_rates) if error_rates else 0,
                "min": min(error_rates) if error_rates else 0,
                "max": max(error_rates) if error_rates else 0,
                "median": statistics.median(error_rates) if error_rates else 0,
                "count": len(error_rates)
            },
            "battery_level": {
                "avg": statistics.mean(battery_levels) if battery_levels else 100,
                "min": min(battery_levels) if battery_levels else 100,
                "max": max(battery_levels) if battery_levels else 100,
                "median": statistics.median(battery_levels) if battery_levels else 100,
                "count": len(battery_levels)
            },
            "signal_strength": {
                "avg": statistics.mean(signal_strengths) if signal_strengths else -50,
                "min": min(signal_strengths) if signal_strengths else -50,
                "max": max(signal_strengths) if signal_strengths else -50,
                "median": statistics.median(signal_strengths) if signal_strengths else -50,
                "count": len(signal_strengths)
            },
            "cpu_usage": {
                "avg": statistics.mean(cpu_usage) if cpu_usage else 0,
                "min": min(cpu_usage) if cpu_usage else 0,
                "max": max(cpu_usage) if cpu_usage else 0,
                "median": statistics.median(cpu_usage) if cpu_usage else 0,
                "count": len(cpu_usage)
            },
            "memory_usage": {
                "avg": statistics.mean(memory_usage) if memory_usage else 0,
                "min": min(memory_usage) if memory_usage else 0,
                "max": max(memory_usage) if memory_usage else 0,
                "median": statistics.median(memory_usage) if memory_usage else 0,
                "count": len(memory_usage)
            },
            "temperature": {
                "avg": statistics.mean(temperatures) if temperatures else 25,
                "min": min(temperatures) if temperatures else 25,
                "max": max(temperatures) if temperatures else 25,
                "median": statistics.median(temperatures) if temperatures else 25,
                "count": len(temperatures)
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    def _percentile(self, data: list[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0

        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    async def get_device_performance_summary(self, device_id: str) -> dict[str, Any]:
        """Get device performance summary."""
        return self.aggregated_metrics.get(device_id, {})

    async def get_device_metrics_history(self, device_id: str, hours: int = 24) -> list[dict[str, Any]]:
        """Get device metrics history for specified hours."""
        if device_id not in self.metrics_history:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        metrics_list = list(self.metrics_history[device_id])

        # Filter by time range
        filtered_metrics = [
            m for m in metrics_list
            if m["timestamp"] >= cutoff_time
        ]

        return filtered_metrics

    async def get_device_metrics_trend(self, device_id: str, metric_name: str, hours: int = 24) -> dict[str, Any]:
        """Get trend analysis for specific metric."""
        metrics_history = await self.get_device_metrics_history(device_id, hours)

        if len(metrics_history) < 2:
            return {"trend": "insufficient_data", "change_percent": 0}

        # Extract metric values
        values = [m.get(metric_name) for m in metrics_history if m.get(metric_name) is not None]

        if len(values) < 2:
            return {"trend": "insufficient_data", "change_percent": 0}

        # Calculate trend
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        if not first_half or not second_half:
            return {"trend": "insufficient_data", "change_percent": 0}

        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)

        if avg_first == 0:
            change_percent = 0
        else:
            change_percent = ((avg_second - avg_first) / avg_first) * 100

        # Determine trend direction
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "first_half_avg": round(avg_first, 2),
            "second_half_avg": round(avg_second, 2),
            "data_points": len(values)
        }

    async def get_all_devices_performance(self) -> dict[str, dict[str, Any]]:
        """Get performance summary for all devices."""
        return self.aggregated_metrics.copy()

    async def get_performance_comparison(self, device_ids: list[str]) -> dict[str, Any]:
        """Compare performance metrics across multiple devices."""
        comparison = {
            "devices": {},
            "summary": {
                "total_devices": len(device_ids),
                "avg_response_time": 0,
                "avg_error_rate": 0,
                "avg_battery_level": 0,
                "avg_signal_strength": 0
            }
        }

        response_times = []
        error_rates = []
        battery_levels = []
        signal_strengths = []

        for device_id in device_ids:
            if device_id in self.aggregated_metrics:
                device_metrics = self.aggregated_metrics[device_id]
                comparison["devices"][device_id] = device_metrics

                # Collect for summary
                if device_metrics["response_time"]["avg"] > 0:
                    response_times.append(device_metrics["response_time"]["avg"])
                if device_metrics["error_rate"]["avg"] > 0:
                    error_rates.append(device_metrics["error_rate"]["avg"])
                if device_metrics["battery_level"]["avg"] > 0:
                    battery_levels.append(device_metrics["battery_level"]["avg"])
                if device_metrics["signal_strength"]["avg"] != -50:
                    signal_strengths.append(device_metrics["signal_strength"]["avg"])

        # Calculate summary statistics
        if response_times:
            comparison["summary"]["avg_response_time"] = round(statistics.mean(response_times), 2)
        if error_rates:
            comparison["summary"]["avg_error_rate"] = round(statistics.mean(error_rates), 4)
        if battery_levels:
            comparison["summary"]["avg_battery_level"] = round(statistics.mean(battery_levels), 1)
        if signal_strengths:
            comparison["summary"]["avg_signal_strength"] = round(statistics.mean(signal_strengths), 1)

        return comparison

    async def _cleanup_old_metrics(self):
        """Clean up old metrics data."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)

                for device_id in list(self.metrics_history.keys()):
                    metrics = self.metrics_history[device_id]

                    # Remove old metrics
                    while metrics and metrics[0]["timestamp"] < cutoff_time:
                        metrics.popleft()

                    # Remove empty entries
                    if not metrics:
                        del self.metrics_history[device_id]
                        if device_id in self.aggregated_metrics:
                            del self.aggregated_metrics[device_id]

                logger.debug("Cleaned up old metrics data")

            except Exception as e:
                logger.error(f"Error during metrics cleanup: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get performance collector statistics."""
        total_devices = len(self.metrics_history)
        total_metrics_points = sum(len(metrics) for metrics in self.metrics_history.values())

        return {
            "total_devices_tracked": total_devices,
            "total_metrics_points": total_metrics_points,
            "retention_hours": self.retention_hours,
            "max_points_per_device": self.max_points_per_device,
            "devices_with_data": list(self.metrics_history.keys())
        }


# Global performance collector instance
performance_collector = PerformanceCollector()
