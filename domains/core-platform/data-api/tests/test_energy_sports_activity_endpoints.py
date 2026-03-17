"""
Tests for energy + sports + activity + ha_automation + analytics endpoints — Epic 80, Story 80.10c

Covers 17 scenarios:

energy_endpoints:
1.  EnergyCorrelation — validates fields
2.  PowerReading — validates fields
3.  DeviceEnergyImpact — validates fields
4.  EnergyStatistics — validates optional peak_time
5.  CarbonIntensityResponse — validates fields

sports_endpoints:
6.  GameResponse — validates all fields including automation attrs
7.  GameListResponse — validates fields
8.  TeamScheduleResponse — validates record fields
9.  ScoreTimelineResponse — validates fields
10. UserTeamsRequest — validates defaults
11. get_teams — returns NFL teams when league=NFL

ha_automation_endpoints:
12. _team_won — home team wins
13. _team_won — away team wins
14. GameStatusResponse — validates fields
15. WebhookRegistration — validates fields

analytics_endpoints:
16. calculate_trend — stable/up/down detection
17. get_time_range_params — returns correct interval params
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# energy_endpoints model tests
# ===========================================================================


class TestEnergyModels:
    """Energy endpoint response models."""

    def test_energy_correlation(self):
        from src.energy_endpoints import EnergyCorrelation

        ec = EnergyCorrelation(
            timestamp=datetime.now(UTC),
            entity_id="switch.kitchen",
            domain="switch",
            state="on",
            previous_state="off",
            power_before_w=50.0,
            power_after_w=200.0,
            power_delta_w=150.0,
            power_delta_pct=300.0,
        )
        assert ec.power_delta_w == 150.0
        assert ec.entity_id == "switch.kitchen"

    def test_power_reading(self):
        from src.energy_endpoints import PowerReading

        pr = PowerReading(
            timestamp=datetime.now(UTC),
            total_power_w=1500.0,
            daily_kwh=12.5,
        )
        assert pr.total_power_w == 1500.0

    def test_device_energy_impact(self):
        from src.energy_endpoints import DeviceEnergyImpact

        dei = DeviceEnergyImpact(
            entity_id="switch.dryer",
            domain="switch",
            average_power_on_w=3000.0,
            average_power_off_w=5.0,
            total_state_changes=20,
            estimated_daily_kwh=24.0,
            estimated_monthly_cost=86.40,
        )
        assert dei.estimated_monthly_cost == 86.40

    def test_energy_statistics_optional_peak(self):
        from src.energy_endpoints import EnergyStatistics

        es = EnergyStatistics(
            current_power_w=1200.0,
            daily_kwh=10.0,
            peak_power_w=3500.0,
            peak_time=None,
            average_power_w=800.0,
            total_correlations=42,
        )
        assert es.peak_time is None
        assert es.total_correlations == 42

    def test_carbon_intensity_response(self):
        from src.energy_endpoints import CarbonIntensityResponse

        ci = CarbonIntensityResponse(
            timestamp=datetime.now(UTC),
            intensity=245.5,
            renewable_percentage=35.0,
            fossil_percentage=65.0,
            forecast_1h=240.0,
            forecast_24h=230.0,
            region="UK",
        )
        assert ci.intensity == 245.5
        assert ci.region == "UK"
        assert ci.grid_operator is None


# ===========================================================================
# sports_endpoints model tests
# ===========================================================================


class TestSportsModels:
    """Sports endpoint response models."""

    def test_game_response_with_automation_attrs(self):
        from src.sports_endpoints import GameResponse

        g = GameResponse(
            game_id="game-001",
            league="NFL",
            season=2025,
            week="14",
            home_team="KC",
            away_team="BUF",
            home_score=24,
            away_score=21,
            status="finished",
            timestamp=datetime.now(UTC).isoformat(),
            team_homeaway="home",
            team_color_primary="#E31837",
            team_color_secondary="#FFB612",
            team_winner=True,
            opponent_winner=False,
            event_name="KC vs BUF",
        )
        assert g.team_winner is True
        assert g.team_color_primary == "#E31837"
        assert g.last_play is None

    def test_game_list_response(self):
        from src.sports_endpoints import GameListResponse, GameResponse

        games = [
            GameResponse(
                game_id=f"g-{i}", league="NFL", season=2025,
                home_team="KC", away_team="BUF", status="finished",
                timestamp=datetime.now(UTC).isoformat(),
            )
            for i in range(3)
        ]
        gl = GameListResponse(games=games, count=3, team="KC", season=2025)
        assert gl.count == 3

    def test_team_schedule_response(self):
        from src.sports_endpoints import TeamScheduleResponse

        ts = TeamScheduleResponse(
            team="KC", season=2025, games=[], total_games=16,
            wins=10, losses=5, ties=1, win_percentage=0.625,
        )
        assert ts.win_percentage == 0.625
        assert ts.total_games == 16

    def test_score_timeline_response(self):
        from src.sports_endpoints import ScoreTimelinePoint, ScoreTimelineResponse

        point = ScoreTimelinePoint(
            timestamp="2026-01-01T20:00:00Z",
            home_score=7, away_score=3,
            quarter_period="Q1", time_remaining="5:00",
        )
        r = ScoreTimelineResponse(
            game_id="g-001", home_team="KC", away_team="BUF",
            timeline=[point], final_score="24-21",
        )
        assert r.final_score == "24-21"

    def test_user_teams_request_defaults(self):
        from src.sports_endpoints import UserTeamsRequest

        req = UserTeamsRequest()
        assert req.nfl_teams == []
        assert req.nhl_teams == []

    @pytest.mark.asyncio
    async def test_get_teams_nfl(self):
        from src.sports_endpoints import get_teams

        result = await get_teams(league="NFL")
        assert result["count"] == 16
        assert all(t["league"] == "NFL" for t in result["teams"])


# ===========================================================================
# ha_automation_endpoints tests
# ===========================================================================


class TestHaAutomationHelpers:
    """ha_automation_endpoints helper functions."""

    def test_team_won_home(self):
        from src.ha_automation_endpoints import _team_won

        game = {"home_team": "KC", "away_team": "BUF", "home_score": 24, "away_score": 21}
        assert _team_won(game, "KC") is True
        assert _team_won(game, "BUF") is False

    def test_team_won_away(self):
        from src.ha_automation_endpoints import _team_won

        game = {"home_team": "KC", "away_team": "BUF", "home_score": 21, "away_score": 24}
        assert _team_won(game, "BUF") is True
        assert _team_won(game, "KC") is False


class TestHaAutomationModels:
    """ha_automation_endpoints response models."""

    def test_game_status_response(self):
        from src.ha_automation_endpoints import GameStatusResponse

        r = GameStatusResponse(
            status="live", team="KC", game_id="g-001",
            opponent="BUF", score="24-21", time_remaining="2:00",
        )
        assert r.status == "live"
        assert r.score == "24-21"

    def test_webhook_registration(self):
        from src.ha_automation_endpoints import WebhookRegistration

        w = WebhookRegistration(
            webhook_url="https://ha.local/api/webhook/test",
            secret="my-secret",
            team="KC",
            events=["game_start", "score_change"],
        )
        assert len(w.events) == 2
        assert w.team == "KC"


# ===========================================================================
# analytics_endpoints tests
# ===========================================================================


class TestAnalyticsHelpers:
    """analytics_endpoints helper functions."""

    def test_calculate_trend_stable(self):
        from src.analytics_endpoints import calculate_trend

        # Not enough data → stable
        assert calculate_trend([1, 2, 3]) == "stable"

        # Equal halves → stable
        data = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        assert calculate_trend(data) == "stable"

    def test_calculate_trend_up(self):
        from src.analytics_endpoints import calculate_trend

        data = [1, 1, 1, 1, 1, 10, 10, 10, 10, 10]
        assert calculate_trend(data) == "up"

    def test_calculate_trend_down(self):
        from src.analytics_endpoints import calculate_trend

        data = [10, 10, 10, 10, 10, 1, 1, 1, 1, 1]
        assert calculate_trend(data) == "down"

    def test_get_time_range_params_1h(self):
        from src.analytics_endpoints import get_time_range_params

        start, interval, points = get_time_range_params("1h")
        assert interval == "1m"
        assert points == 60

    def test_get_time_range_params_24h(self):
        from src.analytics_endpoints import get_time_range_params

        start, interval, points = get_time_range_params("24h")
        assert interval == "15m"
        assert points == 96

    def test_get_time_range_params_default(self):
        from src.analytics_endpoints import get_time_range_params

        start, interval, points = get_time_range_params("bogus")
        assert interval == "1m"
        assert points == 60
