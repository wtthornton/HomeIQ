"""Storage usage monitoring and management."""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import psutil

logger = logging.getLogger(__name__)

@dataclass
class StorageMetrics:
    """Storage usage metrics."""

    timestamp: datetime
    total_size_bytes: int
    used_size_bytes: int
    available_size_bytes: int
    usage_percentage: float
    database_size_bytes: int | None = None
    log_size_bytes: int | None = None
    backup_size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_size_bytes": self.total_size_bytes,
            "used_size_bytes": self.used_size_bytes,
            "available_size_bytes": self.available_size_bytes,
            "usage_percentage": self.usage_percentage,
            "database_size_bytes": self.database_size_bytes,
            "log_size_bytes": self.log_size_bytes,
            "backup_size_bytes": self.backup_size_bytes,
            "total_size_gb": self.total_size_bytes / (1024**3),
            "used_size_gb": self.used_size_bytes / (1024**3),
            "available_size_gb": self.available_size_bytes / (1024**3),
            "database_size_gb": self.database_size_bytes / (1024**3) if self.database_size_bytes else None,
            "log_size_gb": self.log_size_bytes / (1024**3) if self.log_size_bytes else None,
            "backup_size_gb": self.backup_size_bytes / (1024**3) if self.backup_size_bytes else None,
        }

@dataclass
class StorageAlert:
    """Storage usage alert."""

    alert_type: str
    severity: str
    message: str
    threshold_percentage: float
    current_percentage: float
    timestamp: datetime
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "threshold_percentage": self.threshold_percentage,
            "current_percentage": self.current_percentage,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
        }

