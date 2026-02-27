"""Shared circuit breakers for proactive-agent-service cross-group calls.

Module-level breakers ensure all client instances share a single circuit
per target service group.
"""

from __future__ import annotations

from homeiq_resilience import CircuitBreaker

# data-api, sports-data, carbon-intensity all live in core-platform (Group 1)
core_platform_breaker = CircuitBreaker(name="core-platform")

# weather-api lives in data-collectors (Group 2)
data_collectors_breaker = CircuitBreaker(name="data-collectors")

# OpenAI / LLM external API -- when the API is down, callers should
# fall back to rule-based suggestion generation instead of crashing.
openai_breaker = CircuitBreaker(
    name="openai-llm",
    failure_threshold=3,
    recovery_timeout=120.0,  # longer recovery for external API
)
