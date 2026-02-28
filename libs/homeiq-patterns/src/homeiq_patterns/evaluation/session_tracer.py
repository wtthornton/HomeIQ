"""
Agent Evaluation Framework — SessionTracer Middleware

Captures ``SessionTrace`` data from FastAPI agent endpoints via a
decorator pattern.  Adding ``@trace_session(agent_name="my-agent")``
to any endpoint captures request/response pairs, tool calls, and
timing without modifying agent logic.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AgentResponse, SessionTrace, ToolCall, UserMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trace sink protocol
# ---------------------------------------------------------------------------


class TraceSink:
    """
    Base class for session trace sinks.

    Subclass and override ``emit`` to store traces
    (database, file, callback, etc.).
    """

    async def emit(self, trace: SessionTrace) -> None:
        """Handle a completed session trace."""
        pass


class InMemorySink(TraceSink):
    """Stores traces in an in-memory list (useful for testing)."""

    def __init__(self) -> None:
        self.traces: list[SessionTrace] = []

    async def emit(self, trace: SessionTrace) -> None:
        self.traces.append(trace)


class CallbackSink(TraceSink):
    """Forwards traces to a user-supplied callback."""

    def __init__(self, callback: Callable[[SessionTrace], Any]) -> None:
        self._callback = callback

    async def emit(self, trace: SessionTrace) -> None:
        result = self._callback(trace)
        # Support async callbacks
        if hasattr(result, "__await__"):
            await result


class PersistentSink(TraceSink):
    """
    Persists session traces to a PostgreSQL database.

    Stores each ``SessionTrace`` as a JSON-serialized record in a
    ``trace_records`` table, preserving all data without requiring
    the full scoring pipeline.

    Resilient by design: if the database write fails, the error is
    logged but the request is not interrupted.

    Uses lazy initialization so no async setup is needed at import time.

    The database URL is configurable via the ``db_url`` parameter
    or the ``EVAL_STORE_URL`` / ``POSTGRES_URL`` environment variable.
    """

    _CREATE_TRACE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS trace_records (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        trace_json TEXT NOT NULL
    )
    """

    _CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_trace_agent ON trace_records(agent_name)",
        "CREATE INDEX IF NOT EXISTS idx_trace_session ON trace_records(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_trace_timestamp ON trace_records(timestamp)",
    ]

    def __init__(self, db_url: str | None = None, store_path: str | None = None) -> None:
        self._db_url = (
            db_url
            or os.environ.get("EVAL_STORE_URL")
            or os.environ.get("POSTGRES_URL")
            or os.environ.get("DATABASE_URL")
            or "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq"
        )
        self._engine: Any = None
        self._session_maker: Any = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazily create the engine and tables on first use."""
        if self._initialized:
            return

        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import (
                AsyncSession,
                async_sessionmaker,
                create_async_engine,
            )

            self._engine = create_async_engine(self._db_url, echo=False)
            self._session_maker = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

            async with self._engine.begin() as conn:
                await conn.execute(text(self._CREATE_TRACE_TABLE_SQL))
                for idx_sql in self._CREATE_INDEXES_SQL:
                    await conn.execute(text(idx_sql))

            self._initialized = True
            logger.info(
                "PersistentSink initialized with PostgreSQL"
            )
        except Exception:
            logger.exception(
                "PersistentSink: failed to initialize database",
            )

    async def emit(self, trace: SessionTrace) -> None:
        """Persist a completed session trace to the database."""
        try:
            await self._ensure_initialized()
            if self._session_maker is None:
                return

            from sqlalchemy import text

            trace_json = json.dumps(trace.to_dict(), default=str)
            async with self._session_maker() as session:
                await session.execute(
                    text("""
                    INSERT INTO trace_records
                        (session_id, agent_name, timestamp, trace_json)
                    VALUES (:session_id, :agent_name, :timestamp, :trace_json)
                    """),
                    {
                        "session_id": trace.session_id,
                        "agent_name": trace.agent_name,
                        "timestamp": trace.timestamp.isoformat(),
                        "trace_json": trace_json,
                    },
                )
                await session.commit()
            logger.debug(
                "PersistentSink: stored trace %s for agent %s",
                trace.session_id,
                trace.agent_name,
            )
        except Exception:
            logger.exception(
                "PersistentSink: failed to store trace %s",
                getattr(trace, "session_id", "unknown"),
            )

    async def close(self) -> None:
        """Close the database connection."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            self._initialized = False


# ---------------------------------------------------------------------------
# Session tracer context (active during a traced request)
# ---------------------------------------------------------------------------


