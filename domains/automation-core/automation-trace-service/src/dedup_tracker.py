"""
Deduplication tracker for automation trace run_ids.

Keeps an in-memory set of seen run_ids per automation to avoid
re-fetching traces we've already stored. Bounded to prevent
unbounded memory growth.
"""

import logging

logger = logging.getLogger(__name__)


class DedupTracker:
    """Track which trace run_ids have already been captured."""

    def __init__(self, max_per_automation: int = 50):
        self._seen: dict[str, set[str]] = {}
        self.max_per_automation = max_per_automation
        self.total_deduped = 0

    def filter_new(self, automation_id: str, traces: list[dict]) -> list[dict]:
        """Return only traces whose run_id has not been seen yet."""
        seen = self._seen.get(automation_id, set())
        new_traces = [t for t in traces if t.get("run_id") not in seen]
        self.total_deduped += len(traces) - len(new_traces)
        return new_traces

    def mark_seen(self, automation_id: str, traces: list[dict]):
        """Record run_ids as seen. Trims oldest if over limit."""
        if automation_id not in self._seen:
            self._seen[automation_id] = set()

        for t in traces:
            run_id = t.get("run_id")
            if run_id:
                self._seen[automation_id].add(run_id)

        # Trim to bounded size (keep most recent by sort order)
        if len(self._seen[automation_id]) > self.max_per_automation:
            sorted_ids = sorted(self._seen[automation_id])
            self._seen[automation_id] = set(sorted_ids[-self.max_per_automation :])

    @property
    def tracked_automation_count(self) -> int:
        return len(self._seen)

    @property
    def total_tracked_runs(self) -> int:
        return sum(len(v) for v in self._seen.values())
