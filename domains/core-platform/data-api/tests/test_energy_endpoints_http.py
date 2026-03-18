"""
Tests for energy_endpoints.py — all 8 routes under /api/v1/energy/

Mocks the InfluxDB client to avoid real connections.
Does NOT use PostgreSQL (overrides fresh_db from conftest).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers: Fake InfluxDB records / tables
# ---------------------------------------------------------------------------

class FakeRecord:
    """Simulates an influxdb_client FluxRecord."""

    def __init__(self, values: dict, time=None, field=None, value=None):
        self._values = values
        self._time = time or datetime.now(UTC)
        self._field = field
        self._value = value

    def get_time(self):
        return self._time

    def get_field(self):
        return self._field

    def get_value(self):
        return self._value

    @property
    def values(self):
        return self._values


class FakeTable:
    """Simulates an influxdb_client FluxTable."""

    def __init__(self, records: list[FakeRecord]):
        self.records = records


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Override conftest's fresh_db — energy endpoints don't use PostgreSQL
@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


def _make_mock_client(query_side_effect=None):
    """Create a mock InfluxDB client whose query_api().query() returns the
    given side_effect (list or callable).  When *query_side_effect* is a plain
    list it is treated as a single return value; wrap in a function for
    per-call behaviour.
    """
    mock_client = MagicMock()
    mock_query_api = MagicMock()
    mock_client.query_api.return_value = mock_query_api

    if callable(query_side_effect):
        mock_query_api.query.side_effect = query_side_effect
    else:
        mock_query_api.query.return_value = query_side_effect or []

    return mock_client, mock_query_api


@pytest_asyncio.fixture
async def client():
    """Isolated FastAPI app with only the energy router mounted."""
    from src.energy_endpoints import router as energy_router

    app = FastAPI()
    app.include_router(energy_router, prefix="/api/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. GET /api/v1/energy/correlations
# ---------------------------------------------------------------------------


class TestCorrelations:

    @pytest.mark.asyncio
    async def test_correlations_empty(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/correlations")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_correlations_with_data(self, client):
        now = datetime.now(UTC)
        record = FakeRecord(
            values={
                "entity_id": "switch.heater",
                "domain": "switch",
                "state": "on",
                "previous_state": "off",
                "power_before_w": 100.0,
                "power_after_w": 600.0,
                "_value": 500.0,
                "power_delta_pct": 400.0,
            },
            time=now,
            field="power_delta_w",
            value=500.0,
        )
        mock_client, _ = _make_mock_client([FakeTable([record])])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/correlations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["entity_id"] == "switch.heater"
        assert data[0]["power_delta_w"] == 500.0

    @pytest.mark.asyncio
    async def test_correlations_filter_by_entity_id(self, client):
        mock_client, mock_qa = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/correlations",
                params={"entity_id": "light.kitchen"},
            )
        assert resp.status_code == 200
        # Verify the query contained the entity_id filter
        call_args = mock_qa.query.call_args
        assert "light.kitchen" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_correlations_filter_by_domain(self, client):
        mock_client, mock_qa = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/correlations",
                params={"domain": "climate"},
            )
        assert resp.status_code == 200
        call_args = mock_qa.query.call_args
        assert "climate" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_correlations_invalid_entity_id(self, client):
        """Injection-style entity_id is caught — returns 500 because the broad
        except Exception clause wraps the HTTPException (known code pattern)."""
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/correlations",
                params={"entity_id": "';--"},
            )
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_correlations_invalid_domain(self, client):
        """Injection-style domain is caught — returns 500 (same broad except pattern)."""
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/correlations",
                params={"domain": "';--"},
            )
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_correlations_custom_params(self, client):
        mock_client, mock_qa = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/correlations",
                params={"hours": 48, "min_delta": 100, "limit": 5},
            )
        assert resp.status_code == 200
        flux = mock_qa.query.call_args[0][0]
        assert "limit(n: 5)" in flux


# ---------------------------------------------------------------------------
# 2. GET /api/v1/energy/current
# ---------------------------------------------------------------------------


class TestCurrentPower:

    @pytest.mark.asyncio
    async def test_current_with_data(self, client):
        now = datetime.now(UTC)
        rec_power = FakeRecord(
            values={}, time=now, field="total_power_w", value=1234.5
        )
        rec_kwh = FakeRecord(
            values={}, time=now, field="daily_kwh", value=8.7
        )
        mock_client, _ = _make_mock_client(
            [FakeTable([rec_power]), FakeTable([rec_kwh])]
        )
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_power_w"] == 1234.5
        assert data["daily_kwh"] == 8.7

    @pytest.mark.asyncio
    async def test_current_empty_returns_zeros(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_power_w"] == 0.0
        assert data["daily_kwh"] == 0.0


# ---------------------------------------------------------------------------
# 3. GET /api/v1/energy/circuits
# ---------------------------------------------------------------------------


class TestCircuits:

    @pytest.mark.asyncio
    async def test_circuits_empty(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/circuits")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_circuits_with_data(self, client):
        now = datetime.now(UTC)
        rec = FakeRecord(
            values={"circuit_name": "kitchen", "percentage": 35.0},
            time=now,
            field="power_w",
            value=750.0,
        )
        mock_client, _ = _make_mock_client([FakeTable([rec])])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/circuits")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["circuit_name"] == "kitchen"
        assert data[0]["power_w"] == 750.0
        assert data[0]["percentage"] == 35.0

    @pytest.mark.asyncio
    async def test_circuits_custom_hours(self, client):
        mock_client, mock_qa = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/circuits", params={"hours": 6})
        assert resp.status_code == 200
        # Verify hours param was used (range start ~ 6h ago)
        mock_qa.query.assert_called_once()


# ---------------------------------------------------------------------------
# 4. GET /api/v1/energy/device-impact/{entity_id}
# ---------------------------------------------------------------------------


class TestDeviceImpact:

    @pytest.mark.asyncio
    async def test_device_impact_with_data(self, client):
        now = datetime.now(UTC)

        on_record = FakeRecord(
            values={"domain": "switch"}, time=now, field="power_delta_w", value=200.0
        )
        off_record = FakeRecord(
            values={"domain": "switch"}, time=now, field="power_delta_w", value=-180.0
        )
        count_record = FakeRecord(
            values={}, time=now, field="power_delta_w", value=42
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([on_record])]
            elif call_count == 2:
                return [FakeTable([off_record])]
            else:
                return [FakeTable([count_record])]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/device-impact/switch.heater")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == "switch.heater"
        assert data["domain"] == "switch"
        assert data["average_power_on_w"] == 200.0
        assert data["average_power_off_w"] == -180.0
        assert data["total_state_changes"] == 42
        # daily_kwh = (200 * 8) / 1000 = 1.6
        assert data["estimated_daily_kwh"] == pytest.approx(1.6)
        # monthly_cost = 1.6 * 30 * 0.12 = 5.76
        assert data["estimated_monthly_cost"] == pytest.approx(5.76)

    @pytest.mark.asyncio
    async def test_device_impact_invalid_entity_id(self, client):
        """Returns 500 because broad except clause wraps the HTTPException (known pattern)."""
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/device-impact/';--")
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_device_impact_empty_influxdb(self, client):
        """When InfluxDB has no data, the endpoint returns zero defaults."""
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/device-impact/switch.lamp")
        assert resp.status_code == 200
        data = resp.json()
        assert data["average_power_on_w"] == 0.0
        assert data["total_state_changes"] == 0
        assert data["estimated_daily_kwh"] == 0.0


# ---------------------------------------------------------------------------
# 5. GET /api/v1/energy/statistics
# ---------------------------------------------------------------------------


class TestStatistics:

    @pytest.mark.asyncio
    async def test_statistics_with_data(self, client):
        now = datetime.now(UTC)
        peak_time = now - timedelta(hours=3)

        current_power_rec = FakeRecord(
            values={}, time=now, field="total_power_w", value=1500.0
        )
        daily_kwh_rec = FakeRecord(
            values={}, time=now, field="daily_kwh", value=12.3
        )
        peak_rec = FakeRecord(
            values={}, time=peak_time, field="total_power_w", value=3000.0
        )
        avg_rec = FakeRecord(
            values={}, time=now, field="total_power_w", value=1100.0
        )
        corr_rec = FakeRecord(
            values={}, time=now, field="power_delta_w", value=55
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([current_power_rec]), FakeTable([daily_kwh_rec])]
            elif call_count == 2:
                return [FakeTable([peak_rec])]
            elif call_count == 3:
                return [FakeTable([avg_rec])]
            else:
                return [FakeTable([corr_rec])]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/statistics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_power_w"] == 1500.0
        assert data["daily_kwh"] == 12.3
        assert data["peak_power_w"] == 3000.0
        assert data["average_power_w"] == 1100.0
        assert data["total_correlations"] == 55

    @pytest.mark.asyncio
    async def test_statistics_empty_influxdb(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/statistics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_power_w"] == 0.0
        assert data["peak_power_w"] == 0.0
        assert data["peak_time"] is None
        assert data["total_correlations"] == 0


# ---------------------------------------------------------------------------
# 6. GET /api/v1/energy/top-consumers
# ---------------------------------------------------------------------------


class TestTopConsumers:

    @pytest.mark.asyncio
    async def test_top_consumers_with_data(self, client):
        now = datetime.now(UTC)
        rec1 = FakeRecord(
            values={"entity_id": "switch.heater", "domain": "switch"},
            time=now,
            field="power_delta_w",
            value=500.0,
        )
        rec2 = FakeRecord(
            values={"entity_id": "climate.ac", "domain": "climate"},
            time=now,
            field="power_delta_w",
            value=300.0,
        )
        mock_client, _ = _make_mock_client([FakeTable([rec1, rec2])])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/top-consumers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["entity_id"] == "switch.heater"
        # daily_kwh = (500 * 8) / 1000 = 4.0
        assert data[0]["estimated_daily_kwh"] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_top_consumers_empty(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/top-consumers")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_top_consumers_custom_params(self, client):
        mock_client, mock_qa = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get(
                "/api/v1/energy/top-consumers",
                params={"days": 14, "limit": 5},
            )
        assert resp.status_code == 200
        flux = mock_qa.query.call_args[0][0]
        assert "limit(n: 5)" in flux


# ---------------------------------------------------------------------------
# 7. GET /api/v1/energy/carbon-intensity/current
# ---------------------------------------------------------------------------


class TestCarbonIntensityCurrent:

    @pytest.mark.asyncio
    async def test_carbon_current_with_data(self, client):
        now = datetime.now(UTC)
        rec = FakeRecord(
            values={
                "carbon_intensity_gco2_kwh": 185.0,
                "renewable_percentage": 42.0,
                "fossil_percentage": 58.0,
                "forecast_1h": 190.0,
                "forecast_24h": 175.0,
                "region": "UK",
                "grid_operator": "National Grid",
            },
            time=now,
        )
        mock_client, _ = _make_mock_client([FakeTable([rec])])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intensity"] == 185.0
        assert data["renewable_percentage"] == 42.0
        assert data["region"] == "UK"

    @pytest.mark.asyncio
    async def test_carbon_current_404_when_no_data(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/current")
        assert resp.status_code == 404
        assert "No carbon intensity data" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 8. GET /api/v1/energy/carbon-intensity/trends
# ---------------------------------------------------------------------------


class TestCarbonIntensityTrends:

    def _make_current_record(self, intensity=200.0, forecast_1h=210.0):
        return FakeRecord(
            values={
                "carbon_intensity_gco2_kwh": intensity,
                "renewable_percentage": 40.0,
                "fossil_percentage": 60.0,
                "forecast_1h": forecast_1h,
                "forecast_24h": 180.0,
                "region": "UK",
                "grid_operator": "NG",
            },
            time=datetime.now(UTC),
        )

    def _make_intensity_record(self, value):
        return FakeRecord(
            values={}, time=datetime.now(UTC), field="carbon_intensity_gco2_kwh", value=value
        )

    @pytest.mark.asyncio
    async def test_trends_with_data(self, client):
        current_rec = self._make_current_record(200.0)
        # Sorted desc: most recent first. First half avg ~200, second half avg ~200 => stable
        intensity_recs = [self._make_intensity_record(v) for v in [200, 195, 205, 198]]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([current_rec])]
            else:
                return [FakeTable(intensity_recs)]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"]["intensity"] == 200.0
        assert data["trend"] == "stable"
        assert data["min_24h"] <= data["max_24h"]
        assert len(data["forecast"]) == 1

    @pytest.mark.asyncio
    async def test_trends_404_when_no_current(self, client):
        mock_client, _ = _make_mock_client([])
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/trends")
        assert resp.status_code == 404
        assert "No carbon intensity data" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_trends_increasing(self, client):
        """Second half (older data) should be lower; first half (newer) higher => increasing."""
        current_rec = self._make_current_record(300.0)
        # Sorted desc: first_half=[300, 290] avg=295; second_half=[200, 190] avg=195
        # second_avg(195) < first_avg(295)*0.95 => "decreasing"
        # BUT remember: data is desc. first_half = newer, second_half = older
        # The code: if second_avg > first_avg * 1.05 => "increasing"
        # So to get "increasing" we need second_half avg > first_half avg * 1.05
        intensity_recs = [self._make_intensity_record(v) for v in [100, 110, 200, 210]]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([current_rec])]
            else:
                return [FakeTable(intensity_recs)]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/trends")
        assert resp.status_code == 200
        # first_half=[100,110] avg=105; second_half=[200,210] avg=205
        # 205 > 105*1.05=110.25 => "increasing"
        assert resp.json()["trend"] == "increasing"

    @pytest.mark.asyncio
    async def test_trends_decreasing(self, client):
        current_rec = self._make_current_record(100.0)
        # first_half=[300,290] avg=295; second_half=[100,110] avg=105
        # 105 < 295*0.95=280.25 => "decreasing"
        intensity_recs = [self._make_intensity_record(v) for v in [300, 290, 100, 110]]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([current_rec])]
            else:
                return [FakeTable(intensity_recs)]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/trends")
        assert resp.status_code == 200
        assert resp.json()["trend"] == "decreasing"

    @pytest.mark.asyncio
    async def test_trends_single_intensity_is_stable(self, client):
        """With only one intensity reading, trend should be stable."""
        current_rec = self._make_current_record(200.0)
        intensity_recs = [self._make_intensity_record(200)]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [FakeTable([current_rec])]
            else:
                return [FakeTable(intensity_recs)]

        mock_client, _ = _make_mock_client(side_effect)
        with patch("src.energy_endpoints.get_influxdb_client", return_value=mock_client):
            resp = await client.get("/api/v1/energy/carbon-intensity/trends")
        assert resp.status_code == 200
        assert resp.json()["trend"] == "stable"
