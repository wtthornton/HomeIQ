"""
InfluxDB writer for automation trace data.

Creates Points for the `automation_traces` measurement and writes
them to the existing `home_assistant_events` bucket.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from influxdb_client_3 import InfluxDBClient3, Point

from . import config

logger = logging.getLogger(__name__)


class InfluxDBTraceWriter:
    """Write automation trace data to InfluxDB."""

    def __init__(self):
        self.client: InfluxDBClient3 | None = None
        self.write_success_count = 0
        self.write_failure_count = 0
        self.last_write: datetime | None = None
        self.last_write_error: str | None = None

    async def startup(self) -> bool:
        """Initialize InfluxDB client connection."""
        if not config.INFLUXDB_TOKEN:
            logger.error("INFLUXDB_TOKEN not set")
            return False

        try:
            self.client = InfluxDBClient3(
                host=config.INFLUXDB_URL,
                token=config.INFLUXDB_TOKEN,
                database=config.INFLUXDB_BUCKET,
                org=config.INFLUXDB_ORG,
            )
            # Test connection
            await asyncio.to_thread(self.client.query, "SELECT 1")
            logger.info("InfluxDB connection verified at %s", config.INFLUXDB_URL)
            return True
        except Exception:
            logger.exception("Failed to connect to InfluxDB")
            self.client = None
            return False

    def shutdown(self):
        """Close InfluxDB client."""
        if self.client:
            self.client.close()
            self.client = None

    async def write_trace(self, automation_id: str, trace: dict[str, Any]):
        """Convert a full trace into an InfluxDB point and write it.

        Args:
            automation_id: The automation entity_id or item_id.
            trace: Full trace dict from HA trace/get response.
        """
        if not self.client:
            logger.warning("InfluxDB client not available, skipping write")
            return

        try:
            # Parse timestamps
            ts_start = trace.get("timestamp", {}).get("start")
            ts_finish = trace.get("timestamp", {}).get("finish")

            if not ts_start:
                logger.warning("Trace missing start timestamp, skipping")
                return

            start_dt = datetime.fromisoformat(ts_start)
            duration_seconds = 0.0
            if ts_finish:
                finish_dt = datetime.fromisoformat(ts_finish)
                duration_seconds = (finish_dt - start_dt).total_seconds()

            # Extract trigger info
            trigger_desc = trace.get("trigger", "")
            trigger_type = self._extract_trigger_type(trigger_desc)
            trigger_entity = self._extract_trigger_entity(trigger_desc)

            # Count steps in trace
            trace_steps = trace.get("trace", {})
            step_count = sum(len(v) for v in trace_steps.values()) if isinstance(trace_steps, dict) else 0

            # Check if conditions passed (look for condition steps with result)
            conditions_passed = self._check_conditions_passed(trace_steps)

            # Execution result
            execution_result = trace.get("script_execution", "unknown")

            # Build InfluxDB point
            point = (
                Point("automation_traces")
                .tag("automation_id", automation_id)
                .tag("execution_result", execution_result)
                .tag("trigger_type", trigger_type)
                .field("run_id", trace.get("run_id", ""))
                .field("context_id", trace.get("context", {}).get("id", ""))
                .field("duration_seconds", duration_seconds)
                .field("step_count", step_count)
                .field("last_step", trace.get("last_step", ""))
                .field("error_message", trace.get("error", "") or "")
                .field("trigger_entity", trigger_entity)
                .field("conditions_passed", 1 if conditions_passed else 0)
                .field("trace_json", json.dumps(trace, default=str))
                .time(start_dt)
            )

            await self._write_with_retry(point)

        except Exception:
            logger.exception("Error writing trace for %s", automation_id)
            self.write_failure_count += 1

    async def _write_with_retry(self, point: Point):
        """Write a single point with retry and exponential backoff."""
        for attempt in range(1, config.INFLUXDB_WRITE_RETRIES + 1):
            try:
                await asyncio.to_thread(self.client.write, point)
                self.write_success_count += 1
                self.last_write = datetime.now(timezone.utc)
                self.last_write_error = None
                return
            except Exception as e:
                self.last_write_error = str(e)
                if attempt >= config.INFLUXDB_WRITE_RETRIES:
                    self.write_failure_count += 1
                    logger.error("InfluxDB write failed after %d attempts: %s", attempt, e)
                else:
                    backoff = 2 ** (attempt - 1)
                    logger.warning("InfluxDB write failed (attempt %d/%d), retrying in %ds",
                                   attempt, config.INFLUXDB_WRITE_RETRIES, backoff)
                    await asyncio.sleep(backoff)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_trigger_type(trigger_desc: str) -> str:
        """Extract trigger type from human-readable trigger description."""
        desc = trigger_desc.lower()
        if "state of" in desc:
            return "state"
        if "time" in desc:
            return "time"
        if "event" in desc:
            return "event"
        if "mqtt" in desc:
            return "mqtt"
        if "webhook" in desc:
            return "webhook"
        if "sun" in desc:
            return "sun"
        if "zone" in desc:
            return "zone"
        if "numeric_state" in desc:
            return "numeric_state"
        if "template" in desc:
            return "template"
        return "other"

    @staticmethod
    def _extract_trigger_entity(trigger_desc: str) -> str:
        """Extract entity_id from trigger description like 'state of binary_sensor.motion'."""
        if "state of " in trigger_desc:
            return trigger_desc.split("state of ")[-1].strip()
        return ""

    @staticmethod
    def _check_conditions_passed(trace_steps: dict) -> bool:
        """Check whether conditions evaluated to true in the trace."""
        if not isinstance(trace_steps, dict):
            return True  # No conditions = passed
        for key, steps in trace_steps.items():
            if key.startswith("condition/"):
                for step in steps:
                    result = step.get("result", {})
                    if isinstance(result, dict) and result.get("result") is False:
                        return False
        return True
