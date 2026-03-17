"""Parser for Zeek flowmeter.log — ML-ready traffic features.

Reads JSON lines from flowmeter.log (produced by zeek-flowmeter package),
extracts flow statistics, and exposes them for ml-service consumption.
Features include packet sizes, inter-arrival times, flow duration, and
byte/packet ratios that are standard inputs for network ML models.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeiq_observability.logging_config import setup_logging

if TYPE_CHECKING:
    from ..services.log_tracker import LogTracker

logger = setup_logging("zeek-flowmeter-parser")

# ML feature keys extracted from flowmeter.log
_FLOW_FEATURES = [
    "duration",
    "fwd_pkts_tot",
    "bwd_pkts_tot",
    "fwd_data_pkts_tot",
    "bwd_data_pkts_tot",
    "fwd_pkts_per_sec",
    "bwd_pkts_per_sec",
    "flow_pkts_per_sec",
    "down_up_ratio",
    "fwd_header_size_tot",
    "fwd_header_size_min",
    "fwd_header_size_max",
    "bwd_header_size_tot",
    "bwd_header_size_min",
    "bwd_header_size_max",
    "flow_FIN_flag_count",
    "flow_SYN_flag_count",
    "flow_RST_flag_count",
    "fwd_PSH_flag_count",
    "bwd_PSH_flag_count",
    "flow_ACK_flag_count",
    "fwd_URG_flag_count",
    "bwd_URG_flag_count",
    "flow_CWR_flag_count",
    "flow_ECE_flag_count",
    "fwd_pkts_payload.min",
    "fwd_pkts_payload.max",
    "fwd_pkts_payload.tot",
    "fwd_pkts_payload.avg",
    "fwd_pkts_payload.std",
    "bwd_pkts_payload.min",
    "bwd_pkts_payload.max",
    "bwd_pkts_payload.tot",
    "bwd_pkts_payload.avg",
    "bwd_pkts_payload.std",
    "flow_pkts_payload.min",
    "flow_pkts_payload.max",
    "flow_pkts_payload.tot",
    "flow_pkts_payload.avg",
    "flow_pkts_payload.std",
    "fwd_iat.min",
    "fwd_iat.max",
    "fwd_iat.tot",
    "fwd_iat.avg",
    "fwd_iat.std",
    "bwd_iat.min",
    "bwd_iat.max",
    "bwd_iat.tot",
    "bwd_iat.avg",
    "bwd_iat.std",
    "flow_iat.min",
    "flow_iat.max",
    "flow_iat.tot",
    "flow_iat.avg",
    "flow_iat.std",
    "payload_bytes_per_second",
    "fwd_subflow_pkts",
    "bwd_subflow_pkts",
    "fwd_subflow_bytes",
    "bwd_subflow_bytes",
    "fwd_bulk_bytes",
    "bwd_bulk_bytes",
    "fwd_bulk_packets",
    "bwd_bulk_packets",
    "fwd_bulk_rate",
    "bwd_bulk_rate",
    "active.min",
    "active.max",
    "active.tot",
    "active.avg",
    "active.std",
    "idle.min",
    "idle.max",
    "idle.tot",
    "idle.avg",
    "idle.std",
]


class FlowmeterParser:
    """Parses Zeek flowmeter.log for ML-ready traffic features."""

    def __init__(
        self,
        log_tracker: LogTracker,
        service: object,
    ) -> None:
        self._log_tracker = log_tracker
        self._service = service

        # Stats
        self.flows_parsed: int = 0

        # Recent flow features for ML feed (bounded buffer)
        self._recent_flows: list[dict[str, Any]] = []
        self._max_flows = 5000

    async def run(self, interval: int) -> None:
        """Background loop: parse flowmeter.log every ``interval`` seconds."""
        logger.info("Starting flowmeter parser (every %ds)", interval)
        while True:
            try:
                await self._parse_cycle()
            except asyncio.CancelledError:
                logger.info("Flowmeter parser cancelled")
                raise
            except Exception as e:
                logger.error("Flowmeter parse error: %s", e)
            await asyncio.sleep(interval)

    async def _parse_cycle(self) -> None:
        """Read new lines from flowmeter.log and extract features."""
        lines = self._log_tracker.read_new_lines("flowmeter.log")
        if not lines:
            return

        for line in lines:
            features = self._parse_line(line)
            if features:
                self._recent_flows.append(features)
                self.flows_parsed += 1

        # Bound buffer
        if len(self._recent_flows) > self._max_flows:
            self._recent_flows = self._recent_flows[-self._max_flows :]

        self._log_tracker.save_offsets()

    def _parse_line(self, line: str) -> dict[str, Any] | None:
        """Parse a single flowmeter.log JSON line into ML features."""
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None

        # Connection identifiers
        src_ip = entry.get("id.orig_h", "")
        dst_ip = entry.get("id.resp_h", "")
        if not src_ip or not dst_ip:
            return None

        ts_value = entry.get("ts")
        timestamp = (
            datetime.fromtimestamp(float(ts_value), tz=UTC).isoformat()
            if ts_value
            else datetime.now(UTC).isoformat()
        )

        # Extract ML features
        features: dict[str, Any] = {
            "timestamp": timestamp,
            "src_ip": src_ip,
            "src_port": entry.get("id.orig_p", 0),
            "dst_ip": dst_ip,
            "dst_port": entry.get("id.resp_p", 0),
            "proto": entry.get("proto", ""),
        }

        for key in _FLOW_FEATURES:
            val = entry.get(key)
            if val is not None:
                features[key] = float(val) if isinstance(val, (int, float)) else val

        return features

    def get_recent_flows(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent flow features for ML service consumption."""
        return self._recent_flows[-limit:]

    def get_ml_feed(self, since_index: int = 0) -> dict[str, Any]:
        """Get flow features for ML service feed.

        Args:
            since_index: Return flows after this index (for incremental fetching).

        Returns:
            Dict with features list and next index for pagination.
        """
        flows = self._recent_flows[since_index:]
        return {
            "flows": flows,
            "next_index": len(self._recent_flows),
            "total_parsed": self.flows_parsed,
        }
