"""Unit tests for DataAPIService — Story 85.7

Tests service initialization, startup, and shutdown lifecycle.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDataAPIServiceInit:
    """Test DataAPIService constructor."""

    @patch("src._service.settings")
    def test_creates_components(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService
        svc = DataAPIService()

        assert svc.api_port == 8006
        assert svc.is_running is False
        assert svc.total_requests == 0
        assert svc.failed_requests == 0
        assert svc.job_scheduler is None

    @patch("src._service.settings")
    def test_runtime_state_defaults(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService
        svc = DataAPIService()

        assert svc.is_running is False
        assert svc.start_time is not None


class TestDataAPIServiceStartup:

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_startup_sets_running(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics:
            mock_alert.start = AsyncMock()
            mock_metrics.start = AsyncMock()

            svc = DataAPIService()
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.connect = AsyncMock(return_value=False)

            await svc.startup()
            assert svc.is_running is True

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_startup_handles_influxdb_error(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics:
            mock_alert.start = AsyncMock()
            mock_metrics.start = AsyncMock()

            svc = DataAPIService()
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.connect = AsyncMock(side_effect=Exception("connection refused"))

            # Should not raise
            await svc.startup()
            assert svc.is_running is True


    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_startup_successful_influxdb_connect(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics, \
             patch("src._service.get_sports_writer") as mock_sw, \
             patch("src._service.start_webhook_detector"):
            mock_alert.start = AsyncMock()
            mock_metrics.start = AsyncMock()
            mock_writer = AsyncMock()
            mock_sw.return_value = mock_writer

            svc = DataAPIService()
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.connect = AsyncMock(return_value=True)

            await svc.startup()
            assert svc.is_running is True
            mock_writer.connect.assert_called_once()

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_start_job_scheduler_success(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        svc = DataAPIService()
        mock_scheduler = AsyncMock()
        mock_scheduler.start = AsyncMock(return_value=True)

        with patch("src.jobs.scheduler.get_job_scheduler", return_value=mock_scheduler):
            await svc._start_job_scheduler()
            assert svc.job_scheduler is mock_scheduler

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_start_job_scheduler_exception(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        svc = DataAPIService()
        with patch("src.jobs.scheduler.get_job_scheduler", side_effect=Exception("init fail")):
            await svc._start_job_scheduler()
            # Should not raise


class TestDataAPIServiceShutdown:

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_shutdown_sets_not_running(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics, \
             patch("src._service.stop_webhook_detector"):
            mock_alert.stop = AsyncMock()
            mock_metrics.stop = AsyncMock()

            svc = DataAPIService()
            svc.is_running = True
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.close = AsyncMock()

            await svc.shutdown()
            assert svc.is_running is False

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_shutdown_stops_job_scheduler(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics, \
             patch("src._service.stop_webhook_detector"):
            mock_alert.stop = AsyncMock()
            mock_metrics.stop = AsyncMock()

            svc = DataAPIService()
            mock_scheduler = AsyncMock()
            svc.job_scheduler = mock_scheduler
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.close = AsyncMock()

            await svc.shutdown()
            mock_scheduler.stop.assert_called_once()

    @patch("src._service.settings")
    @pytest.mark.asyncio
    async def test_shutdown_handles_influxdb_close_error(self, mock_settings):
        mock_settings.service_port = 8006
        mock_settings.request_timeout = 30
        mock_settings.db_query_timeout = 10
        mock_settings.api_title = "Data API"
        mock_settings.api_version = "1.0.0"
        mock_settings.api_description = "Test"
        mock_settings.allow_anonymous = False
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.rate_limit_per_min = 100
        mock_settings.rate_limit_burst = 20
        mock_settings.api_key = "test-key"

        from src._service import DataAPIService

        with patch("src._service.alerting_service") as mock_alert, \
             patch("src._service.metrics_service") as mock_metrics, \
             patch("src._service.stop_webhook_detector"):
            mock_alert.stop = AsyncMock()
            mock_metrics.stop = AsyncMock()

            svc = DataAPIService()
            svc.influxdb_client = MagicMock()
            svc.influxdb_client.close = AsyncMock(side_effect=Exception("close error"))

            await svc.shutdown()
            assert svc.is_running is False
