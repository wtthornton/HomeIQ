#!/usr/bin/env python3
"""
Baseline Metrics Collection Script

Collects baseline metrics for Phase 1, 2, 3 production testing.
Measures token usage, accuracy, and performance before Phase 3 features are enabled.

Usage:
    python scripts/production_testing/baseline_metrics.py \
        --prompts-file test_data/user_prompts.json \
        --output-file baseline_metrics.json
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp


async def collect_baseline_metrics(
    prompts_file: Path,
    output_file: Path,
    api_url: str = "http://localhost:8025"
) -> dict[str, Any]:
    """
    Collect baseline metrics by running test prompts.
    
    Args:
        prompts_file: Path to JSON file with test prompts
        output_file: Path to output JSON file for metrics
        api_url: Base URL for HA AI Agent Service API
        
    Returns:
        Dictionary with baseline metrics
    """
    # Load test prompts
    with open(prompts_file) as f:
        test_prompts = json.load(f)
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "phase": "baseline",
        "total_prompts": len(test_prompts),
        "token_usage": {
            "system_tokens": [],
            "context_tokens": [],
            "history_tokens": [],
            "total_tokens": [],
            "average_tokens": 0
        },
        "accuracy": {
            "entity_resolution_correct": 0,
            "entity_resolution_total": 0,
            "automation_creation_success": 0,
            "automation_creation_total": 0,
            "user_approval_rate": 0
        },
        "performance": {
            "response_times": [],
            "average_response_time": 0,
            "p50_response_time": 0,
            "p95_response_time": 0,
            "p99_response_time": 0
        },
        "errors": []
    }
    
    async with aiohttp.ClientSession() as session:
        for prompt_data in test_prompts:
            prompt = prompt_data["prompt"]
            expected_entities = prompt_data.get("expected_entities", [])
            
            try:
                start_time = time.time()
                
                # Make API call
                async with session.post(
                    f"{api_url}/api/chat",
                    json={"message": prompt},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_data = await response.json()
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    metrics["performance"]["response_times"].append(response_time)
                    
                    # Extract token usage from metadata
                    if "metadata" in response_data:
                        metadata = response_data["metadata"]
                        if "token_breakdown" in metadata:
                            token_breakdown = metadata["token_breakdown"]
                            metrics["token_usage"]["system_tokens"].append(
                                token_breakdown.get("system_tokens", 0)
                            )
                            metrics["token_usage"]["context_tokens"].append(
                                token_breakdown.get("context_tokens", 0)
                            )
                            metrics["token_usage"]["history_tokens"].append(
                                token_breakdown.get("history_tokens", 0)
                            )
                        
                        if "tokens_used" in metadata:
                            metrics["token_usage"]["total_tokens"].append(
                                metadata["tokens_used"]
                            )
                    
                    # Track accuracy (simplified - would need more complex analysis)
                    # This is a placeholder for actual accuracy measurement
                    
            except Exception as e:
                metrics["errors"].append({
                    "prompt": prompt,
                    "error": str(e)
                })
    
    # Calculate averages
    if metrics["token_usage"]["total_tokens"]:
        metrics["token_usage"]["average_tokens"] = sum(
            metrics["token_usage"]["total_tokens"]
        ) / len(metrics["token_usage"]["total_tokens"])
    
    if metrics["performance"]["response_times"]:
        response_times = sorted(metrics["performance"]["response_times"])
        metrics["performance"]["average_response_time"] = sum(response_times) / len(response_times)
        metrics["performance"]["p50_response_time"] = response_times[len(response_times) // 2]
        metrics["performance"]["p95_response_time"] = response_times[int(len(response_times) * 0.95)]
        metrics["performance"]["p99_response_time"] = response_times[int(len(response_times) * 0.99)]
    
    # Save metrics
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=2)
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Collect baseline metrics for production testing")
    parser.add_argument(
        "--prompts-file",
        type=Path,
        required=True,
        help="Path to JSON file with test prompts"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        required=True,
        help="Path to output JSON file for metrics"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8025",
        help="Base URL for HA AI Agent Service API"
    )
    
    args = parser.parse_args()
    
    # Run async function
    metrics = asyncio.run(collect_baseline_metrics(
        prompts_file=args.prompts_file,
        output_file=args.output_file,
        api_url=args.api_url
    ))
    
    print(f"✅ Baseline metrics collected:")
    print(f"   Total prompts: {metrics['total_prompts']}")
    print(f"   Average tokens: {metrics['token_usage']['average_tokens']:.0f}")
    print(f"   Average response time: {metrics['performance']['average_response_time']:.0f}ms")
    print(f"   Metrics saved to: {args.output_file}")


if __name__ == "__main__":
    main()
