"""Unit tests for Pydantic models in endpoint modules — Story 85.10

Tests the response/request models defined in various endpoint files.
Pure data-class tests — no HTTP or database interaction.
"""

from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# _models.py — shared response models
# ---------------------------------------------------------------------------

class TestSharedModels:

    def test_api_response_success(self):
        from src._models import APIResponse
        r = APIResponse(success=True, data={"key": "val"}, message="ok")
        assert r.success is True
        assert r.data == {"key": "val"}
        assert r.timestamp  # auto-generated

    def test_api_response_defaults(self):
        from src._models import APIResponse
        r = APIResponse(success=False)
        assert r.data is None
        assert r.message is None

    def test_error_response(self):
        from src._models import ErrorResponse
        r = ErrorResponse(error="something went wrong")
        assert r.success is False
        assert r.error_code is None
        assert r.timestamp

    def test_error_response_with_code(self):
        from src._models import ErrorResponse
        r = ErrorResponse(error="not found", error_code="E404")
        assert r.error_code == "E404"


# ---------------------------------------------------------------------------
# evaluation_endpoints models
# ---------------------------------------------------------------------------

class TestEvaluationModels:

    def test_agent_summary_defaults(self):
        from src.evaluation_endpoints import AgentSummary
        s = AgentSummary(agent_name="test-agent")
        assert s.agent_name == "test-agent"
        assert s.last_run is None
        assert s.sessions_evaluated == 0
        assert s.total_evaluations == 0
        assert s.alerts_triggered == 0
        assert s.aggregate_scores == {}

    def test_agents_list_response(self):
        from src.evaluation_endpoints import AgentsListResponse, AgentSummary
        r = AgentsListResponse(agents=[
            AgentSummary(agent_name="a1"),
            AgentSummary(agent_name="a2"),
        ])
        assert len(r.agents) == 2
        assert r.timestamp  # auto-generated

    def test_history_response(self):
        from src.evaluation_endpoints import HistoryResponse
        r = HistoryResponse(
            agent_name="test", scores=[], total=0, page=1, page_size=10
        )
        assert r.total == 0

    def test_trends_response(self):
        from src.evaluation_endpoints import TrendsResponse
        r = TrendsResponse(agent_name="test", period="7d", trends={})
        assert r.period == "7d"

    def test_alert_response(self):
        from src.evaluation_endpoints import AlertResponse
        r = AlertResponse(
            alert_id="a1", agent_name="test", evaluator_name="eval",
            level="warning", metric="score", threshold=0.8,
            actual_score=0.5, priority="high", status="active",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        assert r.acknowledged_by is None
        assert r.note is None

    def test_acknowledge_request_defaults(self):
        from src.evaluation_endpoints import AcknowledgeRequest
        r = AcknowledgeRequest()
        assert r.by == "operator"
        assert r.note == ""

    def test_health_response(self):
        from src.evaluation_endpoints import HealthResponse
        r = HealthResponse(
            status="running", registered_agents=["a1"],
            batch_size=10, timestamp="now"
        )
        assert r.status == "running"

    def test_trigger_response(self):
        from src.evaluation_endpoints import TriggerResponse
        r = TriggerResponse(
            agent_name="test", sessions_evaluated=5,
            total_evaluations=10, alerts_triggered=1,
            timestamp="now",
        )
        assert r.sessions_evaluated == 5


# ---------------------------------------------------------------------------
# jobs_endpoints models
# ---------------------------------------------------------------------------

class TestJobsEndpointModels:

    def test_job_status_response(self):
        from src.jobs_endpoints import JobStatusResponse
        r = JobStatusResponse(
            running=True, apscheduler_available=True,
            jobs=[], consolidation=None,
        )
        assert r.running is True
        assert r.consolidation is None

    def test_consolidation_metrics_response_defaults(self):
        from src.jobs_endpoints import ConsolidationMetricsResponse
        r = ConsolidationMetricsResponse(started_at="2026-01-01T00:00:00")
        assert r.memories_created == 0
        assert r.overrides_detected == 0
        assert r.success is True
        assert r.error is None

    def test_trigger_response(self):
        from src.jobs_endpoints import TriggerResponse
        r = TriggerResponse()
        assert r.success is True
        assert r.duration_ms == 0.0


# ---------------------------------------------------------------------------
# hygiene_endpoints models
# ---------------------------------------------------------------------------

class TestHygieneModels:

    def test_hygiene_issue_response_defaults(self):
        from src.hygiene_endpoints import HygieneIssueResponse
        r = HygieneIssueResponse(
            issue_key="iss-1", issue_type="naming",
            severity="low", status="open",
        )
        assert r.device_id is None
        assert r.metadata == {}

    def test_hygiene_issue_list_response(self):
        from src.hygiene_endpoints import HygieneIssueListResponse
        r = HygieneIssueListResponse(issues=[], count=0, total=0)
        assert r.count == 0

    def test_update_issue_status_request(self):
        from src.hygiene_endpoints import UpdateIssueStatusRequest
        r = UpdateIssueStatusRequest(status="resolved")
        assert r.status == "resolved"

    def test_apply_issue_action_request(self):
        from src.hygiene_endpoints import ApplyIssueActionRequest
        r = ApplyIssueActionRequest(action="rename")
        assert r.value is None


# ---------------------------------------------------------------------------
# health_endpoints models
# ---------------------------------------------------------------------------

class TestHealthEndpointModels:

    def test_health_status(self):
        from src.health_endpoints import HealthStatus
        r = HealthStatus(
            status="healthy", timestamp="now", uptime_seconds=3600.0,
            version="1.0.0", services={}, dependencies={}, metrics={},
        )
        assert r.status == "healthy"
        assert r.uptime_seconds == 3600.0

    def test_service_health_defaults(self):
        from src.health_endpoints import ServiceHealth
        r = ServiceHealth(name="test", status="healthy", last_check="now")
        assert r.response_time_ms is None
        assert r.error_message is None

    def test_service_health_with_error(self):
        from src.health_endpoints import ServiceHealth
        r = ServiceHealth(
            name="test", status="error", last_check="now",
            response_time_ms=500.0, error_message="timeout",
        )
        assert r.error_message == "timeout"


# ---------------------------------------------------------------------------
# config_endpoints models
# ---------------------------------------------------------------------------

class TestConfigEndpointModels:

    def test_config_item(self):
        from src.config_endpoints import ConfigItem
        r = ConfigItem(
            key="HA_URL", value="ws://localhost",
            description="HA URL", type="string",
        )
        assert r.required is False
        assert r.default is None
        assert r.validation_rules == {}

    def test_config_update(self):
        from src.config_endpoints import ConfigUpdate
        r = ConfigUpdate(key="PORT", value=8080)
        assert r.reason is None

    def test_config_validation(self):
        from src.config_endpoints import ConfigValidation
        r = ConfigValidation(is_valid=True)
        assert r.errors == []
        assert r.warnings == []


# ---------------------------------------------------------------------------
# docker_endpoints & docker_service models
# ---------------------------------------------------------------------------

    # docker_endpoints/docker_service skipped — `docker` package not installed in test env


# ---------------------------------------------------------------------------
# sports_endpoints models
# ---------------------------------------------------------------------------

class TestSportsModels:

    def test_game_response_defaults(self):
        from src.sports_endpoints import GameResponse
        g = GameResponse(
            game_id="g1", league="NFL", season=2025,
            home_team="CBJ", away_team="VGK",
            status="scheduled", timestamp="now",
        )
        assert g.home_score is None
        assert g.team_homeaway is None
        assert g.team_color_primary is None
        assert g.team_winner is None
        assert g.event_name is None

    def test_game_response_full(self):
        from src.sports_endpoints import GameResponse
        g = GameResponse(
            game_id="g1", league="NHL", season=2025,
            home_team="CBJ", away_team="VGK",
            home_score=3, away_score=2,
            status="finished", timestamp="now",
            team_homeaway="home", team_winner=True,
            team_color_primary="#344043",
            team_color_secondary="#b4975a",
            event_name="CBJ @ VGK",
            last_play="Goal!",
        )
        assert g.team_winner is True
        assert g.team_color_primary == "#344043"

    def test_game_list_response(self):
        from src.sports_endpoints import GameListResponse
        r = GameListResponse(games=[], count=0)
        assert r.team is None
        assert r.season is None

    def test_team_schedule_response(self):
        from src.sports_endpoints import TeamScheduleResponse
        r = TeamScheduleResponse(
            team="CBJ", season=2025, games=[], total_games=82,
            wins=40, losses=30, ties=12, win_percentage=0.56,
        )
        assert r.win_percentage == 0.56

    def test_score_timeline_point(self):
        from src.sports_endpoints import ScoreTimelinePoint
        p = ScoreTimelinePoint(
            timestamp="now", home_score=2, away_score=1,
            quarter_period="2nd", time_remaining="10:00",
        )
        assert p.home_score == 2

    def test_score_timeline_response(self):
        from src.sports_endpoints import ScoreTimelineResponse
        r = ScoreTimelineResponse(
            game_id="g1", home_team="CBJ", away_team="VGK",
            timeline=[], final_score="3-2",
        )
        assert r.final_score == "3-2"

    def test_user_teams_request_defaults(self):
        from src.sports_endpoints import UserTeamsRequest
        r = UserTeamsRequest()
        assert r.nfl_teams == []
        assert r.nhl_teams == []

    def test_user_teams_response(self):
        from src.sports_endpoints import UserTeamsResponse
        r = UserTeamsResponse(
            user_id="u1", nfl_teams=["Browns"],
            nhl_teams=["CBJ"],
        )
        assert r.created_at is None


    # alert_endpoints and metrics_endpoints use class-based routers, skipped
