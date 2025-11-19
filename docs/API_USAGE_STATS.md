# API Usage Statistics Endpoint

**Endpoint:** `GET /api/suggestions/usage/stats`  
**Phase:** 5 (Simplified Monitoring)  
**Last Updated:** November 19, 2025

---

## Overview

The usage stats endpoint provides comprehensive monitoring of OpenAI API usage, including:
- Token counts and costs
- Endpoint-level breakdown
- Cache performance metrics
- Success metrics (token reduction, cost savings)

---

## Response Format

```json
{
  "total_tokens": 125000,
  "input_tokens": 100000,
  "output_tokens": 25000,
  "estimated_cost_usd": 0.1250,
  "total_cost_usd": 0.1250,
  "model": "gpt-5.1",
  "endpoint_breakdown": {
    "ask_ai_suggestions": {
      "calls": 10,
      "input_tokens": 50000,
      "output_tokens": 12000,
      "total_tokens": 62000,
      "cost_usd": 0.0625,
      "avg_cost_per_call": 0.00625
    },
    "yaml_generation": {
      "calls": 8,
      "input_tokens": 40000,
      "output_tokens": 10000,
      "total_tokens": 50000,
      "cost_usd": 0.0500,
      "avg_cost_per_call": 0.00625
    },
    "pattern_suggestion_generation": {
      "calls": 5,
      "input_tokens": 10000,
      "output_tokens": 3000,
      "total_tokens": 13000,
      "cost_usd": 0.0125,
      "avg_cost_per_call": 0.0025
    }
  },
  "model_pricing": {
    "gpt-5.1": {
      "input_cost_per_1m": 1.25,
      "output_cost_per_1m": 10.0,
      "cached_input_cost_per_1m": 0.125
    },
    "gpt-5-mini": {
      "input_cost_per_1m": 0.25,
      "output_cost_per_1m": 2.0,
      "cached_input_cost_per_1m": 0.025
    },
    "gpt-5-nano": {
      "input_cost_per_1m": 0.05,
      "output_cost_per_1m": 0.4,
      "cached_input_cost_per_1m": 0.005
    }
  },
  "last_usage": {
    "prompt_tokens": 5000,
    "completion_tokens": 1200,
    "total_tokens": 6200,
    "cost_usd": 0.00625,
    "model": "gpt-5.1",
    "endpoint": "ask_ai_suggestions"
  },
  "cache_stats": {
    "total_entries": 15,
    "valid_entries": 12,
    "expired_entries": 3,
    "ttl_seconds": 300
  },
  "success_metrics": {
    "cache_performance": {
      "total_cache_entries": 15,
      "valid_cache_entries": 12,
      "estimated_hit_rate_percent": 52.17,
      "cache_ttl_seconds": 300
    },
    "token_reduction": {
      "baseline_avg_input_tokens": 25000,
      "current_avg_input_tokens": 12000,
      "reduction_percent": 52.0,
      "tokens_saved_per_request": 13000,
      "current_avg_output_tokens": 1086.96,
      "current_avg_total_tokens": 13086.96
    },
    "cost_savings": {
      "baseline_cost_per_request": 0.03925,
      "current_cost_per_request": 0.01500,
      "savings_per_request": 0.02425,
      "savings_percent": 61.78,
      "baseline_monthly_cost": 64.43,
      "estimated_monthly_cost": 24.62,
      "estimated_monthly_savings": 39.81
    },
    "optimization_status": "excellent"
  },
  "timestamp": "2025-11-19T17:30:00.000000Z"
}
```

---

## Field Descriptions

### Top-Level Stats
- `total_tokens`: Total tokens used across all requests
- `input_tokens`: Total input tokens
- `output_tokens`: Total output tokens
- `estimated_cost_usd`: Estimated cost based on current token counts
- `total_cost_usd`: Actual tracked cost (may differ slightly due to rounding)
- `model`: Primary model being used

### Endpoint Breakdown (Phase 5)
Tracks usage per endpoint:
- `ask_ai_suggestions`: Ask AI query → suggestion generation
- `yaml_generation`: YAML generation from suggestions
- `pattern_suggestion_generation`: Pattern-based suggestion generation

Each endpoint includes:
- `calls`: Number of API calls
- `input_tokens`: Total input tokens
- `output_tokens`: Total output tokens
- `total_tokens`: Total tokens
- `cost_usd`: Total cost for this endpoint
- `avg_cost_per_call`: Average cost per call

### Cache Stats (Phase 4)
- `total_entries`: Total cached entries
- `valid_entries`: Entries still within TTL
- `expired_entries`: Entries past TTL
- `ttl_seconds`: Time-to-live for cache entries

### Success Metrics (Phase 5)
- **Cache Performance:**
  - `estimated_hit_rate_percent`: Estimated cache hit rate
  - Based on valid cache entries vs total requests

- **Token Reduction:**
  - `baseline_avg_input_tokens`: Baseline (25,000 tokens)
  - `current_avg_input_tokens`: Current average
  - `reduction_percent`: Percentage reduction
  - `tokens_saved_per_request`: Tokens saved per request

- **Cost Savings:**
  - `baseline_cost_per_request`: Baseline cost ($0.03925)
  - `current_cost_per_request`: Current average cost
  - `savings_per_request`: Savings per request
  - `savings_percent`: Percentage savings
  - `baseline_monthly_cost`: Baseline monthly cost ($64.43)
  - `estimated_monthly_cost`: Estimated current monthly cost
  - `estimated_monthly_savings`: Estimated monthly savings

- **Optimization Status:**
  - `excellent`: ≥40% token reduction AND ≥50% cost savings
  - `good`: ≥30% token reduction AND ≥40% cost savings
  - `moderate`: ≥20% token reduction AND ≥30% cost savings
  - `minimal`: Any reduction
  - `none`: No reduction

---

## Usage Examples

### Get Current Stats
```bash
curl -H "X-HomeIQ-API-Key: your-key" \
  http://localhost:8024/api/suggestions/usage/stats
```

### Monitor Endpoint Costs
```python
import requests

response = requests.get(
    "http://localhost:8024/api/suggestions/usage/stats",
    headers={"X-HomeIQ-API-Key": "your-key"}
)
stats = response.json()

# Check endpoint costs
for endpoint, data in stats['endpoint_breakdown'].items():
    print(f"{endpoint}: ${data['cost_usd']:.4f} ({data['calls']} calls)")
```

### Check Success Metrics
```python
metrics = stats['success_metrics']
print(f"Token Reduction: {metrics['token_reduction']['reduction_percent']:.1f}%")
print(f"Cost Savings: {metrics['cost_savings']['savings_percent']:.1f}%")
print(f"Status: {metrics['optimization_status']}")
```

---

## Notes

- Stats are in-memory and reset when service restarts
- Endpoint tracking requires passing `endpoint` parameter to API calls
- Success metrics use baseline values from pre-optimization analysis
- Cache hit rate is estimated based on cache entries vs requests

---

**Last Updated:** November 19, 2025