class StorageMonitor:
    """Monitors storage usage and generates alerts."""

    def __init__(self, influxdb_client=None, storage_paths: list[str] | None = None):
        """
        Initialize storage monitor.

        Args:
            influxdb_client: InfluxDB client for database size monitoring
            storage_paths: List of storage paths to monitor
        """
        self.influxdb_client = influxdb_client
        self.storage_paths = storage_paths or ["/", "/var/lib/influxdb", "/var/log"]
        self.metrics_history: list[StorageMetrics] = []
        self.active_alerts: list[StorageAlert] = []
        self.is_running = False
        self.monitor_task: asyncio.Task | None = None

        # Alert thresholds
        self.warning_threshold = 80.0  # 80% usage
        self.critical_threshold = 90.0  # 90% usage

        logger.info("Storage monitor initialized")

    async def start(self) -> None:
        """Start the storage monitor."""
        if self.is_running:
            logger.warning("Storage monitor is already running")
            return

        self.is_running = True
        logger.info("Storage monitor started")

    async def stop(self) -> None:
        """Stop the storage monitor."""
        if not self.is_running:
            return

        self.is_running = False

        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor_task

        logger.info("Storage monitor stopped")

    async def collect_metrics(self) -> StorageMetrics:
        """
        Collect current storage metrics.

        Returns:
            StorageMetrics: Current storage metrics
        """
        try:
            # Get system disk usage
            disk_usage = psutil.disk_usage("/")

            # Get database size if InfluxDB client is available
            database_size = await self._get_database_size()

            # Get log size
            log_size = await self._get_log_size()

            # Get backup size
            backup_size = await self._get_backup_size()

            metrics = StorageMetrics(
                timestamp=datetime.utcnow(),
                total_size_bytes=disk_usage.total,
                used_size_bytes=disk_usage.used,
                available_size_bytes=disk_usage.free,
                usage_percentage=(disk_usage.used / disk_usage.total) * 100,
                database_size_bytes=database_size,
                log_size_bytes=log_size,
                backup_size_bytes=backup_size,
            )

            self.metrics_history.append(metrics)

            # Keep only last 1000 metrics to prevent memory issues
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            # Check for alerts
            await self._check_alerts(metrics)

            return metrics

        except Exception as e:
            logger.exception(f"Failed to collect storage metrics: {e}")
            raise

    async def _get_database_size(self) -> int | None:
        """
        Get InfluxDB database size.

        Returns:
            Database size in bytes or None if unavailable
        """
        if not self.influxdb_client:
            return None

        try:
            # Query InfluxDB for database size
            query = """
            from(bucket: "home-assistant-events")
                |> range(start: -1y)
                |> count()
            """

            await self.influxdb_client.query(query)

            # This is a simplified approach - in reality, you'd need to query
            # the actual database size from InfluxDB system tables
            return None  # Placeholder

        except Exception as e:
            logger.warning(f"Failed to get database size: {e}")
            return None

    async def _get_log_size(self) -> int | None:
        """
        Get log file size.

        Returns:
            Log size in bytes or None if unavailable
        """
        try:
            import os
            log_path = "/var/log"
            if os.path.exists(log_path):
                total_size = 0
                for dirpath, _dirnames, filenames in os.walk(log_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        with contextlib.suppress(OSError):
                            total_size += os.path.getsize(filepath)
                return total_size
            return None

        except Exception as e:
            logger.warning(f"Failed to get log size: {e}")
            return None

    async def _get_backup_size(self) -> int | None:
        """
        Get backup file size.

        Returns:
            Backup size in bytes or None if unavailable
        """
        try:
            import os
            backup_path = "/backups"
            if os.path.exists(backup_path):
                total_size = 0
                for dirpath, _dirnames, filenames in os.walk(backup_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        with contextlib.suppress(OSError):
                            total_size += os.path.getsize(filepath)
                return total_size
            return None

        except Exception as e:
            logger.warning(f"Failed to get backup size: {e}")
            return None

    async def _check_alerts(self, metrics: StorageMetrics) -> None:
        """
        Check for storage usage alerts.

        Args:
            metrics: Current storage metrics
        """
        current_percentage = metrics.usage_percentage

        # Check for critical threshold
        if current_percentage >= self.critical_threshold:
            await self._create_alert(
                alert_type="storage_critical",
                severity="critical",
                message=f"Storage usage is critical: {current_percentage:.1f}%",
                threshold_percentage=self.critical_threshold,
                current_percentage=current_percentage,
            )

        # Check for warning threshold
        elif current_percentage >= self.warning_threshold:
            await self._create_alert(
                alert_type="storage_warning",
                severity="warning",
                message=f"Storage usage is high: {current_percentage:.1f}%",
                threshold_percentage=self.warning_threshold,
                current_percentage=current_percentage,
            )

        # Resolve alerts if usage drops below thresholds
        else:
            await self._resolve_alerts()

    async def _create_alert(self, alert_type: str, severity: str, message: str,
                          threshold_percentage: float, current_percentage: float) -> None:
        """
        Create a storage alert.

        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            threshold_percentage: Threshold that triggered the alert
            current_percentage: Current usage percentage
        """
        # Check if alert already exists
        existing_alert = next(
            (alert for alert in self.active_alerts
             if alert.alert_type == alert_type and not alert.resolved),
            None,
        )

        if existing_alert:
            return  # Alert already exists

        alert = StorageAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            threshold_percentage=threshold_percentage,
            current_percentage=current_percentage,
            timestamp=datetime.utcnow(),
        )

        self.active_alerts.append(alert)
        logger.warning(f"Storage alert created: {message}")

    async def _resolve_alerts(self) -> None:
        """Resolve storage alerts when usage drops below thresholds."""
        for alert in self.active_alerts:
            if not alert.resolved and alert.current_percentage < alert.threshold_percentage:
                alert.resolved = True
                logger.info(f"Storage alert resolved: {alert.message}")

    async def schedule_monitoring(self, interval_minutes: int = 5) -> None:
        """
        Schedule periodic storage monitoring.

        Args:
            interval_minutes: Interval between monitoring runs in minutes
        """
        if self.monitor_task and not self.monitor_task.done():
            logger.warning("Monitoring task is already running")
            return

        async def monitoring_loop():
            while self.is_running:
                try:
                    await self.collect_metrics()
                except Exception as e:
                    logger.exception(f"Storage monitoring failed: {e}")

                # Wait for next monitoring cycle
                await asyncio.sleep(interval_minutes * 60)

        self.monitor_task = asyncio.create_task(monitoring_loop())
        logger.info(f"Scheduled storage monitoring every {interval_minutes} minutes")

    def get_current_metrics(self) -> StorageMetrics | None:
        """
        Get current storage metrics.

        Returns:
            Latest storage metrics or None if no metrics available
        """
        return self.metrics_history[-1] if self.metrics_history else None

    def get_metrics_history(self, hours: int = 24) -> list[StorageMetrics]:
        """
        Get storage metrics history.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of storage metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            metrics for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]

    def get_active_alerts(self) -> list[StorageAlert]:
        """
        Get active storage alerts.

        Returns:
            List of active alerts
        """
        return [alert for alert in self.active_alerts if not alert.resolved]

    def get_storage_statistics(self) -> dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary containing storage statistics
        """
        if not self.metrics_history:
            return {
                "total_metrics": 0,
                "current_usage_percentage": 0.0,
                "average_usage_percentage": 0.0,
                "peak_usage_percentage": 0.0,
                "active_alerts": 0,
                "last_measurement": None,
            }

        current_metrics = self.get_current_metrics()
        usage_percentages = [metrics.usage_percentage for metrics in self.metrics_history]

        return {
            "total_metrics": len(self.metrics_history),
            "current_usage_percentage": current_metrics.usage_percentage if current_metrics else 0.0,
            "average_usage_percentage": sum(usage_percentages) / len(usage_percentages),
            "peak_usage_percentage": max(usage_percentages),
            "active_alerts": len(self.get_active_alerts()),
            "last_measurement": self.metrics_history[-1].timestamp.isoformat() if self.metrics_history else None,
        }

    def set_alert_thresholds(self, warning_threshold: float, critical_threshold: float) -> None:
        """
        Set alert thresholds.

        Args:
            warning_threshold: Warning threshold percentage
            critical_threshold: Critical threshold percentage
        """
        if warning_threshold >= critical_threshold:
            msg = "Warning threshold must be less than critical threshold"
            raise ValueError(msg)

        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

        logger.info(f"Alert thresholds updated: warning={warning_threshold}%, critical={critical_threshold}%")
