"""
Energy-Event Correlation Service
Post-processes HA events and power data to find causality relationships
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

from aiohttp import web
from dotenv import load_dotenv

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import log_error_with_context, log_with_context, setup_logging

from .correlator import EnergyEventCorrelator
from .health_check import HealthCheckHandler
from .security import validate_bucket_name, validate_internal_request

load_dotenv()

logger = setup_logging("energy-correlator")

# Set logger in security module for error logging
from . import security as security_module
security_module.logger = logger


class EnergyCorrelatorService:
    """Main service for energy-event correlation"""

    def __init__(self):
        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')
        
        # Epic 48 Story 48.1: Validate bucket name on startup
        try:
            validate_bucket_name(self.influxdb_bucket)
        except ValueError as e:
            raise ValueError(f"Invalid InfluxDB bucket configuration: {e}")

        # Service configuration
        self.processing_interval = int(os.getenv('PROCESSING_INTERVAL', '60'))  # 1 minute
        self.lookback_minutes = int(os.getenv('LOOKBACK_MINUTES', '5'))  # Process last 5 minutes
        self.max_events_per_interval = int(os.getenv('MAX_EVENTS_PER_INTERVAL', '500'))
        self.max_retry_queue_size = int(os.getenv('MAX_RETRY_QUEUE_SIZE', '250'))
        self.retry_window_minutes = int(os.getenv('RETRY_WINDOW_MINUTES', str(self.lookback_minutes)))
        self.correlation_window_seconds = int(os.getenv('CORRELATION_WINDOW_SECONDS', '10'))
        self.power_lookup_padding_seconds = int(os.getenv('POWER_LOOKUP_PADDING_SECONDS', '30'))
        self.min_power_delta = float(os.getenv('MIN_POWER_DELTA', '10.0'))
        # Epic 48 Story 48.5: Make error retry interval configurable
        self.error_retry_interval = int(os.getenv('ERROR_RETRY_INTERVAL', '60'))  # Default 60 seconds

        # Components
        self.correlator = EnergyEventCorrelator(
            self.influxdb_url,
            self.influxdb_token,
            self.influxdb_org,
            self.influxdb_bucket,
            correlation_window_seconds=self.correlation_window_seconds,
            min_power_delta=self.min_power_delta,
            max_events_per_interval=self.max_events_per_interval,
            power_lookup_padding_seconds=self.power_lookup_padding_seconds,
            max_retry_queue_size=self.max_retry_queue_size,
            retry_window_minutes=self.retry_window_minutes
        )

        self.health_handler = HealthCheckHandler()

        # Validate configuration
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")
        
        # Epic 48 Story 48.1: Get allowed networks for internal request validation
        allowed_networks_env = os.getenv('ALLOWED_NETWORKS', '')
        self.allowed_networks = [
            net.strip() for net in allowed_networks_env.split(',') if net.strip()
        ] if allowed_networks_env else None

        logger.info(
            f"Service configured: interval={self.processing_interval}s, "
            f"lookback={self.lookback_minutes}m"
        )

    async def startup(self):
        """Initialize service"""
        logger.info("Initializing Energy Correlator Service...")

        try:
            await self.correlator.startup()
            logger.info("Energy Correlator Service initialized successfully")
        except Exception as e:
            log_error_with_context(
                logger,
                "Failed to initialize service",
                service="energy-correlator",
                error=str(e)
            )
            raise

    async def shutdown(self):
        """Cleanup"""
        logger.info("Shutting down Energy Correlator Service...")

        try:
            await self.correlator.shutdown()
            logger.info("Energy Correlator Service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def run_continuous(self):
        """Run continuous correlation processing"""

        log_with_context(
            logger, "INFO",
            f"Starting correlation loop (every {self.processing_interval}s)",
            service="energy-correlator",
            interval=self.processing_interval,
            lookback_minutes=self.lookback_minutes
        )

        while True:
            try:
                # Process events from last N minutes
                await self.correlator.process_recent_events(
                    lookback_minutes=self.lookback_minutes
                )

                # Update health check
                self.health_handler.last_successful_fetch = datetime.now(timezone.utc)
                self.health_handler.total_fetches += 1

                # Wait for next interval
                await asyncio.sleep(self.processing_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    "Error in correlation loop",
                    service="energy-correlator",
                    error=str(e)
                )
                self.health_handler.failed_fetches += 1

                # Epic 48 Story 48.5: Use configurable error retry interval
                await asyncio.sleep(self.error_retry_interval)


async def create_app(service: EnergyCorrelatorService):
    """Create web application"""
    app = web.Application()

    # Health check endpoint
    app.router.add_get('/health', service.health_handler.handle)

    # Statistics endpoint
    async def get_statistics(request):
        """Get correlation statistics"""
        stats = service.correlator.get_statistics()
        return web.json_response(stats)

    app.router.add_get('/statistics', get_statistics)

    # Reset statistics endpoint (Epic 48 Story 48.1: Internal network validation)
    async def reset_statistics(request):
        """Reset correlation statistics (requires internal network access)"""
        # Validate request is from internal network
        if not validate_internal_request(request, service.allowed_networks):
            logger.warning(
                f"Unauthorized reset attempt from {request.remote}",
                extra={"service": "energy-correlator", "endpoint": "/statistics/reset"}
            )
            return web.json_response(
                {"error": "Forbidden: This endpoint is only accessible from internal networks"},
                status=403
            )
        
        service.correlator.reset_statistics()
        return web.json_response({"message": "Statistics reset"})

    app.router.add_post('/statistics/reset', reset_statistics)

    return app


async def main():
    """Main entry point"""
    logger.info("Starting Energy Correlator Service...")

    service: EnergyCorrelatorService | None = None
    runner: web.AppRunner | None = None
    site: web.TCPSite | None = None

    try:
        # Create service
        service = EnergyCorrelatorService()
        await service.startup()

        # Create web app
        app = await create_app(service)
        runner = web.AppRunner(app)
        await runner.setup()

        # Start HTTP server
        port = int(os.getenv('SERVICE_PORT', '8017'))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()

        logger.info(f"Service running on port {port}")
        logger.info("Endpoints: /health, /statistics, /statistics/reset")

        # Run correlation loop
        await service.run_continuous()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        log_error_with_context(
            logger,
            "Fatal error in main",
            service="energy-correlator",
            error=str(e)
        )
        raise
    finally:
        if site:
            await site.stop()
        if runner:
            await runner.cleanup()
        if service:
            await service.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

