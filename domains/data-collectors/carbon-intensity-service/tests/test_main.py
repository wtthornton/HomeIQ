"""
Tests for Carbon Intensity Service
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("influxdb_client_3", reason="influxdb_client_3 required by main")

from main import CarbonIntensityService

# --- Helpers ---

def _make_v3_response(current_moer=500.0, forecast_1h_moer=400.0, num_entries=13):
    """Build a WattTime v3 /forecast response with the given MOER values.

    entry[0]  = current value
    entry[12] = 1-hour forecast (5-min intervals, 12 per hour)
    Remaining entries are filled with *forecast_1h_moer*.
    """
    entries = [{"point_time": "2026-03-03T00:00:00Z", "value": current_moer}]
    for i in range(1, num_entries):
        val = forecast_1h_moer if i == 12 else current_moer
        entries.append({"point_time": f"2026-03-03T00:{i * 5:02d}:00Z", "value": val})
    return {
        "data": entries,
        "meta": {"signal_type": "co2_moer", "units": "lbs_co2_per_mwh", "region": "CAISO_NORTH"},
    }


# --- Fixtures ---

@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv('WATTTIME_API_TOKEN', 'test_token')
    monkeypatch.setenv('GRID_REGION', 'CAISO_NORTH')
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_influx_token')
    monkeypatch.setenv('INFLUXDB_URL', 'http://localhost:8086')


@pytest.fixture
def service(_mock_env):
    """Create service instance with mocked external clients (no real connections)."""
    svc = CarbonIntensityService()
    # Replace real clients with mocks to prevent network calls in tests
    svc.session = MagicMock()
    svc.influxdb_client = MagicMock()
    svc.credentials_configured = True
    return svc


# --- Initialization ---

@pytest.mark.asyncio
async def test_service_initialization(_mock_env):
    """Test service initializes correctly"""
    svc = CarbonIntensityService()

    assert svc.api_token == 'test_token'
    assert svc.region == 'CAISO_NORTH'
    assert svc.fetch_interval == 900
    assert svc.cached_data is None


@pytest.mark.asyncio
async def test_influxdb_url_preserved(_mock_env):
    """Test full InfluxDB URL is passed through to client"""
    svc = CarbonIntensityService()
    assert svc.influxdb_url == "http://localhost:8086"


@pytest.mark.asyncio
async def test_influxdb_bare_hostname_gets_scheme(monkeypatch):
    """Test bare hostname gets http:// scheme and default port"""
    monkeypatch.setenv('WATTTIME_API_TOKEN', 'test_token')
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_influx_token')
    monkeypatch.setenv('INFLUXDB_URL', 'influxdb')
    svc = CarbonIntensityService()
    assert svc.influxdb_url == "http://influxdb:8086"


@pytest.mark.asyncio
async def test_missing_influxdb_token_raises():
    """Test service raises ValueError when INFLUXDB_TOKEN is missing"""
    with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
        CarbonIntensityService()


@pytest.mark.asyncio
async def test_missing_watttime_credentials_enters_standby(monkeypatch):
    """Test service enters standby mode when WattTime credentials are missing"""
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_token')
    svc = CarbonIntensityService()
    assert svc.credentials_configured is False


@pytest.mark.asyncio
async def test_invalid_grid_region_raises(monkeypatch):
    """Test invalid GRID_REGION is rejected"""
    monkeypatch.setenv('WATTTIME_API_TOKEN', 'test_token')
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test_token')
    monkeypatch.setenv('GRID_REGION', 'INVALID;REGION')
    with pytest.raises(ValueError, match="Invalid GRID_REGION"):
        CarbonIntensityService()


# --- Fetch (v3 API format) ---

@pytest.mark.asyncio
async def test_fetch_carbon_intensity_success(service):
    """Test successful API fetch with v3 response format"""
    current_moer = 500.0
    forecast_1h_moer = 400.0
    mock_response = _make_v3_response(current_moer, forecast_1h_moer, num_entries=13)

    with patch.object(service.session, 'get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_resp.request_info = MagicMock()
        mock_resp.history = ()
        mock_get.return_value.__aenter__.return_value = mock_resp

        data = await service.fetch_carbon_intensity()

        assert data is not None
        assert data['carbon_intensity'] == pytest.approx(current_moer * 0.4536)
        assert data['carbon_intensity_raw_moer'] == current_moer
        assert 'renewable_percentage' not in data
        assert 'fossil_percentage' not in data
        assert data['forecast_1h'] == pytest.approx(forecast_1h_moer * 0.4536)
        assert service.cached_data == data
        assert service.health_handler.total_fetches == 1


@pytest.mark.asyncio
async def test_fetch_carbon_intensity_api_failure_returns_cache(service):
    """Test non-retryable API failure returns cached data"""
    service.cached_data = {
        'carbon_intensity': 200.0,
        'timestamp': datetime.now(UTC),
    }

    with patch.object(service.session, 'get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 400  # Non-retryable status — immediate failure
        mock_resp.request_info = MagicMock()
        mock_resp.history = ()
        mock_get.return_value.__aenter__.return_value = mock_resp

        data = await service.fetch_carbon_intensity()

        assert data == service.cached_data
        assert service.health_handler.failed_fetches == 1


@pytest.mark.asyncio
async def test_fetch_403_subscription_required(service):
    """Test 403 from WattTime returns None (subscription-restricted endpoint)"""
    with patch.object(service.session, 'get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 403
        mock_resp.request_info = MagicMock()
        mock_resp.history = ()
        mock_get.return_value.__aenter__.return_value = mock_resp

        data = await service.fetch_carbon_intensity()

        # 403 returns None via _dispatch, then cache fallback (None since no cache)
        assert data is None
        assert service.health_handler.failed_fetches == 1


# --- InfluxDB Storage ---

@pytest.mark.asyncio
async def test_store_in_influxdb(service):
    """Test data storage in InfluxDB"""
    test_data = {
        'carbon_intensity': 226.8,
        'carbon_intensity_raw_moer': 500.0,
        'forecast_1h': 181.44,
        'forecast_24h': 181.44,
        'timestamp': datetime.now(UTC),
    }

    with patch.object(service.influxdb_client, 'write') as mock_write:
        await service.store_in_influxdb(test_data)

        assert mock_write.called
        call_args = mock_write.call_args[0][0]
        assert call_args._name == "carbon_intensity"


# --- Cache ---

@pytest.mark.asyncio
async def test_cache_functionality(service):
    """Test caching behavior — second fetch within TTL skips API call"""
    mock_response = _make_v3_response(500.0, 400.0, num_entries=13)

    with patch.object(service.session, 'get') as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_resp.request_info = MagicMock()
        mock_resp.history = ()
        mock_get.return_value.__aenter__.return_value = mock_resp

        # First fetch — hits API
        data1 = await service.fetch_carbon_intensity()
        assert service.cached_data == data1
        assert service.cached_data['carbon_intensity'] == pytest.approx(500.0 * 0.4536)
        assert service.last_fetch_time is not None

        # Second fetch — should return cache without calling API again
        data2 = await service.fetch_carbon_intensity()
        assert data2 == data1
        assert mock_get.call_count == 1  # Only one API call


@pytest.mark.asyncio
async def test_standby_mode_skips_fetch(service):
    """Test that standby mode (no credentials) skips fetch silently"""
    service.credentials_configured = False

    data = await service.fetch_carbon_intensity()

    assert data is None
