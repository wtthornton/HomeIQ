"""
MetricsBuffer — Rolling in-memory per-minute metrics for analytics.

Stores per-minute aggregated snapshots of API response times, InfluxDB query
latencies, and error rates.  Queried by the analytics endpoint to produce
real time-series data instead of mock random numbers.

The buffer holds up to 10 080 minute-buckets (7 days).  Data resets on
service restart — this is acceptable for operational dashboards.
"""

import re
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class MinuteBucket:
    """Aggregated metrics for a single minute."""

    timestamp: datetime  # minute boundary (seconds/micros = 0)

    # Request metrics
    request_count: int = 0
    error_count: int = 0
    response_time_sum: float = 0.0
    response_time_count: int = 0
    response_time_min: float = float("inf")
    response_time_max: float = 0.0

    # InfluxDB query metrics
    db_query_sum: float = 0.0
    db_query_count: int = 0
    db_query_min: float = float("inf")
    db_query_max: float = 0.0

    # Derived helpers --------------------------------------------------
    @property
    def avg_response_time(self) -> float:
        return self.response_time_sum / self.response_time_count if self.response_time_count else 0.0

    @property
    def avg_db_latency(self) -> float:
        return self.db_query_sum / self.db_query_count if self.db_query_count else 0.0

    @property
    def error_rate(self) -> float:
        return (self.error_count / self.request_count * 100) if self.request_count else 0.0


_INTERVAL_RE = re.compile(r"(\d+)([mhd])")


def _parse_interval(interval: str) -> timedelta:
    """Parse interval string like '1m', '5m', '2h' into timedelta."""
    m = _INTERVAL_RE.match(interval)
    if not m:
        return timedelta(minutes=1)
    value, unit = int(m.group(1)), m.group(2)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    return timedelta(days=value)


class MetricsBuffer:
    """Thread-safe rolling per-minute metrics buffer.

    Call ``record_request`` from the HTTP middleware and
    ``record_db_query`` from the InfluxDB query callback.
    The analytics endpoint reads via ``get_series``.
    """

    MAX_MINUTES = 10_080  # 7 days

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshots: deque[MinuteBucket] = deque(maxlen=self.MAX_MINUTES)
        self._current: MinuteBucket | None = None

    # -- Recording -----------------------------------------------------

    def _minute_boundary(self) -> datetime:
        return datetime.now(timezone.utc).replace(second=0, microsecond=0)

    def _ensure_current(self) -> MinuteBucket:
        now = self._minute_boundary()
        if self._current is None or self._current.timestamp != now:
            if self._current is not None:
                self._snapshots.append(self._current)
            self._current = MinuteBucket(timestamp=now)
        return self._current

    def record_request(self, response_time_ms: float, is_error: bool) -> None:
        with self._lock:
            b = self._ensure_current()
            b.request_count += 1
            if is_error:
                b.error_count += 1
            b.response_time_sum += response_time_ms
            b.response_time_count += 1
            if response_time_ms < b.response_time_min:
                b.response_time_min = response_time_ms
            if response_time_ms > b.response_time_max:
                b.response_time_max = response_time_ms

    def record_db_query(self, latency_ms: float) -> None:
        with self._lock:
            b = self._ensure_current()
            b.db_query_sum += latency_ms
            b.db_query_count += 1
            if latency_ms < b.db_query_min:
                b.db_query_min = latency_ms
            if latency_ms > b.db_query_max:
                b.db_query_max = latency_ms

    # -- Querying ------------------------------------------------------

    def get_series(
        self,
        metric: str,
        start_time: str,
        interval: str,
        num_points: int,
    ) -> list[dict[str, Any]]:
        """Return aggregated time-series for *metric*.

        Parameters
        ----------
        metric : str
            One of ``'response_time'``, ``'db_latency'``, ``'error_rate'``.
        start_time : str
            ISO-8601 start timestamp.
        interval : str
            Aggregation window, e.g. ``'1m'``, ``'5m'``, ``'15m'``, ``'2h'``.
        num_points : int
            Number of data points to return.

        Returns
        -------
        list[dict]
            ``[{"timestamp": "...", "value": float}, ...]``
        """
        interval_td = _parse_interval(interval)
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        # Snapshot the current state under lock
        with self._lock:
            all_buckets: list[MinuteBucket] = list(self._snapshots)
            if self._current is not None:
                all_buckets.append(self._current)

        # Index buckets by minute for fast lookup
        bucket_map: dict[datetime, MinuteBucket] = {b.timestamp: b for b in all_buckets}

        # Build output series
        series: list[dict[str, Any]] = []
        for i in range(num_points):
            window_start = start_dt + interval_td * i
            window_end = window_start + interval_td

            # Collect minute-buckets that fall inside this window
            value = self._aggregate_window(metric, bucket_map, window_start, window_end)

            series.append({
                "timestamp": window_start.isoformat() + ("Z" if window_start.tzinfo else ""),
                "value": round(value, 4),
            })

        return series

    @staticmethod
    def _aggregate_window(
        metric: str,
        bucket_map: dict[datetime, MinuteBucket],
        window_start: datetime,
        window_end: datetime,
    ) -> float:
        """Aggregate minute-buckets within [window_start, window_end)."""
        # Iterate through each minute in the window
        t = window_start.replace(second=0, microsecond=0)
        one_min = timedelta(minutes=1)

        total_requests = 0
        total_errors = 0
        rt_sum = 0.0
        rt_count = 0
        db_sum = 0.0
        db_count = 0

        while t < window_end:
            bucket = bucket_map.get(t)
            if bucket is not None:
                total_requests += bucket.request_count
                total_errors += bucket.error_count
                rt_sum += bucket.response_time_sum
                rt_count += bucket.response_time_count
                db_sum += bucket.db_query_sum
                db_count += bucket.db_query_count
            t += one_min

        if metric == "response_time":
            return rt_sum / rt_count if rt_count else 0.0
        if metric == "db_latency":
            return db_sum / db_count if db_count else 0.0
        if metric == "error_rate":
            return (total_errors / total_requests * 100) if total_requests else 0.0
        return 0.0
