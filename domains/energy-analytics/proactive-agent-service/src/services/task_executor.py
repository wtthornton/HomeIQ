"""Execute scheduled tasks by calling ha-ai-agent-service.

Epic 27: Scheduled AI Tasks (Continuity)
Story 27.2: Task Executor with Tool Access
Story 27.5: Notification Integration
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.scheduled_task import ScheduledTask, TaskExecution

logger = logging.getLogger(__name__)

# Keywords that indicate an alert condition in the LLM response
_ALERT_KEYWORDS = frozenset({
    "alert", "warning", "urgent", "critical", "attention",
    "problem", "issue", "offline", "unavailable", "open",
    "unlocked", "anomaly", "spike", "unusual", "breach",
    "low battery", "not responding",
})


class TaskExecutor:
    """Execute a scheduled task prompt via ha-ai-agent-service.

    Each execution creates a ``TaskExecution`` row and POSTs the task
    prompt to the agent chat endpoint.  Results are persisted regardless
    of success or failure so the history is always complete.
    """

    def __init__(self, settings: Settings) -> None:
        self._agent_url = settings.ha_ai_agent_url.rstrip("/")
        self._agent_timeout = settings.ha_ai_agent_timeout
        self._notify_url = settings.ha_device_control_notify_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Create the shared HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(300, connect=10),
            follow_redirects=True,
        )

    async def stop(self) -> None:
        """Close the shared HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        task: ScheduledTask,
        session: AsyncSession,
    ) -> TaskExecution:
        """Run a single task and persist the execution result.

        Args:
            task: The scheduled task to execute.
            session: An active database session (caller manages commit).

        Returns:
            The completed ``TaskExecution`` row.
        """
        execution = TaskExecution(
            task_id=task.id,
            started_at=datetime.now(UTC),
            status="running",
            prompt=task.prompt,
        )
        session.add(execution)
        await session.flush()  # get execution.id

        start_ts = time.monotonic()
        try:
            response_data = await self._call_agent(
                task.prompt,
                timeout=task.max_execution_seconds,
            )
            elapsed_ms = int((time.monotonic() - start_ts) * 1000)

            execution.status = "completed"
            execution.completed_at = datetime.now(UTC)
            execution.response = response_data.get("reply", "")
            execution.tools_used = json.dumps(
                response_data.get("tools_used", []),
            )
            execution.duration_ms = elapsed_ms

        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start_ts) * 1000)
            execution.status = "timeout"
            execution.completed_at = datetime.now(UTC)
            execution.error = (
                f"Execution timed out after {task.max_execution_seconds}s"
            )
            execution.duration_ms = elapsed_ms
            logger.warning(
                "Task %s (%s) timed out after %d ms",
                task.id, task.name, elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_ts) * 1000)
            execution.status = "failed"
            execution.completed_at = datetime.now(UTC)
            execution.error = str(exc)[:2000]
            execution.duration_ms = elapsed_ms
            logger.exception(
                "Task %s (%s) failed: %s", task.id, task.name, exc,
            )

        # Update task metadata
        await session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task.id)
            .values(
                last_run_at=execution.started_at,
                run_count=ScheduledTask.run_count + 1,
            ),
        )

        # Notifications (best-effort, never fails the execution)
        await self._maybe_notify(task, execution)

        await session.commit()
        return execution

    # ------------------------------------------------------------------
    # Agent communication
    # ------------------------------------------------------------------

    async def _call_agent(
        self,
        prompt: str,
        *,
        timeout: int = 120,
    ) -> dict:
        """POST to ha-ai-agent-service /api/chat.

        Returns the parsed JSON response body.
        """
        if self._client is None:
            msg = "TaskExecutor not started — call start() first"
            raise RuntimeError(msg)

        url = f"{self._agent_url}/api/chat"
        payload = {
            "message": prompt,
            "conversation_id": None,  # new conversation per task
            "include_tools": True,
        }
        resp = await self._client.post(
            url,
            json=payload,
            timeout=httpx.Timeout(float(timeout), connect=10),
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Notification helpers (Story 27.5)
    # ------------------------------------------------------------------

    async def _maybe_notify(
        self,
        task: ScheduledTask,
        execution: TaskExecution,
    ) -> None:
        """Send a notification based on the task's preference."""
        pref = task.notification_preference
        if pref == "never":
            return

        should_send = False
        if pref == "always":
            should_send = True
        elif pref == "on_alert":
            should_send = self._response_contains_alert(
                execution.response or "",
            )

        if not should_send:
            return

        try:
            await self._send_notification(task, execution)
            execution.notification_sent = True
        except Exception:
            logger.exception(
                "Failed to send notification for task %s", task.id,
            )

    @staticmethod
    def _response_contains_alert(text: str) -> bool:
        """Heuristic check: does the response contain alert-like keywords?"""
        lower = text.lower()
        return any(kw in lower for kw in _ALERT_KEYWORDS)

    async def _send_notification(
        self,
        task: ScheduledTask,
        execution: TaskExecution,
    ) -> None:
        """POST a notification to ha-device-control notify endpoint."""
        if self._client is None:
            return

        title = f"HomeIQ: {task.name}"
        body = (execution.response or "Task completed.")[:500]
        if execution.status == "failed":
            title = f"HomeIQ: {task.name} (FAILED)"
            body = execution.error or "Unknown error"

        payload = {
            "title": title,
            "message": body,
            "data": {
                "task_id": task.id,
                "execution_id": execution.id,
                "status": execution.status,
            },
        }
        try:
            resp = await self._client.post(
                self._notify_url,
                json=payload,
                timeout=httpx.Timeout(10, connect=5),
            )
            resp.raise_for_status()
        except Exception:
            logger.debug(
                "Notification endpoint unavailable at %s", self._notify_url,
            )
            raise
