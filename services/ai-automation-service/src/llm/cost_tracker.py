"""
Cost Tracker for OpenAI API Usage

Tracks token usage and calculates costs based on OpenAI pricing.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class CostTracker:
    """Track OpenAI API costs"""
    
    # GPT-5.1 Model Pricing (as of November 2025) - VERIFIED
    # Source: OpenAI API Pricing (November 2025)
    # GPT-5.1: Best quality with 50% cost savings vs GPT-4o
    GPT5_1_INPUT_COST_PER_1M = 1.25  # $1.25 per 1M input tokens (50% cheaper than GPT-4o)
    GPT5_1_OUTPUT_COST_PER_1M = 10.00  # $10.00 per 1M output tokens (same as GPT-4o)
    GPT5_1_CACHED_INPUT_COST_PER_1M = 0.125  # $0.125 per 1M cached input tokens (90% discount)
    
    # GPT-4o Model Pricing (Legacy - as of 2024) - VERIFIED
    # Source: https://openai.com/api/pricing/
    # GPT-4o: Best quality for creative tasks
    GPT4O_INPUT_COST_PER_1M = 2.50  # $2.50 per 1M input tokens
    GPT4O_OUTPUT_COST_PER_1M = 10.00  # $10.00 per 1M output tokens
    GPT4O_CACHED_INPUT_COST_PER_1M = 0.25  # $0.25 per 1M cached input tokens (90% discount)
    
    # GPT-4o-mini: Cost savings, good for standard tasks (Legacy)
    GPT4O_MINI_INPUT_COST_PER_1M = 0.15  # $0.15 per 1M input tokens
    GPT4O_MINI_OUTPUT_COST_PER_1M = 0.60  # $0.60 per 1M output tokens
    GPT4O_MINI_CACHED_INPUT_COST_PER_1M = 0.015  # $0.015 per 1M cached input tokens (90% discount)
    
    # Default pricing (GPT-5.1 - current recommended)
    INPUT_COST_PER_1M = GPT5_1_INPUT_COST_PER_1M
    OUTPUT_COST_PER_1M = GPT5_1_OUTPUT_COST_PER_1M
    
    @staticmethod
    def get_model_pricing(model: str) -> Dict[str, float]:
        """
        Get pricing for a specific model.
        
        Args:
            model: Model name (gpt-5.1, gpt-4o, gpt-4o-mini)
        
        Returns:
            Dictionary with input_cost, output_cost, cached_input_cost per 1M tokens
        """
        model_lower = model.lower()
        if "gpt-5" in model_lower or "gpt5" in model_lower:
            # GPT-5.1 (current recommended - 50% cheaper than GPT-4o)
            return {
                'input': CostTracker.GPT5_1_INPUT_COST_PER_1M,
                'output': CostTracker.GPT5_1_OUTPUT_COST_PER_1M,
                'cached_input': CostTracker.GPT5_1_CACHED_INPUT_COST_PER_1M
            }
        elif "gpt-4o" in model_lower and "mini" not in model_lower:
            # GPT-4o (legacy full model)
            return {
                'input': CostTracker.GPT4O_INPUT_COST_PER_1M,
                'output': CostTracker.GPT4O_OUTPUT_COST_PER_1M,
                'cached_input': CostTracker.GPT4O_CACHED_INPUT_COST_PER_1M
            }
        elif "mini" in model_lower:
            # GPT-4o-mini (legacy)
            return {
                'input': CostTracker.GPT4O_MINI_INPUT_COST_PER_1M,
                'output': CostTracker.GPT4O_MINI_OUTPUT_COST_PER_1M,
                'cached_input': CostTracker.GPT4O_MINI_CACHED_INPUT_COST_PER_1M
            }
        else:
            # Default to GPT-5.1 (current recommended)
            return {
                'input': CostTracker.GPT5_1_INPUT_COST_PER_1M,
                'output': CostTracker.GPT5_1_OUTPUT_COST_PER_1M,
                'cached_input': CostTracker.GPT5_1_CACHED_INPUT_COST_PER_1M
            }
    
    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-5.1", cached_input: bool = False) -> float:
        """
        Calculate cost in USD for token usage.
        
        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            model: Model name (gpt-5.1, gpt-4o, gpt-4o-mini) - defaults to gpt-5.1
            cached_input: Whether input tokens are cached (90% discount)
        
        Returns:
            Total cost in USD
        """
        pricing = CostTracker.get_model_pricing(model)
        input_cost_per_1m = pricing['cached_input'] if cached_input else pricing['input']
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost
        
        logger.debug(
            f"Cost calculation ({model}, cached={cached_input}): "
            f"{input_tokens} input + {output_tokens} output = ${total_cost:.4f}"
        )
        
        return total_cost
    
    @staticmethod
    def estimate_monthly_cost(suggestions_per_day: int, avg_tokens_per_suggestion: int = 800) -> Dict:
        """
        Estimate monthly cost based on daily suggestion volume.
        
        Args:
            suggestions_per_day: Number of suggestions generated per day
            avg_tokens_per_suggestion: Average total tokens per suggestion
        
        Returns:
            Dictionary with cost estimates
        """
        # Assume 60% input, 40% output (typical ratio)
        input_tokens = int(avg_tokens_per_suggestion * 0.6)
        output_tokens = int(avg_tokens_per_suggestion * 0.4)
        
        cost_per_suggestion = CostTracker.calculate_cost(input_tokens, output_tokens)
        daily_cost = cost_per_suggestion * suggestions_per_day
        monthly_cost = daily_cost * 30
        
        return {
            'suggestions_per_day': suggestions_per_day,
            'avg_tokens_per_suggestion': avg_tokens_per_suggestion,
            'cost_per_suggestion_usd': round(cost_per_suggestion, 4),
            'daily_cost_usd': round(daily_cost, 2),
            'monthly_cost_usd': round(monthly_cost, 2),
            'assumptions': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'days_per_month': 30
            }
        }
    
    @staticmethod
    def check_budget_alert(total_cost: float, budget: float = 10.0) -> Dict:
        """
        Check if cost is approaching budget and return alert info.
        
        Args:
            total_cost: Current total cost
            budget: Monthly budget in USD (default: $10)
        
        Returns:
            Dictionary with alert status and details
        """
        usage_percent = (total_cost / budget) * 100
        
        alert_level = "ok"
        if usage_percent >= 90:
            alert_level = "critical"
        elif usage_percent >= 75:
            alert_level = "warning"
        elif usage_percent >= 50:
            alert_level = "info"
        
        return {
            'alert_level': alert_level,
            'total_cost_usd': round(total_cost, 2),
            'budget_usd': budget,
            'usage_percent': round(usage_percent, 1),
            'remaining_usd': round(budget - total_cost, 2),
            'should_alert': alert_level in ['warning', 'critical']
        }
    
    @staticmethod
    def is_local_model(model_name: str) -> bool:
        """
        Check if model is local (no API cost).
        
        Returns True for:
        - HuggingFace models (dslim/bert-base-NER, etc.)
        - SentenceTransformer models (all-MiniLM-L6-v2, etc.)
        - Pattern matching (no model)
        - spaCy models
        
        Args:
            model_name: Model identifier string
        
        Returns:
            True if model is local (no API cost), False otherwise
        """
        if not model_name:
            return True
        
        model_lower = model_name.lower()
        local_indicators = [
            'huggingface', 'sentence-transformers', 'transformers',
            'pattern', 'spacy', 'bert', 'roberta', 'dslim',
            'all-minilm', 'sentence_transformer'
        ]
        return any(indicator in model_lower for indicator in local_indicators)
    
    @staticmethod
    def estimate_monthly_cost_per_model(
        model_name: str,
        requests_per_day: int,
        avg_input_tokens: int = 0,
        avg_output_tokens: int = 0
    ) -> float:
        """
        Estimate monthly cost for a model.
        
        Returns 0.0 for local models (HuggingFace, SentenceTransformers, etc.)
        
        Args:
            model_name: Model identifier
            requests_per_day: Average number of requests per day
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request
        
        Returns:
            Estimated monthly cost in USD
        """
        if CostTracker.is_local_model(model_name):
            return 0.0
        
        total_input_tokens = avg_input_tokens * requests_per_day * 30
        total_output_tokens = avg_output_tokens * requests_per_day * 30
        
        return CostTracker.calculate_cost(
            total_input_tokens,
            total_output_tokens,
            model=model_name
        )

