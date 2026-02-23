"""
Background trace polling loop.

Every TRACE_POLL_INTERVAL_SECONDS:
1. List all automation entities from HA
2. For each automation, list trace summaries
3. For new traces (not yet seen), fetch full trace detail
4. Write to InfluxDB + POST metadata to data-api
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from . import config
from .dedup_tracker import DedupTracker
from .ha_client import HATraceClient
from .influxdb_writer import InfluxDBTraceWriter

logger = logging.getLogger(__name__)


class TracePoller:
    """Poll HA automation traces and store new ones."""

    def __init__(
        self,
        ha_client: HATraceClient,
        influxdb_writer: InfluxDBTraceWriter,
        dedup: DedupTracker,
    ):
        self.ha = ha_client
        self.writer = influxdb_writer
        self.dedup = dedup
        self.poll_count = 0
        self.traces_captured = 0
        self.automations_found = 0
        self.errors = 0
        self.last_poll: datetime | None = None
        self.last_error: str | None = None
        self._http_session: aiohttp.ClientSession | None = None

    async def run_continuous(self):
        """Background loop — runs until cancelled."""
        logger.info(
            "Starting trace poller (interval=%ds)", config.TRACE_POLL_INTERVAL_SECONDS
        )
        consecutive_failures = 0

        while True:
            try:
                await self._poll_once()
                consecutive_failures = 0
                await asyncio.sleep(config.TRACE_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                logger.info("Trace poller cancelled")
                raise
            except Exception as e:
                consecutive_failures += 1
                self.errors += 1
                self.last_error = str(e)
                backoff = min(60 * consecutive_failures, 600)
                logger.error(
                    "Trace poll error (#%d): %s — retrying in %ds",
                    consecutive_failures, e, backoff,
                )
                await asyncio.sleep(backoff)

    async def _poll_once(self):
        """Single poll cycle."""
        # 1. Get all automation entities
        automations = await self.ha.get_automation_entities()
        self.automations_found = len(automations)
        logger.info("Found %d automations", len(automations))

        # 2. List ALL traces in one call (more efficient than per-automation)
        all_traces = await self.ha.list_traces()

        # Group traces by item_id
        traces_by_automation: dict[str, list[dict]] = {}
        for trace in all_traces:
            item_id = trace.get("item_id", "")
            traces_by_automation.setdefault(item_id, []).append(trace)

        # 3. For each automation, find new traces and fetch full detail
        new_count = 0
        execution_batch: list[dict[str, Any]] = []

        for item_id, traces in traces_by_automation.items():
            new_traces = self.dedup.filter_new(item_id, traces)

            for trace_summary in new_traces:
                run_id = trace_summary.get("run_id", "")
                try:
                    full_trace = await self.ha.get_trace(item_id, run_id)
                    if full_trace:
                        automation_entity_id = self._find_entity_id(item_id, automations)
                        await self.writer.write_trace(automation_entity_id, full_trace)
                        execution_batch.append(
                            self._build_execution_record(automation_entity_id, full_trace)
                        )
                        new_count += 1
                except Exception:
                    logger.exception("Failed to process trace %s/%s", item_id, run_id)

            self.dedup.mark_seen(item_id, traces)

        self.traces_captured += new_count
        self.poll_count += 1
        self.last_poll = datetime.now(timezone.utc)

        if new_count > 0:
            logger.info("Captured %d new traces (poll #%d)", new_count, self.poll_count)
        else:
            logger.debug("No new traces (poll #%d)", self.poll_count)

        # 4. Batch-POST all executions to data-api in a single request
        if execution_batch:
            await self._post_executions_batch(execution_batch)

        # 5. Sync automation registry to data-api
        await self._sync_automation_registry(automations)

    # ------------------------------------------------------------------
    # data-api integration
    # ------------------------------------------------------------------

    async def _ensure_http_session(self) -> aiohttp.ClientSession:
        if not self._http_session or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    def _build_execution_record(self, automation_id: str, trace: dict[str, Any]) -> dict[str, Any]:
        """Build execution dict from a full trace (for batching)."""
        ts_start = trace.get("timestamp", {}).get("start")
        ts_finish = trace.get("timestamp", {}).get("finish")
        duration = 0.0
        if ts_start and ts_finish:
            s = datetime.fromisoformat(ts_start)
            f = datetime.fromisoformat(ts_finish)
            duration = (f - s).total_seconds()

        trigger_desc = trace.get("trigger") or ""
        trace_steps = trace.get("trace", {})
        step_count = sum(len(v) for v in trace_steps.values()) if isinstance(trace_steps, dict) else 0

        return {
            "automation_id": automation_id,
            "run_id": trace.get("run_id", ""),
            "started_at": ts_start,
            "finished_at": ts_finish,
            "duration_seconds": duration,
            "execution_result": trace.get("script_execution", "unknown"),
            "trigger_type": self._extract_trigger_type(trigger_desc),
            "trigger_entity": self._extract_trigger_entity(trigger_desc),
            "error_message": trace.get("error") or "",
            "step_count": step_count,
            "last_step": trace.get("last_step", ""),
            "context_id": trace.get("context", {}).get("id", ""),
        }

    async def _post_executions_batch(self, executions: list[dict[str, Any]]):
        """POST all execution records in a single batch request."""
        try:
            session = await self._ensure_http_session()
            url = f"{config.DATA_API_URL}/internal/automations/executions/bulk_upsert"
            headers = {"Content-Type": "application/json"}
            if config.DATA_API_API_KEY:
                headers["Authorization"] = f"Bearer {config.DATA_API_API_KEY}"

            async with session.post(url, json=executions, headers=headers) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    logger.warning("data-api execution batch upsert failed (%d): %s", resp.status, body[:200])
                else:
                    logger.info("Batch upserted %d executions to data-api", len(executions))
        except Exception:
            logger.debug("Failed to POST execution batch to data-api", exc_info=True)

    async def _sync_automation_registry(self, automations: list[dict[str, Any]]):
        """Sync automation entity list to data-api /internal/automations/bulk_upsert."""
        if not automations:
            return
        try:
            session = await self._ensure_http_session()

            records = []
            for entity in automations:
                entity_id = entity.get("entity_id", "")
                records.append({
                    "automation_id": entity_id,
                    "alias": entity.get("name") or entity.get("original_name") or entity_id,
                    "enabled": entity.get("disabled_by") is None,
                })

            url = f"{config.DATA_API_URL}/internal/automations/bulk_upsert"
            headers = {"Content-Type": "application/json"}
            if config.DATA_API_API_KEY:
                headers["Authorization"] = f"Bearer {config.DATA_API_API_KEY}"

            async with session.post(url, json=records, headers=headers) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    logger.warning("data-api automation upsert failed (%d): %s", resp.status, body[:200])
                else:
                    logger.debug("Synced %d automations to data-api", len(records))
        except Exception:
            logger.debug("Failed to sync automation registry to data-api", exc_info=True)

    async def cleanup(self):
        """Close HTTP session."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_entity_id(item_id: str, automations: list[dict]) -> str:
        """Map trace item_id back to the automation entity_id."""
        for entity in automations:
            eid = entity.get("entity_id", "")
            # HA item_id is the numeric automation ID; entity_id is "automation.xxx"
            # Try matching by the slug part
            if eid == f"automation.{item_id}" or eid.endswith(f".{item_id}"):
                return eid
        # Fallback: use item_id directly
        return item_id

    @staticmethod
    def _extract_trigger_type(trigger_desc: str) -> str:
        desc = trigger_desc.lower()
        for keyword, ttype in [
            ("state of", "state"), ("time", "time"), ("event", "event"),
            ("mqtt", "mqtt"), ("webhook", "webhook"), ("sun", "sun"),
            ("zone", "zone"), ("numeric_state", "numeric_state"),
            ("template", "template"),
        ]:
            if keyword in desc:
                return ttype
        return "other"

    @staticmethod
    def _extract_trigger_entity(trigger_desc: str) -> str:
        if "state of " in trigger_desc:
            return trigger_desc.split("state of ")[-1].strip()
        return ""