class SessionTracerContext:
    """
    Mutable context object available during a traced request.

    Agent code can call ``record_tool_call()`` to capture tool
    invocations.  The decorator captures user messages and agent
    responses automatically.
    """

    def __init__(self, agent_name: str) -> None:
        self.trace = SessionTrace(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc),
        )
        self._tool_sequence: int = 0
        self._turn: int = 0

    def record_user_message(self, content: str) -> None:
        """Record an incoming user message."""
        self.trace.user_messages.append(
            UserMessage(
                content=content,
                timestamp=datetime.now(timezone.utc),
                turn_index=self._turn,
            )
        )

    def record_agent_response(
        self,
        content: str,
        tool_calls_in_turn: list[ToolCall] | None = None,
    ) -> None:
        """Record an agent response."""
        self.trace.agent_responses.append(
            AgentResponse(
                content=content,
                timestamp=datetime.now(timezone.utc),
                turn_index=self._turn,
                tool_calls_in_turn=tool_calls_in_turn or [],
            )
        )
        self._turn += 1

    def record_tool_call(
        self,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        result: Any = None,
        latency_ms: float | None = None,
    ) -> ToolCall:
        """Record a tool invocation and return the ToolCall object."""
        tc = ToolCall(
            tool_name=tool_name,
            parameters=parameters or {},
            result=result,
            sequence_index=self._tool_sequence,
            turn_index=self._turn,
            latency_ms=latency_ms,
        )
        self.trace.tool_calls.append(tc)
        self._tool_sequence += 1
        return tc


# ---------------------------------------------------------------------------
# Thread-/task-local storage for the active context
# ---------------------------------------------------------------------------

import contextvars

_active_context: contextvars.ContextVar[SessionTracerContext | None] = (
    contextvars.ContextVar("_active_tracer_ctx", default=None)
)


def get_tracer_context() -> SessionTracerContext | None:
    """Get the active tracer context (if inside a traced request)."""
    return _active_context.get()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def trace_session(
    agent_name: str,
    sink: TraceSink | None = None,
    model: str = "",
    temperature: float | None = None,
):
    """
    Decorator that wraps a FastAPI endpoint to capture a SessionTrace.

    Usage::

        @app.post("/api/v1/chat")
        @trace_session(agent_name="ha-ai-agent")
        async def chat(request: ChatRequest):
            ...

    The decorator:
    1. Creates a ``SessionTracerContext`` before the endpoint runs.
    2. Makes it available via ``get_tracer_context()`` so agent code
       can call ``ctx.record_tool_call(...)`` during execution.
    3. After the endpoint returns, emits the completed trace to the
       configured sink.

    Minimal performance overhead (~1ms).
    """
    _sink = sink or InMemorySink()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = SessionTracerContext(agent_name=agent_name)
            ctx.trace.model = model
            ctx.trace.temperature = temperature

            token = _active_context.set(ctx)
            start = time.perf_counter()

            try:
                # Try to capture user input from common request patterns
                _capture_user_input(ctx, args, kwargs)

                result = await func(*args, **kwargs)

                # Try to capture agent output
                _capture_agent_output(ctx, result)

                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                ctx.trace.metadata["total_latency_ms"] = round(elapsed_ms, 2)
                _active_context.reset(token)
                try:
                    await _sink.emit(ctx.trace)
                except Exception:
                    logger.exception("Failed to emit session trace")

        return wrapper

    return decorator


def _capture_user_input(
    ctx: SessionTracerContext,
    args: tuple,
    kwargs: dict[str, Any],
) -> None:
    """Best-effort extraction of user message from request args."""
    # Check kwargs for common request parameter names
    for key in ("request", "body", "payload", "data"):
        obj = kwargs.get(key)
        if obj is None:
            continue
        # Pydantic model or dict with a message/content/prompt field
        for field_name in ("message", "content", "prompt", "user_message"):
            val = getattr(obj, field_name, None) or (
                obj.get(field_name) if isinstance(obj, dict) else None
            )
            if val and isinstance(val, str):
                ctx.record_user_message(val)
                return


def _capture_agent_output(ctx: SessionTracerContext, result: Any) -> None:
    """Best-effort extraction of agent response from endpoint return value."""
    if result is None:
        return

    for field_name in ("response", "content", "message", "reply", "answer"):
        val = getattr(result, field_name, None) or (
            result.get(field_name) if isinstance(result, dict) else None
        )
        if val and isinstance(val, str):
            # Collect tool calls that belong to the current turn
            turn_tools = [
                tc
                for tc in ctx.trace.tool_calls
                if tc.turn_index == ctx._turn
            ]
            ctx.record_agent_response(val, tool_calls_in_turn=turn_tools)
            return
