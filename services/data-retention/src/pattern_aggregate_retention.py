"""
Pattern Aggregate Retention Policies
Story AI5.9 - Data Retention Policies & Cleanup

Manages retention policies for Epic AI-5 pattern aggregates:
- pattern_aggregates_daily: 90 days
- pattern_aggregates_weekly: 365 days
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetentionConfig:
    """Retention configuration for a bucket"""
    bucket_name: str
    retention_days: int
    cleanup_enabled: bool = True
    description: str = ""


class PatternAggregateRetention:
    """Manage retention policies for pattern aggregates (Epic AI-5)"""

    def __init__(self, influxdb_client=None):
        """
        Initialize pattern aggregate retention manager.

        Args:
            influxdb_client: InfluxDB client instance
        """
        self.influxdb_client = influxdb_client

        # Epic AI-5 retention policies
        self.retention_policies = {
            "pattern_aggregates_daily": RetentionConfig(
                bucket_name="pattern_aggregates_daily",
                retention_days=90,
                cleanup_enabled=True,
                description="Daily pattern aggregates - 90 day retention",
            ),
            "pattern_aggregates_weekly": RetentionConfig(
                bucket_name="pattern_aggregates_weekly",
                retention_days=365,
                cleanup_enabled=True,
                description="Weekly/monthly pattern aggregates - 365 day retention",
            ),
        }

        logger.info("Pattern aggregate retention manager initialized")
        logger.info(f"Configured {len(self.retention_policies)} retention policies")

    async def run_cleanup(self) -> dict[str, Any]:
        """
        Run cleanup for all pattern aggregate buckets.

        Returns:
            Dict with cleanup results for each bucket
        """
        logger.info("Starting pattern aggregate retention cleanup...")

        results = {}
        start_time = datetime.now()

        for policy_name, config in self.retention_policies.items():
            if not config.cleanup_enabled:
                logger.info(f"Skipping cleanup for {policy_name} (disabled)")
                continue

            try:
                result = await self._cleanup_bucket(config)
                results[policy_name] = result
            except Exception as e:
                logger.error(f"Error cleaning up {policy_name}: {e}", exc_info=True)
                results[policy_name] = {
                    "success": False,
                    "error": str(e),
                }

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Pattern aggregate cleanup completed in {duration:.2f}s")

        return {
            "success": True,
            "duration_seconds": duration,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def _cleanup_bucket(self, config: RetentionConfig) -> dict[str, Any]:
        """
        Clean up expired data from a bucket.

        Args:
            config: Retention configuration

        Returns:
            Dict with cleanup results
        """
        logger.info(f"Cleaning up bucket: {config.bucket_name} (retention: {config.retention_days} days)")

        try:
            cutoff_date = datetime.now() - timedelta(days=config.retention_days)

            if not self.influxdb_client:
                # Mock implementation for testing
                logger.warning(f"Mock cleanup for {config.bucket_name} (no InfluxDB client)")
                return {
                    "success": True,
                    "records_deleted": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "note": "Mock operation - no InfluxDB client",
                }

            # In production, this would delete data older than cutoff_date
            # For safety, logging the operation rather than actual deletion
            logger.info(f"Would delete data older than {cutoff_date.isoformat()} from {config.bucket_name}")

            # Actual implementation would use InfluxDB delete API:
            # self.influxdb_client.delete(
            #     bucket=config.bucket_name,
            #     start='1970-01-01T00:00:00Z',
            #     stop=cutoff_date.isoformat()
            # )

            return {
                "success": True,
                "records_deleted": 0,  # Would be actual count in production
                "cutoff_date": cutoff_date.isoformat(),
                "note": "Dry run - actual deletion commented for safety",
            }

        except Exception as e:
            logger.error(f"Error cleaning up {config.bucket_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    def get_retention_summary(self) -> dict[str, Any]:
        """
        Get summary of retention policies.

        Returns:
            Dict with retention policy summary
        """
        summary = {
            "policies": {},
            "total_buckets": len(self.retention_policies),
            "total_retention_days": sum(
                config.retention_days
                for config in self.retention_policies.values()
            ),
        }

        for policy_name, config in self.retention_policies.items():
            summary["policies"][policy_name] = {
                "retention_days": config.retention_days,
                "enabled": config.cleanup_enabled,
                "description": config.description,
            }

        return summary


async def run_pattern_aggregate_retention(influxdb_client=None) -> dict[str, Any]:
    """
    Run pattern aggregate retention cleanup.

    Args:
        influxdb_client: InfluxDB client instance

    Returns:
        Dict with cleanup results
    """
    manager = PatternAggregateRetention(influxdb_client=influxdb_client)
    return await manager.run_cleanup()


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await run_pattern_aggregate_retention()
        print("Pattern Aggregate Retention Results:")
        print(f"  Duration: {results['duration_seconds']:.2f}s")
        for bucket, result in results["results"].items():
            print(f"  {bucket}: {'✅' if result['success'] else '❌'}")

# Run if executed directly
if __name__ == "__main__":
    asyncio.run(main())
