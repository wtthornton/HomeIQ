"""
Pattern Aggregate Retention Policies
Story AI5.9 - Data Retention Policies & Cleanup

Manages retention policies for Epic AI-5 pattern aggregates:
- pattern_aggregates_daily: 90 days
- pattern_aggregates_weekly: 365 days
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
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

    def __init__(self, influxdb_client=None, influxdb_org: str | None = None):
        """
        Initialize pattern aggregate retention manager.

        Args:
            influxdb_client: InfluxDBClient instance (not a DeleteApi -- this
                class calls ``.delete_api()`` on it).
            influxdb_org: Organization the buckets live in. Passed explicitly so
                the delete target is never inferred from ambient client state.
        """
        self.influxdb_client = influxdb_client
        self.influxdb_org = influxdb_org

        # Epic AI-5 retention policies
        self.retention_policies = {
            'pattern_aggregates_daily': RetentionConfig(
                bucket_name='pattern_aggregates_daily',
                retention_days=90,
                cleanup_enabled=True,
                description='Daily pattern aggregates - 90 day retention'
            ),
            'pattern_aggregates_weekly': RetentionConfig(
                bucket_name='pattern_aggregates_weekly',
                retention_days=365,
                cleanup_enabled=True,
                description='Weekly/monthly pattern aggregates - 365 day retention'
            )
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
        all_succeeded = True

        for policy_name, config in self.retention_policies.items():
            if not config.cleanup_enabled:
                logger.info(f"Skipping cleanup for {policy_name} (disabled)")
                continue

            try:
                result = await self._cleanup_bucket(config)
                results[policy_name] = result
                if not result.get('success', False):
                    all_succeeded = False
            except Exception as e:
                logger.error(f"Error cleaning up {policy_name}: {e}", exc_info=True)
                results[policy_name] = {
                    'success': False,
                    'error': str(e)
                }
                all_succeeded = False

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Pattern aggregate cleanup completed in {duration:.2f}s")

        return {
            'success': all_succeeded,
            'duration_seconds': duration,
            'results': results,
            'timestamp': datetime.now().isoformat()
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
                # A pass that deletes nothing has not succeeded. Reporting success
                # here is what let the 90/365-day policy look enforced while no
                # data was ever removed.
                logger.error(
                    "No InfluxDB client configured - cannot enforce retention for %s",
                    config.bucket_name,
                )
                return {
                    'success': False,
                    'records_deleted': 0,
                    'cutoff_date': cutoff_date.isoformat(),
                    'bucket': config.bucket_name,
                    'error': 'No InfluxDB client configured',
                }

            # Delete data older than cutoff_date using InfluxDB delete API
            logger.info(f"Deleting data older than {cutoff_date.isoformat()} from {config.bucket_name}")

            # InfluxDBClient has no .delete(); deletes go through delete_api().
            # DeleteApi.delete requires a predicate -- an empty one means "every
            # series in the range", which is the intent for a whole-bucket sweep.
            #
            # influxdb-client v2 is synchronous, so this HTTP call is offloaded
            # rather than run inline: a whole-bucket delete can take a long time
            # and would otherwise block the event loop for its duration. Same
            # pattern DataCompressionService uses for its blocking work.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                partial(
                    self.influxdb_client.delete_api().delete,
                    start='1970-01-01T00:00:00Z',
                    stop=cutoff_date.isoformat(),
                    predicate='',
                    bucket=config.bucket_name,
                    org=self.influxdb_org,
                ),
            )

            logger.info(f"Successfully deleted expired data from {config.bucket_name} before {cutoff_date.isoformat()}")

            return {
                'success': True,
                'records_deleted': None,  # InfluxDB delete API doesn't return record count
                'cutoff_date': cutoff_date.isoformat(),
                'bucket': config.bucket_name
            }

        except Exception as e:
            logger.error(f"Error cleaning up {config.bucket_name}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_retention_summary(self) -> dict[str, Any]:
        """
        Get summary of retention policies.

        Returns:
            Dict with retention policy summary
        """
        summary = {
            'policies': {},
            'total_buckets': len(self.retention_policies),
            'total_retention_days': sum(
                config.retention_days
                for config in self.retention_policies.values()
            )
        }

        for policy_name, config in self.retention_policies.items():
            summary['policies'][policy_name] = {
                'retention_days': config.retention_days,
                'enabled': config.cleanup_enabled,
                'description': config.description
            }

        return summary


async def run_pattern_aggregate_retention(
    influxdb_client=None,
    influxdb_org: str | None = None,
) -> dict[str, Any]:
    """
    Run pattern aggregate retention cleanup.

    Args:
        influxdb_client: InfluxDBClient instance
        influxdb_org: Organization the pattern-aggregate buckets live in

    Returns:
        Dict with cleanup results
    """
    manager = PatternAggregateRetention(
        influxdb_client=influxdb_client,
        influxdb_org=influxdb_org,
    )
    return await manager.run_cleanup()


if __name__ == "__main__":
    import asyncio

    async def main():
        results = await run_pattern_aggregate_retention()
        logger.info("Pattern Aggregate Retention Results:")
        logger.info("  Duration: %.2fs", results['duration_seconds'])
        for bucket, result in results['results'].items():
            bucket_status = 'OK' if result['success'] else 'FAIL'
            logger.info("  %s: %s", bucket, bucket_status)

    asyncio.run(main())
