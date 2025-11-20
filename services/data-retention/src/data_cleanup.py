"""Data cleanup and expiration service."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .retention_policy import RetentionPolicy, RetentionPolicyManager

logger = logging.getLogger(__name__)

@dataclass
class CleanupResult:
    """Result of a data cleanup operation."""

    policy_name: str
    records_deleted: int
    records_processed: int
    cleanup_duration: float
    success: bool
    error_message: str | None = None
    cleanup_timestamp: datetime = None

    def __post_init__(self):
        if self.cleanup_timestamp is None:
            self.cleanup_timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "policy_name": self.policy_name,
            "records_deleted": self.records_deleted,
            "records_processed": self.records_processed,
            "cleanup_duration": self.cleanup_duration,
            "success": self.success,
            "error_message": self.error_message,
            "cleanup_timestamp": self.cleanup_timestamp.isoformat()
        }

class DataCleanupService:
    """Service for cleaning up expired data."""

    def __init__(self, influxdb_client=None):
        """
        Initialize data cleanup service.
        
        Args:
            influxdb_client: InfluxDB client for data operations
        """
        self.influxdb_client = influxdb_client
        self.policy_manager = RetentionPolicyManager()
        self.cleanup_history: list[CleanupResult] = []
        self.is_running = False
        self.cleanup_task: asyncio.Task | None = None

        logger.info("Data cleanup service initialized")

    async def start(self) -> None:
        """Start the cleanup service."""
        if self.is_running:
            logger.warning("Cleanup service is already running")
            return

        self.is_running = True
        logger.info("Data cleanup service started")

    async def stop(self) -> None:
        """Stop the cleanup service."""
        if not self.is_running:
            return

        self.is_running = False

        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Data cleanup service stopped")

    async def run_cleanup(self, policy_name: str | None = None) -> list[CleanupResult]:
        """
        Run data cleanup for specified policy or all enabled policies.
        
        Args:
            policy_name: Specific policy to run cleanup for (None for all)
            
        Returns:
            List of cleanup results
        """
        results = []

        if policy_name:
            policy = self.policy_manager.get_policy(policy_name)
            if not policy:
                raise ValueError(f"Policy '{policy_name}' not found")
            policies = [policy] if policy.enabled else []
        else:
            policies = self.policy_manager.get_enabled_policies()

        for policy in policies:
            try:
                result = await self._cleanup_policy(policy)
                results.append(result)
                self.cleanup_history.append(result)

                logger.info(f"Cleanup completed for policy '{policy.name}': "
                          f"{result.records_deleted} records deleted")

            except Exception as e:
                logger.error(f"Cleanup failed for policy '{policy.name}': {e}")
                error_result = CleanupResult(
                    policy_name=policy.name,
                    records_deleted=0,
                    records_processed=0,
                    cleanup_duration=0.0,
                    success=False,
                    error_message=str(e)
                )
                results.append(error_result)
                self.cleanup_history.append(error_result)

        return results

    async def _cleanup_policy(self, policy: RetentionPolicy) -> CleanupResult:
        """
        Clean up data for a specific policy.
        
        Args:
            policy: Retention policy to apply
            
        Returns:
            CleanupResult: Result of the cleanup operation
        """
        start_time = datetime.utcnow()

        try:
            # Calculate expiration date
            expiration_date = policy.get_expiration_date()

            # Get records to delete
            records_to_delete = await self._get_expired_records(expiration_date)
            records_processed = len(records_to_delete)

            # Delete expired records
            records_deleted = await self._delete_expired_records(records_to_delete)

            cleanup_duration = (datetime.utcnow() - start_time).total_seconds()

            return CleanupResult(
                policy_name=policy.name,
                records_deleted=records_deleted,
                records_processed=records_processed,
                cleanup_duration=cleanup_duration,
                success=True
            )

        except Exception as e:
            cleanup_duration = (datetime.utcnow() - start_time).total_seconds()
            return CleanupResult(
                policy_name=policy.name,
                records_deleted=0,
                records_processed=0,
                cleanup_duration=cleanup_duration,
                success=False,
                error_message=str(e)
            )

    async def _get_expired_records(self, expiration_date: datetime) -> list[dict[str, Any]]:
        """
        Get records that have expired.
        
        Args:
            expiration_date: Date before which records are considered expired
            
        Returns:
            List of expired records
        """
        if not self.influxdb_client:
            # Mock implementation for testing
            return [
                {"id": f"record_{i}", "timestamp": (expiration_date - timedelta(days=i)).isoformat()}
                for i in range(1, 11)
            ]

        try:
            # Query InfluxDB for expired records
            query = f"""
            from(bucket: "home-assistant-events")
                |> range(start: 1970-01-01T00:00:00Z, stop: {expiration_date.isoformat()}Z)
                |> limit(n: 10000)
            """

            result = await self.influxdb_client.query(query)
            records = []

            for table in result:
                for record in table.records:
                    records.append({
                        "id": record.get_field(),
                        "timestamp": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "tags": record.values
                    })

            return records

        except Exception as e:
            logger.error(f"Failed to get expired records: {e}")
            return []

    async def _delete_expired_records(self, records: list[dict[str, Any]]) -> int:
        """
        Delete expired records.
        
        Args:
            records: List of records to delete
            
        Returns:
            Number of records deleted
        """
        if not self.influxdb_client:
            # Mock implementation for testing
            return len(records)

        try:
            deleted_count = 0

            for record in records:
                try:
                    # Delete record from InfluxDB
                    await self.influxdb_client.delete(
                        bucket="home-assistant-events",
                        start=record["timestamp"],
                        stop=record["timestamp"],
                        predicate=f'_measurement="{record["measurement"]}"'
                    )
                    deleted_count += 1

                except Exception as e:
                    logger.warning(f"Failed to delete record {record['id']}: {e}")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete expired records: {e}")
            return 0

    async def schedule_cleanup(self, interval_hours: int = 24) -> None:
        """
        Schedule periodic cleanup operations.
        
        Args:
            interval_hours: Interval between cleanup runs in hours
        """
        if self.cleanup_task and not self.cleanup_task.done():
            logger.warning("Cleanup task is already running")
            return

        async def cleanup_loop():
            while self.is_running:
                try:
                    logger.info("Starting scheduled cleanup")
                    results = await self.run_cleanup()

                    total_deleted = sum(result.records_deleted for result in results)
                    logger.info(f"Scheduled cleanup completed: {total_deleted} records deleted")

                except Exception as e:
                    logger.error(f"Scheduled cleanup failed: {e}")

                # Wait for next cleanup
                await asyncio.sleep(interval_hours * 3600)

        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Scheduled cleanup every {interval_hours} hours")

    def get_cleanup_history(self, limit: int = 100) -> list[CleanupResult]:
        """
        Get cleanup history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of cleanup results
        """
        return self.cleanup_history[-limit:] if self.cleanup_history else []

    def get_cleanup_statistics(self) -> dict[str, Any]:
        """
        Get cleanup statistics.
        
        Returns:
            Dictionary containing cleanup statistics
        """
        if not self.cleanup_history:
            return {
                "total_cleanups": 0,
                "total_records_deleted": 0,
                "total_records_processed": 0,
                "average_cleanup_duration": 0.0,
                "success_rate": 0.0,
                "last_cleanup": None
            }

        total_cleanups = len(self.cleanup_history)
        total_deleted = sum(result.records_deleted for result in self.cleanup_history)
        total_processed = sum(result.records_processed for result in self.cleanup_history)
        total_duration = sum(result.cleanup_duration for result in self.cleanup_history)
        successful_cleanups = sum(1 for result in self.cleanup_history if result.success)

        return {
            "total_cleanups": total_cleanups,
            "total_records_deleted": total_deleted,
            "total_records_processed": total_processed,
            "average_cleanup_duration": total_duration / total_cleanups if total_cleanups > 0 else 0.0,
            "success_rate": successful_cleanups / total_cleanups if total_cleanups > 0 else 0.0,
            "last_cleanup": self.cleanup_history[-1].cleanup_timestamp.isoformat() if self.cleanup_history else None
        }

    def get_policy_manager(self) -> RetentionPolicyManager:
        """
        Get the retention policy manager.
        
        Returns:
            RetentionPolicyManager instance
        """
        return self.policy_manager
