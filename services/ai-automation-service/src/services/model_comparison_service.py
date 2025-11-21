"""
Model Comparison Service

Aggregates statistics from all model usage sources and provides comparison
and recommendation capabilities.

Collects data from:
- OpenAIClient instances (multiple models)
- MultiModelEntityExtractor
- DescriptionGenerator
- SuggestionRefiner
"""

import logging
from collections import defaultdict
from typing import Any

from ..llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class ModelComparisonService:
    """
    Service to aggregate and compare model usage statistics.

    Collects stats from all tracking sources and provides:
    - Per-model aggregated statistics
    - Model comparison
    - Recommendations
    - Cost analysis
    """

    def __init__(
        self,
        openai_client=None,
        multi_model_extractor=None,
        description_generator=None,
        suggestion_refiner=None,
    ):
        """
        Initialize model comparison service.

        Args:
            openai_client: OpenAIClient instance (optional)
            multi_model_extractor: MultiModelEntityExtractor instance (optional)
            description_generator: DescriptionGenerator instance (optional)
            suggestion_refiner: SuggestionRefiner instance (optional)
        """
        self.openai_client = openai_client
        self.multi_model_extractor = multi_model_extractor
        self.description_generator = description_generator
        self.suggestion_refiner = suggestion_refiner

    def get_all_model_stats(self) -> dict[str, dict[str, Any]]:
        """
        Collect and aggregate statistics from all sources.

        Returns:
            Dictionary mapping model_name -> aggregated stats
        """
        aggregated = defaultdict(lambda: {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "sources": [],
        })

        # Collect from OpenAIClient
        if self.openai_client:
            try:
                stats = self.openai_client.get_usage_stats()
                model_breakdown = stats.get("model_breakdown", {})

                for model_name, model_stats in model_breakdown.items():
                    aggregated[model_name]["total_requests"] += model_stats.get("calls", 0)
                    aggregated[model_name]["total_input_tokens"] += model_stats.get("input_tokens", 0)
                    aggregated[model_name]["total_output_tokens"] += model_stats.get("output_tokens", 0)
                    aggregated[model_name]["total_cost_usd"] += model_stats.get("cost_usd", 0.0)
                    aggregated[model_name]["sources"].append("OpenAIClient")

                # Also include the primary model from OpenAIClient
                primary_model = stats.get("model")
                if primary_model and primary_model not in model_breakdown:
                    # If model not in breakdown, use total stats
                    aggregated[primary_model]["total_requests"] += sum(
                        ep.get("calls", 0) for ep in stats.get("endpoint_breakdown", {}).values()
                    )
                    aggregated[primary_model]["total_input_tokens"] += stats.get("input_tokens", 0)
                    aggregated[primary_model]["total_output_tokens"] += stats.get("output_tokens", 0)
                    aggregated[primary_model]["total_cost_usd"] += stats.get("total_cost_usd", 0.0)
                    aggregated[primary_model]["sources"].append("OpenAIClient")
            except Exception as e:
                logger.warning(f"Failed to collect stats from OpenAIClient: {e}")

        # Collect from MultiModelEntityExtractor
        if self.multi_model_extractor:
            try:
                stats = self.multi_model_extractor.get_stats()
                models = stats.get("models", {})

                for model_type, model_info in models.items():
                    model_name = model_info.get("model_name", model_type)
                    calls = model_info.get("calls", 0)
                    cost = model_info.get("cost_usd", 0.0)

                    aggregated[model_name]["total_requests"] += calls
                    aggregated[model_name]["total_cost_usd"] += cost
                    aggregated[model_name]["sources"].append(f"MultiModelEntityExtractor.{model_type}")
            except Exception as e:
                logger.warning(f"Failed to collect stats from MultiModelEntityExtractor: {e}")

        # Collect from DescriptionGenerator
        if self.description_generator:
            try:
                stats = self.description_generator.get_usage_stats()
                model_name = stats.get("model", "gpt-4o-mini")

                # Estimate requests from tokens (rough estimate)
                # We don't track requests separately, so estimate based on usage
                if stats.get("total_tokens", 0) > 0:
                    # Rough estimate: average 200 tokens per description
                    estimated_requests = max(1, stats.get("total_tokens", 0) // 200)
                    aggregated[model_name]["total_requests"] += estimated_requests

                aggregated[model_name]["total_input_tokens"] += stats.get("input_tokens", 0)
                aggregated[model_name]["total_output_tokens"] += stats.get("output_tokens", 0)
                aggregated[model_name]["total_cost_usd"] += stats.get("total_cost_usd", 0.0)
                aggregated[model_name]["sources"].append("DescriptionGenerator")
            except Exception as e:
                logger.warning(f"Failed to collect stats from DescriptionGenerator: {e}")

        # Collect from SuggestionRefiner
        if self.suggestion_refiner:
            try:
                stats = self.suggestion_refiner.get_usage_stats()
                model_name = stats.get("model", "gpt-4o-mini")

                # Estimate requests from tokens (rough estimate)
                if stats.get("total_tokens", 0) > 0:
                    estimated_requests = max(1, stats.get("total_tokens", 0) // 200)
                    aggregated[model_name]["total_requests"] += estimated_requests

                aggregated[model_name]["total_input_tokens"] += stats.get("input_tokens", 0)
                aggregated[model_name]["total_output_tokens"] += stats.get("output_tokens", 0)
                aggregated[model_name]["total_cost_usd"] += stats.get("total_cost_usd", 0.0)
                aggregated[model_name]["sources"].append("SuggestionRefiner")
            except Exception as e:
                logger.warning(f"Failed to collect stats from SuggestionRefiner: {e}")

        # Calculate derived metrics
        result = {}
        for model_name, stats in aggregated.items():
            total_requests = stats["total_requests"]
            total_cost = stats["total_cost_usd"]

            result[model_name] = {
                "model_name": model_name,
                "total_requests": total_requests,
                "total_input_tokens": stats["total_input_tokens"],
                "total_output_tokens": stats["total_output_tokens"],
                "total_tokens": stats["total_input_tokens"] + stats["total_output_tokens"],
                "total_cost_usd": round(total_cost, 4),
                "avg_cost_per_request": round(total_cost / total_requests, 4) if total_requests > 0 else 0.0,
                "avg_input_tokens": round(stats["total_input_tokens"] / total_requests, 2) if total_requests > 0 else 0,
                "avg_output_tokens": round(stats["total_output_tokens"] / total_requests, 2) if total_requests > 0 else 0,
                "is_local": CostTracker.is_local_model(model_name),
                "sources": list(set(stats["sources"])),  # Unique sources
            }

        return result

    def compare_models(self) -> dict[str, Any]:
        """
        Compare all models side-by-side.

        Returns:
            Dictionary with comparison data
        """
        model_stats = self.get_all_model_stats()

        if not model_stats:
            return {
                "models": [],
                "summary": {
                    "total_models": 0,
                    "total_requests": 0,
                    "total_cost_usd": 0.0,
                },
            }

        # Calculate summary
        total_requests = sum(s["total_requests"] for s in model_stats.values())
        total_cost = sum(s["total_cost_usd"] for s in model_stats.values())

        # Sort by total requests (most used first)
        sorted_models = sorted(
            model_stats.values(),
            key=lambda x: x["total_requests"],
            reverse=True,
        )

        return {
            "models": sorted_models,
            "summary": {
                "total_models": len(model_stats),
                "total_requests": total_requests,
                "total_cost_usd": round(total_cost, 4),
                "avg_cost_per_request": round(total_cost / total_requests, 4) if total_requests > 0 else 0.0,
            },
        }

    def calculate_recommendations(self) -> dict[str, Any]:
        """
        Calculate model recommendations based on usage and cost.

        Returns:
            Dictionary with recommendations
        """
        model_stats = self.get_all_model_stats()

        if not model_stats:
            return {
                "best_overall": None,
                "best_cost": None,
                "best_quality": None,
                "reasoning": {},
                "cost_savings_opportunities": [],
            }

        # Filter out models with no usage
        active_models = {k: v for k, v in model_stats.items() if v["total_requests"] > 0}

        if not active_models:
            return {
                "best_overall": None,
                "best_cost": None,
                "best_quality": None,
                "reasoning": {},
                "cost_savings_opportunities": [],
            }

        # Best Overall: Highest usage with reasonable cost
        best_overall = max(
            active_models.items(),
            key=lambda x: x[1]["total_requests"] * (1.0 - min(x[1]["avg_cost_per_request"] / 0.10, 1.0)),
        )[0]

        # Best Cost: Lowest cost per request (excluding local models for comparison)
        paid_models = {k: v for k, v in active_models.items() if not v["is_local"]}
        best_cost = min(paid_models.items(), key=lambda x: x[1]["avg_cost_per_request"])[0] if paid_models else None

        # Best Quality: Highest usage (proxy for quality - more usage = better quality)
        best_quality = max(active_models.items(), key=lambda x: x[1]["total_requests"])[0]

        # Cost savings opportunities
        cost_savings = []
        if len(paid_models) > 1:
            # Find models with similar usage but higher cost
            sorted_paid = sorted(paid_models.items(), key=lambda x: x[1]["avg_cost_per_request"])

            for _i, (model_name, stats) in enumerate(sorted_paid[1:], 1):
                cheaper_model = sorted_paid[0][0]
                cheaper_stats = sorted_paid[0][1]

                if stats["avg_cost_per_request"] > cheaper_stats["avg_cost_per_request"] * 1.5:
                    savings_percent = (
                        (stats["avg_cost_per_request"] - cheaper_stats["avg_cost_per_request"]) /
                        stats["avg_cost_per_request"] * 100
                    )

                    cost_savings.append({
                        "current_model": model_name,
                        "recommended_model": cheaper_model,
                        "potential_savings_percent": round(savings_percent, 1),
                        "quality_impact": "minimal" if stats["total_requests"] < cheaper_stats["total_requests"] * 2 else "unknown",
                        "reasoning": f"{cheaper_model} costs {savings_percent:.1f}% less per request",
                    })

        reasoning = {
            "best_overall": f"{best_overall} has the best balance of usage and cost",
            "best_cost": f"{best_cost} has the lowest cost per request" if best_cost else "All models are local (free)",
            "best_quality": f"{best_quality} is used most frequently (proxy for quality)",
        }

        return {
            "best_overall": best_overall,
            "best_cost": best_cost,
            "best_quality": best_quality,
            "reasoning": reasoning,
            "cost_savings_opportunities": cost_savings,
        }

    def calculate_cost_impact(self, model_name: str, requests_per_day: int) -> dict[str, Any]:
        """
        Calculate cost impact for a specific model and usage pattern.

        Args:
            model_name: Model to analyze
            requests_per_day: Expected daily requests

        Returns:
            Dictionary with cost analysis
        """
        model_stats = self.get_all_model_stats()
        model_info = model_stats.get(model_name, {})

        if not model_info:
            return {
                "model_name": model_name,
                "error": "Model not found in usage statistics",
            }

        # Calculate monthly cost
        avg_input = model_info.get("avg_input_tokens", 0)
        avg_output = model_info.get("avg_output_tokens", 0)

        monthly_cost = CostTracker.estimate_monthly_cost_per_model(
            model_name,
            requests_per_day,
            int(avg_input),
            int(avg_output),
        )

        return {
            "model_name": model_name,
            "requests_per_day": requests_per_day,
            "estimated_monthly_cost_usd": round(monthly_cost, 2),
            "avg_cost_per_request": model_info.get("avg_cost_per_request", 0.0),
            "is_local": model_info.get("is_local", False),
        }

