"""
Success Metrics Calculator

Calculates success metrics for OpenAI optimization efforts:
- Cache hit rate
- Token reduction percentage
- Cost savings vs baseline
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Baseline metrics (before optimization)
BASELINE_AVG_INPUT_TOKENS = 25_000  # Average before optimization
BASELINE_AVG_COST_PER_REQUEST = 0.03925  # $0.03925 per request (GPT-4o only)
BASELINE_MONTHLY_COST = 64.43  # $64.43/month (900 requests, GPT-4o only)


def calculate_success_metrics(
    current_stats: Dict[str, Any],
    cache_stats: Optional[Dict[str, Any]] = None,
    total_requests: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate success metrics from current usage statistics.
    
    Args:
        current_stats: Current usage statistics from OpenAI client
        cache_stats: Cache statistics from entity context cache
        total_requests: Total number of requests (for calculating averages)
    
    Returns:
        Dictionary with success metrics
    """
    metrics = {
        'cache_performance': {},
        'token_reduction': {},
        'cost_savings': {},
        'optimization_status': 'unknown'
    }
    
    # Cache Performance Metrics
    if cache_stats:
        total_entries = cache_stats.get('total_entries', 0)
        valid_entries = cache_stats.get('valid_entries', 0)
        
        # Estimate cache hit rate (simplified - assumes 1 request per cache entry)
        # In production, you'd track actual hits vs misses
        if total_requests and total_requests > 0:
            # Rough estimate: valid entries represent potential cache hits
            estimated_hit_rate = min((valid_entries / total_requests) * 100, 100) if total_requests > 0 else 0
        else:
            estimated_hit_rate = 0
        
        metrics['cache_performance'] = {
            'total_cache_entries': total_entries,
            'valid_cache_entries': valid_entries,
            'estimated_hit_rate_percent': round(estimated_hit_rate, 2),
            'cache_ttl_seconds': cache_stats.get('ttl_seconds', 300)
        }
    else:
        metrics['cache_performance'] = {
            'status': 'not_available',
            'message': 'Cache statistics not available'
        }
    
    # Token Reduction Metrics
    current_input_tokens = current_stats.get('input_tokens', 0)
    current_output_tokens = current_stats.get('output_tokens', 0)
    current_total_tokens = current_stats.get('total_tokens', 0)
    
    if total_requests and total_requests > 0:
        avg_input_tokens = current_input_tokens / total_requests
        avg_output_tokens = current_output_tokens / total_requests
        avg_total_tokens = current_total_tokens / total_requests
    else:
        avg_input_tokens = current_input_tokens
        avg_output_tokens = current_output_tokens
        avg_total_tokens = current_total_tokens
    
    token_reduction_percent = 0
    if BASELINE_AVG_INPUT_TOKENS > 0:
        token_reduction_percent = ((BASELINE_AVG_INPUT_TOKENS - avg_input_tokens) / BASELINE_AVG_INPUT_TOKENS) * 100
    
    metrics['token_reduction'] = {
        'baseline_avg_input_tokens': BASELINE_AVG_INPUT_TOKENS,
        'current_avg_input_tokens': round(avg_input_tokens, 2),
        'reduction_percent': round(max(token_reduction_percent, 0), 2),
        'tokens_saved_per_request': round(max(BASELINE_AVG_INPUT_TOKENS - avg_input_tokens, 0), 2),
        'current_avg_output_tokens': round(avg_output_tokens, 2),
        'current_avg_total_tokens': round(avg_total_tokens, 2)
    }
    
    # Cost Savings Metrics
    current_total_cost = current_stats.get('total_cost_usd', 0.0)
    
    if total_requests and total_requests > 0:
        avg_cost_per_request = current_total_cost / total_requests
        estimated_monthly_cost = avg_cost_per_request * 900  # Assuming 900 requests/month
    else:
        avg_cost_per_request = current_total_cost
        estimated_monthly_cost = current_total_cost * (900 / max(total_requests, 1)) if total_requests else 0
    
    cost_savings_percent = 0
    if BASELINE_AVG_COST_PER_REQUEST > 0:
        cost_savings_percent = ((BASELINE_AVG_COST_PER_REQUEST - avg_cost_per_request) / BASELINE_AVG_COST_PER_REQUEST) * 100
    
    monthly_savings = BASELINE_MONTHLY_COST - estimated_monthly_cost
    
    metrics['cost_savings'] = {
        'baseline_cost_per_request': BASELINE_AVG_COST_PER_REQUEST,
        'current_cost_per_request': round(avg_cost_per_request, 4),
        'savings_per_request': round(max(BASELINE_AVG_COST_PER_REQUEST - avg_cost_per_request, 0), 4),
        'savings_percent': round(max(cost_savings_percent, 0), 2),
        'baseline_monthly_cost': BASELINE_MONTHLY_COST,
        'estimated_monthly_cost': round(estimated_monthly_cost, 2),
        'estimated_monthly_savings': round(max(monthly_savings, 0), 2)
    }
    
    # Overall Optimization Status
    if token_reduction_percent >= 40 and cost_savings_percent >= 50:
        metrics['optimization_status'] = 'excellent'
    elif token_reduction_percent >= 30 and cost_savings_percent >= 40:
        metrics['optimization_status'] = 'good'
    elif token_reduction_percent >= 20 and cost_savings_percent >= 30:
        metrics['optimization_status'] = 'moderate'
    elif token_reduction_percent > 0 or cost_savings_percent > 0:
        metrics['optimization_status'] = 'minimal'
    else:
        metrics['optimization_status'] = 'none'
    
    return metrics

