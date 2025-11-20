"""
Simple tests for refactored stats endpoints
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.monitoring import StatsEndpoints


def test_stats_endpoints_initialization():
    """Test StatsEndpoints can be initialized"""
    stats = StatsEndpoints()

    assert stats is not None
    assert stats.influxdb_client is not None
    assert hasattr(stats, 'router')
    assert hasattr(stats, 'service_urls')


def test_calculate_alerts_no_errors():
    """Test alert calculation with no errors"""
    stats = StatsEndpoints()

    service_metrics = {
        "websocket-ingestion": {
            "success_rate": 100,
            "processing_time_ms": 50
        }
    }

    error_stats = {
        "error_rate_percent": 0
    }

    alerts = stats._calculate_alerts(service_metrics, error_stats)

    assert isinstance(alerts, list)
    assert len(alerts) == 0  # No alerts for good metrics


def test_calculate_alerts_high_error_rate():
    """Test alert calculation with high error rate"""
    stats = StatsEndpoints()

    service_metrics = {}
    error_stats = {
        "error_rate_percent": 10  # High error rate
    }

    alerts = stats._calculate_alerts(service_metrics, error_stats)

    assert isinstance(alerts, list)
    assert len(alerts) > 0
    assert alerts[0]["level"] == "error"
    assert "error rate" in alerts[0]["message"].lower()


def test_calculate_alerts_elevated_error_rate():
    """Test alert calculation with elevated error rate"""
    stats = StatsEndpoints()

    service_metrics = {}
    error_stats = {
        "error_rate_percent": 3  # Elevated but not critical
    }

    alerts = stats._calculate_alerts(service_metrics, error_stats)

    assert isinstance(alerts, list)
    assert len(alerts) > 0
    assert alerts[0]["level"] == "warning"
    assert "elevated" in alerts[0]["message"].lower()


def test_calculate_alerts_low_success_rate():
    """Test alert calculation with low success rate"""
    stats = StatsEndpoints()

    service_metrics = {
        "test-service": {
            "success_rate": 85,  # Below 90%
            "processing_time_ms": 50
        }
    }

    error_stats = {
        "error_rate_percent": 0
    }

    alerts = stats._calculate_alerts(service_metrics, error_stats)

    assert isinstance(alerts, list)
    assert len(alerts) > 0

    # Find the alert for low success rate
    low_success_alert = [a for a in alerts if "success rate" in a["message"].lower()][0]
    assert low_success_alert["level"] == "error"
    assert low_success_alert["service"] == "test-service"


def test_calculate_alerts_slow_processing():
    """Test alert calculation with slow processing"""
    stats = StatsEndpoints()

    service_metrics = {
        "slow-service": {
            "success_rate": 100,
            "processing_time_ms": 1500  # > 1000ms
        }
    }

    error_stats = {
        "error_rate_percent": 0
    }

    alerts = stats._calculate_alerts(service_metrics, error_stats)

    assert isinstance(alerts, list)
    assert len(alerts) > 0

    # Find the alert for slow processing
    slow_alert = [a for a in alerts if "processing" in a["message"].lower()][0]
    assert slow_alert["level"] == "warning"
    assert slow_alert["service"] == "slow-service"


@pytest.mark.asyncio
async def test_initialize_influxdb():
    """Test InfluxDB initialization"""
    stats = StatsEndpoints()

    # Mock the influxdb_client.connect to return False
    stats.influxdb_client.connect = AsyncMock(return_value=False)

    await stats.initialize()

    # Should disable InfluxDB on connection failure
    assert stats.use_influxdb is False


@pytest.mark.asyncio
async def test_close_influxdb():
    """Test InfluxDB close"""
    stats = StatsEndpoints()

    # Mock the close method
    stats.influxdb_client.close = AsyncMock()

    await stats.close()

    # Verify close was called
    stats.influxdb_client.close.assert_called_once()


def test_feature_flag_from_env():
    """Test feature flag reads from environment"""
    with patch.dict(os.environ, {'USE_INFLUXDB_STATS': 'false'}):
        stats = StatsEndpoints()
        assert stats.use_influxdb is False

    with patch.dict(os.environ, {'USE_INFLUXDB_STATS': 'true'}):
        stats = StatsEndpoints()
        assert stats.use_influxdb is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

