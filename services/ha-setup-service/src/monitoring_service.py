"""
Continuous Health Monitoring Service

Context7 Best Practices Applied:
- Background task scheduling with asyncio
- Proper exception handling
- Graceful shutdown handling
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .health_service import HealthMonitoringService
from .integration_checker import IntegrationHealthChecker
from .models import EnvironmentHealth
from .schemas import HealthStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class ContinuousHealthMonitor:
    """
    Background service for continuous health monitoring
    
    Features:
    - Scheduled health checks every 60 seconds
    - Integration checks every 5 minutes
    - Automatic alerting for critical issues
    - Health trend analysis
    """

    def __init__(
        self,
        health_service: HealthMonitoringService,
        integration_checker: IntegrationHealthChecker
    ):
        self.health_service = health_service
        self.integration_checker = integration_checker
        self.running = False
        self.task: asyncio.Task | None = None

        # Monitoring intervals
        self.health_check_interval = settings.health_check_interval  # 60 seconds
        self.integration_check_interval = settings.integration_check_interval  # 300 seconds

        # Last check timestamps
        self.last_health_check: datetime | None = None
        self.last_integration_check: datetime | None = None

    async def start(self):
        """Start continuous monitoring"""
        if self.running:
            logger.warning("Continuous monitoring already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Continuous health monitoring started")

    async def stop(self):
        """Stop continuous monitoring"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Continuous health monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting continuous health monitoring loop")

        while self.running:
            try:
                current_time = datetime.now(timezone.utc)

                # Check if health check is due
                if self._is_health_check_due(current_time):
                    await self._run_health_check()
                    self.last_health_check = current_time

                # Check if integration check is due
                if self._is_integration_check_due(current_time):
                    await self._run_integration_check()
                    self.last_integration_check = current_time

                # Sleep for 10 seconds before next iteration
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error("Error in monitoring loop", exc_info=e)
                # Continue running even if an error occurs
                await asyncio.sleep(10)

    def _is_health_check_due(self, current_time: datetime) -> bool:
        """Check if health check should run"""
        if not self.last_health_check:
            return True

        elapsed = (current_time - self.last_health_check).total_seconds()
        return elapsed >= self.health_check_interval

    def _is_integration_check_due(self, current_time: datetime) -> bool:
        """Check if integration check should run"""
        if not self.last_integration_check:
            return True

        elapsed = (current_time - self.last_integration_check).total_seconds()
        return elapsed >= self.integration_check_interval

    async def _run_health_check(self):
        """Run scheduled health check"""
        try:
            # Import here to avoid circular dependency
            from .database import async_session_maker

            async with async_session_maker() as db:
                health_result = await self.health_service.check_environment_health(db)

                # Check for critical issues and alert
                if health_result.ha_status == HealthStatus.CRITICAL:
                    await self._send_alert(
                        "CRITICAL: Environment Health Critical",
                        f"Health score: {health_result.health_score}/100. "
                        f"Issues: {', '.join(health_result.issues_detected)}"
                    )

                logger.info(f"Health check complete - Score: {health_result.health_score}/100")

        except Exception as e:
            logger.error("Error running health check", exc_info=e)

    async def _run_integration_check(self):
        """Run scheduled integration check"""
        try:
            from .database import async_session_maker

            async with async_session_maker() as db:
                check_results = await self.integration_checker.check_all_integrations()

                # Store results
                from .models import IntegrationHealth as IntegrationHealthModel

                for result in check_results:
                    integration_health = IntegrationHealthModel(
                        integration_name=result.integration_name,
                        integration_type=result.integration_type,
                        status=result.status.value,
                        is_configured=result.is_configured,
                        is_connected=result.is_connected,
                        error_message=result.error_message,
                        last_check=result.last_check,
                        check_details=result.check_details
                    )
                    db.add(integration_health)

                await db.commit()

                # Check for critical integration issues
                error_integrations = [r for r in check_results if r.status.value == 'error']
                if error_integrations:
                    await self._send_alert(
                        "WARNING: Integration Issues Detected",
                        f"Integrations with errors: {', '.join([r.integration_name for r in error_integrations])}"
                    )

                logger.info(
                    f"Integration check complete - "
                    f"{sum(1 for r in check_results if r.status.value == 'healthy')}/{len(check_results)} healthy"
                )

        except Exception as e:
            logger.error("Error running integration check", exc_info=e)

    async def _send_alert(self, title: str, message: str):
        """
        Send alert for critical issues
        
        Placeholder for future alerting implementation
        Currently logs to console
        """
        logger.critical(f"ALERT: {title} - {message}")

        # Future: Send to alert_manager, email, Slack, etc.

    async def get_health_trends(
        self,
        db: AsyncSession,
        hours: int = 24
    ) -> dict:
        """
        Get health trends over specified time period
        
        Args:
            db: Database session
            hours: Number of hours to analyze
            
        Returns:
            Trend data including average score, score changes, issue frequency
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Get health metrics from database
            stmt = select(EnvironmentHealth).where(
                EnvironmentHealth.timestamp >= cutoff_time
            ).order_by(EnvironmentHealth.timestamp.asc())

            result = await db.execute(stmt)
            health_metrics = result.scalars().all()

            if not health_metrics:
                return {
                    "period_hours": hours,
                    "data_points": 0,
                    "average_score": 0,
                    "min_score": 0,
                    "max_score": 0,
                    "trend": "no_data"
                }

            # Calculate statistics
            scores = [m.health_score for m in health_metrics]
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)

            # Determine trend (comparing first half to second half)
            mid_point = len(scores) // 2
            if mid_point > 0:
                first_half_avg = sum(scores[:mid_point]) / mid_point
                second_half_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)

                if second_half_avg > first_half_avg + 5:
                    trend = "improving"
                elif second_half_avg < first_half_avg - 5:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            return {
                "period_hours": hours,
                "data_points": len(health_metrics),
                "average_score": round(avg_score, 1),
                "min_score": min_score,
                "max_score": max_score,
                "trend": trend,
                "current_score": scores[-1] if scores else 0,
                "score_history": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "score": m.health_score,
                        "status": m.ha_status
                    }
                    for m in health_metrics
                ]
            }

        except Exception as e:
            logger.error("Error calculating health trends", exc_info=e)
            return {
                "period_hours": hours,
                "data_points": 0,
                "error": str(e)
            }

