"""
Performance monitoring for Multi-Model Entity Extraction
Tracks costs, accuracy, and performance metrics
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class ExtractionMetrics:
    """Metrics for entity extraction performance"""
    timestamp: datetime
    query: str
    method_used: str  # ner, openai, pattern
    processing_time: float
    entities_found: int
    confidence_score: float
    cost_usd: float = 0.0
    error: str = None

class MultiModelPerformanceMonitor:
    """Monitor performance and costs for multi-model entity extraction"""

    def __init__(self, log_file: str = "/app/data/extraction_metrics.jsonl"):
        self.log_file = log_file
        self.metrics: list[ExtractionMetrics] = []
        self.daily_stats = {}

        # Cost tracking (USD)
        self.openai_cost_per_token = 0.0004 / 1000  # GPT-4o-mini pricing
        self.ner_cost = 0.0  # Free
        self.pattern_cost = 0.0  # Free

    def log_extraction(self,
                      query: str,
                      method_used: str,
                      processing_time: float,
                      entities_found: int,
                      confidence_score: float,
                      tokens_used: int = 0,
                      error: str | None = None):
        """Log extraction metrics"""

        # Calculate cost
        cost = 0.0
        if method_used == "openai":
            cost = tokens_used * self.openai_cost_per_token
        elif method_used in {"ner", "pattern"}:
            cost = 0.0  # Free

        metric = ExtractionMetrics(
            timestamp=datetime.now(),
            query=query,
            method_used=method_used,
            processing_time=processing_time,
            entities_found=entities_found,
            confidence_score=confidence_score,
            cost_usd=cost,
            error=error,
        )

        self.metrics.append(metric)

        # Log to file
        self._log_to_file(metric)

        # Update daily stats
        self._update_daily_stats(metric)

        logger.debug(f"Logged extraction: {method_used} in {processing_time:.3f}s, cost: ${cost:.6f}")

    def _log_to_file(self, metric: ExtractionMetrics):
        """Log metric to JSONL file"""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(asdict(metric), default=str) + "\n")
        except Exception as e:
            logger.exception(f"Failed to log metric to file: {e}")

    def _update_daily_stats(self, metric: ExtractionMetrics):
        """Update daily statistics"""
        today = metric.timestamp.date()
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                "total_queries": 0,
                "ner_queries": 0,
                "openai_queries": 0,
                "pattern_queries": 0,
                "total_cost": 0.0,
                "avg_processing_time": 0.0,
                "avg_confidence": 0.0,
                "errors": 0,
            }

        stats = self.daily_stats[today]
        stats["total_queries"] += 1
        stats[f"{metric.method_used}_queries"] += 1
        stats["total_cost"] += metric.cost_usd
        stats["errors"] += 1 if metric.error else 0

        # Update averages
        total = stats["total_queries"]
        stats["avg_processing_time"] = (
            (stats["avg_processing_time"] * (total - 1) + metric.processing_time) / total
        )
        stats["avg_confidence"] = (
            (stats["avg_confidence"] * (total - 1) + metric.confidence_score) / total
        )

    def get_daily_summary(self, date: datetime | None = None) -> dict[str, Any]:
        """Get daily performance summary"""
        if date is None:
            date = datetime.now().date()

        if date not in self.daily_stats:
            return {
                "date": date.isoformat(),
                "total_queries": 0,
                "ner_queries": 0,
                "openai_queries": 0,
                "pattern_queries": 0,
                "total_cost": 0.0,
                "avg_processing_time": 0.0,
                "avg_confidence": 0.0,
                "errors": 0,
                "ner_success_rate": 0.0,
                "openai_success_rate": 0.0,
                "pattern_fallback_rate": 0.0,
            }

        stats = self.daily_stats[date].copy()
        stats["date"] = date.isoformat()

        total = stats["total_queries"]
        if total > 0:
            stats["ner_success_rate"] = stats["ner_queries"] / total
            stats["openai_success_rate"] = stats["openai_queries"] / total
            stats["pattern_fallback_rate"] = stats["pattern_queries"] / total
        else:
            stats["ner_success_rate"] = 0.0
            stats["openai_success_rate"] = 0.0
            stats["pattern_fallback_rate"] = 0.0

        return stats

    def get_weekly_summary(self) -> dict[str, Any]:
        """Get weekly performance summary"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        weekly_stats = {
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
            "total_queries": 0,
            "ner_queries": 0,
            "openai_queries": 0,
            "pattern_queries": 0,
            "total_cost": 0.0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
            "errors": 0,
            "daily_breakdown": [],
        }

        for date in [start_date + timedelta(days=i) for i in range(7)]:
            daily = self.get_daily_summary(date)
            weekly_stats["daily_breakdown"].append(daily)

            weekly_stats["total_queries"] += daily["total_queries"]
            weekly_stats["ner_queries"] += daily["ner_queries"]
            weekly_stats["openai_queries"] += daily["openai_queries"]
            weekly_stats["pattern_queries"] += daily["pattern_queries"]
            weekly_stats["total_cost"] += daily["total_cost"]
            weekly_stats["errors"] += daily["errors"]

        # Calculate averages
        total = weekly_stats["total_queries"]
        if total > 0:
            weekly_stats["ner_success_rate"] = weekly_stats["ner_queries"] / total
            weekly_stats["openai_success_rate"] = weekly_stats["openai_queries"] / total
            weekly_stats["pattern_fallback_rate"] = weekly_stats["pattern_queries"] / total

            # Weighted averages
            total_time = sum(d["avg_processing_time"] * d["total_queries"]
                           for d in weekly_stats["daily_breakdown"] if d["total_queries"] > 0)
            total_confidence = sum(d["avg_confidence"] * d["total_queries"]
                                 for d in weekly_stats["daily_breakdown"] if d["total_queries"] > 0)

            weekly_stats["avg_processing_time"] = total_time / total if total > 0 else 0.0
            weekly_stats["avg_confidence"] = total_confidence / total if total > 0 else 0.0
        else:
            weekly_stats["ner_success_rate"] = 0.0
            weekly_stats["openai_success_rate"] = 0.0
            weekly_stats["pattern_fallback_rate"] = 0.0
            weekly_stats["avg_processing_time"] = 0.0
            weekly_stats["avg_confidence"] = 0.0

        return weekly_stats

    def get_cost_analysis(self, days: int = 30) -> dict[str, Any]:
        """Analyze costs over specified period"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        total_cost = 0.0
        openai_cost = 0.0
        ner_cost = 0.0
        pattern_cost = 0.0
        total_queries = 0

        for date in [start_date + timedelta(days=i) for i in range(days)]:
            if date in self.daily_stats:
                stats = self.daily_stats[date]
                total_cost += stats["total_cost"]
                total_queries += stats["total_queries"]

                # Estimate costs by method
                stats["openai_queries"]
                stats["ner_queries"]
                stats["pattern_queries"]

                # OpenAI cost is already calculated
                openai_cost += stats["total_cost"]  # All cost is from OpenAI
                ner_cost += 0.0  # Free
                pattern_cost += 0.0  # Free

        return {
            "period_days": days,
            "total_queries": total_queries,
            "total_cost_usd": total_cost,
            "avg_cost_per_query": total_cost / total_queries if total_queries > 0 else 0.0,
            "openai_cost_usd": openai_cost,
            "ner_cost_usd": ner_cost,
            "pattern_cost_usd": pattern_cost,
            "monthly_projection": total_cost * (30 / days) if days > 0 else 0.0,
            "cost_breakdown": {
                "openai_percentage": (openai_cost / total_cost * 100) if total_cost > 0 else 0.0,
                "ner_percentage": 0.0,  # Always 0%
                "pattern_percentage": 0.0,  # Always 0%
            },
        }

    def export_metrics(self, output_file: str | None = None) -> str:
        """Export metrics to JSON file"""
        if output_file is None:
            output_file = f"/app/data/extraction_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_metrics": len(self.metrics),
            "daily_stats": self.daily_stats,
            "weekly_summary": self.get_weekly_summary(),
            "cost_analysis_30d": self.get_cost_analysis(30),
            "metrics": [asdict(m) for m in self.metrics[-1000:]],  # Last 1000 metrics
        }

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Metrics exported to {output_file}")
        return output_file

# Global monitor instance
performance_monitor = MultiModelPerformanceMonitor()
