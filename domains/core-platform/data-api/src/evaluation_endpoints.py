"""
Evaluation API Endpoints for Data API
E4.S3: Agent Evaluation Observability

REST endpoints exposing evaluation results, trends, alerts, and
manual triggers from the shared evaluation framework.

Endpoints:
  GET  /evaluations              — list all agents with latest scores
  GET  /evaluations/health       — scheduler status
  GET  /evaluations/{agent}      — latest report for an agent
  GET  /evaluations/{agent}/history  — paginated historical results
  GET  /evaluations/{agent}/trends   — score trends over time
  GET  /evaluations/{agent}/alerts   — active threshold violations
  POST /evaluations/{agent}/trigger  — manual evaluation trigger
  POST /evaluations/{agent}/results  — direct result submission (Story 5.4)
  POST /evaluations/{agent}/alerts/{alert_id}/acknowledge — ack alert
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AgentSummary(BaseModel):
    """Summary for one agent in the agents list."""
    agent_name: str
    last_run: str | None = None
    sessions_evaluated: int = 0
    total_evaluations: int = 0
    alerts_triggered: int = 0
    aggregate_scores: dict[str, float] = Field(default_factory=dict)


class AgentsListResponse(BaseModel):
    agents: list[AgentSummary]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HistoryResponse(BaseModel):
    agent_name: str
    scores: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class TrendsResponse(BaseModel):
    agent_name: str
    period: str
    trends: dict[str, list[dict[str, Any]]]


class AlertResponse(BaseModel):
    alert_id: str
    agent_name: str
    evaluator_name: str
    level: str
    metric: str
    threshold: float
    actual_score: float
    priority: str
    status: str
    created_at: str
    updated_at: str
    acknowledged_by: str | None = None
    note: str | None = None


class AlertsListResponse(BaseModel):
    agent_name: str
    alerts: list[AlertResponse]
    total: int


class TriggerResponse(BaseModel):
    agent_name: str
    sessions_evaluated: int
    total_evaluations: int
    alerts_triggered: int
    timestamp: str


class AcknowledgeRequest(BaseModel):
    by: str = "operator"
    note: str = ""


class HealthResponse(BaseModel):
    status: str
    registered_agents: list[str]
    batch_size: int
    timestamp: str


# ---------------------------------------------------------------------------
# Lazy singletons (created on first request)
# ---------------------------------------------------------------------------

_store = None
_store_initialized = False
_scheduler = None
_alert_engine = None


async def _get_store():
    """Lazy-init EvaluationStore and ensure tables are created."""
    global _store, _store_initialized
    if _store is None:
        from homeiq_patterns.evaluation import EvaluationStore
        _store = EvaluationStore(sqlite_path="./data/evaluations.db")
    if not _store_initialized:
        await _store.initialize()
        _store_initialized = True
    return _store


def _get_scheduler():
    """Lazy-init EvaluationScheduler."""
    global _scheduler
    if _scheduler is None:
        from homeiq_patterns.evaluation import EvaluationRegistry, EvaluationScheduler
        registry = EvaluationRegistry()
        _scheduler = EvaluationScheduler(registry=registry)
    return _scheduler


def _get_alert_engine():
    """Lazy-init AlertEngine."""
    global _alert_engine
    if _alert_engine is None:
        from homeiq_patterns.evaluation import AlertEngine
        _alert_engine = AlertEngine()
    return _alert_engine


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Agent Evaluation"])


@router.get("/evaluations", response_model=AgentsListResponse)
async def list_agents():
    """List all registered agents with their latest evaluation scores."""
    store = await _get_store()
    scheduler = _get_scheduler()

    agents: list[AgentSummary] = []
    for agent_name in scheduler.registered_agents:
        report = await store.get_latest_report(agent_name)
        if report:
            agents.append(AgentSummary(
                agent_name=agent_name,
                last_run=report.get("run_timestamp"),
                sessions_evaluated=report.get("sessions_evaluated", 0),
                total_evaluations=report.get("total_evaluations", 0),
                alerts_triggered=report.get("alerts_triggered", 0),
                aggregate_scores=report.get("summary", {}),
            ))
        else:
            agents.append(AgentSummary(agent_name=agent_name))

    return AgentsListResponse(agents=agents)


@router.get("/evaluations/health", response_model=HealthResponse)
async def evaluation_health():
    """Scheduler status and last run times."""
    scheduler = _get_scheduler()
    return HealthResponse(
        status="operational",
        registered_agents=scheduler.registered_agents,
        batch_size=scheduler.batch_size,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/evaluations/{agent_name}")
async def get_agent_report(agent_name: str):
    """Get the latest evaluation report for an agent."""
    store = await _get_store()
    report = await store.get_latest_report(agent_name)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evaluation data found for agent '{agent_name}'",
        )
    return report


@router.get("/evaluations/{agent_name}/history", response_model=HistoryResponse)
async def get_agent_history(
    agent_name: str,
    evaluator: str | None = Query(None, description="Filter by evaluator name"),
    level: str | None = Query(None, description="Filter by level (L1-L5)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page"),
):
    """Paginated historical evaluation results for an agent."""
    store = await _get_store()
    all_scores = await store.get_scores(agent_name, evaluator=evaluator)

    # Filter by level if specified
    if level:
        all_scores = [s for s in all_scores if s.get("level") == level]

    total = len(all_scores)
    start = (page - 1) * page_size
    page_scores = all_scores[start : start + page_size]

    return HistoryResponse(
        agent_name=agent_name,
        scores=page_scores,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/evaluations/{agent_name}/trends", response_model=TrendsResponse)
async def get_agent_trends(
    agent_name: str,
    period: str = Query("7d", description="Time period: 7d, 30d, 90d"),
):
    """Aggregated score trends over time for an agent."""
    store = await _get_store()
    trends = await store.get_trends(agent_name, period=period)
    return TrendsResponse(
        agent_name=agent_name,
        period=period,
        trends=trends,
    )


@router.get("/evaluations/{agent_name}/alerts", response_model=AlertsListResponse)
async def get_agent_alerts(
    agent_name: str,
    alert_status: str | None = Query(
        None, alias="status", description="Filter: active, acknowledged, resolved"
    ),
):
    """Active threshold violation alerts for an agent."""
    engine = _get_alert_engine()

    if alert_status and alert_status in ("active", "acknowledged"):
        alerts = engine.get_active_alerts(agent_name=agent_name)
    else:
        alerts = engine.get_all_alerts(agent_name=agent_name)

    if alert_status:
        alerts = [a for a in alerts if a.status == alert_status]

    alert_responses = [
        AlertResponse(
            alert_id=a.alert_id,
            agent_name=a.agent_name,
            evaluator_name=a.evaluator_name,
            level=a.level.value,
            metric=a.metric,
            threshold=a.threshold,
            actual_score=a.actual_score,
            priority=a.priority,
            status=a.status,
            created_at=a.created_at.isoformat(),
            updated_at=a.updated_at.isoformat(),
            acknowledged_by=a.acknowledged_by,
            note=a.note,
        )
        for a in alerts
    ]

    return AlertsListResponse(
        agent_name=agent_name,
        alerts=alert_responses,
        total=len(alert_responses),
    )


@router.post("/evaluations/{agent_name}/trigger", response_model=TriggerResponse)
async def trigger_evaluation(agent_name: str):
    """Manually trigger an evaluation run for an agent."""
    scheduler = _get_scheduler()

    if agent_name not in scheduler.registered_agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' is not registered in the scheduler",
        )

    report = await scheduler.run_agent(agent_name)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation run failed for '{agent_name}'",
        )

    # Store the results
    store = await _get_store()
    await store.store_batch_report(report)

    # Check alerts
    engine = _get_alert_engine()
    try:
        from homeiq_patterns.evaluation import ConfigLoader
        config = ConfigLoader.from_yaml(
            f"shared/patterns/evaluation/configs/{agent_name.replace('-', '_')}.yaml"
        )
        engine.check_report(report, config)
    except Exception:
        logger.debug("Could not load config for alert checking: %s", agent_name)

    return TriggerResponse(
        agent_name=agent_name,
        sessions_evaluated=report.sessions_evaluated,
        total_evaluations=report.total_evaluations,
        alerts_triggered=len(report.alerts),
        timestamp=report.timestamp.isoformat(),
    )


class SubmitResultsRequest(BaseModel):
    """Request body for direct evaluation result submission."""
    session_id: str = ""
    timestamp: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    aggregate_scores: dict[str, float] = Field(default_factory=dict)


class SubmitResultsResponse(BaseModel):
    agent_name: str
    run_id: int
    results_stored: int
    timestamp: str


@router.post(
    "/evaluations/{agent_name}/results",
    response_model=SubmitResultsResponse,
)
async def submit_evaluation_results(
    agent_name: str,
    body: SubmitResultsRequest,
):
    """
    Submit pre-computed evaluation results directly to storage.

    Used by the test harness (Story 5.4) to store evaluation results
    without going through the scheduler. The test harness runs evaluators
    locally and POSTs the results for dashboard trending.
    """
    from homeiq_patterns.evaluation.models import (
        BatchReport,
        EvalLevel,
        EvaluationReport,
        EvaluationResult,
    )

    ts_str = body.timestamp or datetime.now(timezone.utc).isoformat()

    # Reconstruct EvaluationResult objects from dicts
    eval_results: list[EvaluationResult] = []
    for r in body.results:
        level_str = r.get("level", "L1_OUTCOME")
        try:
            level = EvalLevel(level_str)
        except ValueError:
            level = EvalLevel.OUTCOME
        eval_results.append(
            EvaluationResult(
                evaluator_name=r.get("evaluator", r.get("evaluator_name", "")),
                level=level,
                score=float(r.get("score", 0.0)),
                label=r.get("label", ""),
                explanation=r.get("explanation", ""),
                passed=r.get("passed", True),
            )
        )

    # Build a BatchReport wrapping the single session
    report = BatchReport(
        agent_name=agent_name,
        sessions_evaluated=1,
        total_evaluations=len(eval_results),
        reports=[
            EvaluationReport(
                session_id=body.session_id,
                agent_name=agent_name,
                results=eval_results,
            )
        ],
        aggregate_scores=body.aggregate_scores,
    )

    # Store in InfluxDB + SQLite
    store = await _get_store()
    run_id = await store.store_batch_report(report)

    logger.info(
        "Stored %d evaluation results for '%s' (run_id=%d)",
        len(eval_results),
        agent_name,
        run_id,
    )

    return SubmitResultsResponse(
        agent_name=agent_name,
        run_id=run_id,
        results_stored=len(eval_results),
        timestamp=ts_str,
    )


@router.post("/evaluations/{agent_name}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    agent_name: str,
    alert_id: str,
    body: AcknowledgeRequest,
):
    """Acknowledge a threshold violation alert."""
    engine = _get_alert_engine()
    alert = engine.acknowledge(alert_id, by=body.by, note=body.note)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found",
        )
    return {
        "alert_id": alert.alert_id,
        "status": alert.status,
        "acknowledged_by": alert.acknowledged_by,
        "note": alert.note,
    }
