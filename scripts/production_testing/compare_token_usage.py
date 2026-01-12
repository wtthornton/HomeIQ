#!/usr/bin/env python3
"""
Token Usage Comparison Script

Compares token usage between baseline and current metrics.
Calculates token reduction percentage for Phase 3 features.

Usage:
    python scripts/production_testing/compare_token_usage.py \
        --baseline baseline_metrics.json \
        --current current_metrics.json \
        --output comparison_report.json
"""

import argparse
import json
from pathlib import Path
from typing import Any


def compare_token_usage(
    baseline_file: Path,
    current_file: Path,
    output_file: Path
) -> dict[str, Any]:
    """
    Compare token usage between baseline and current metrics.
    
    Args:
        baseline_file: Path to baseline metrics JSON file
        current_file: Path to current metrics JSON file
        output_file: Path to output comparison report JSON file
        
    Returns:
        Dictionary with comparison results
    """
    # Load metrics
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    with open(current_file) as f:
        current = json.load(f)
    
    # Extract token usage
    baseline_avg = baseline["token_usage"]["average_tokens"]
    current_avg = current["token_usage"]["average_tokens"]
    
    # Calculate reduction
    token_reduction = baseline_avg - current_avg
    token_reduction_percent = (token_reduction / baseline_avg) * 100 if baseline_avg > 0 else 0
    
    # Compare breakdown
    baseline_system = sum(baseline["token_usage"].get("system_tokens", []))
    current_system = sum(current["token_usage"].get("system_tokens", []))
    baseline_context = sum(baseline["token_usage"].get("context_tokens", []))
    current_context = sum(current["token_usage"].get("context_tokens", []))
    baseline_history = sum(baseline["token_usage"].get("history_tokens", []))
    current_history = sum(current["token_usage"].get("history_tokens", []))
    
    baseline_total_prompts = baseline["total_prompts"]
    current_total_prompts = current["total_prompts"]
    
    if baseline_total_prompts > 0:
        baseline_system_avg = baseline_system / baseline_total_prompts
        baseline_context_avg = baseline_context / baseline_total_prompts
        baseline_history_avg = baseline_history / baseline_total_prompts
    else:
        baseline_system_avg = 0
        baseline_context_avg = 0
        baseline_history_avg = 0
    
    if current_total_prompts > 0:
        current_system_avg = current_system / current_total_prompts
        current_context_avg = current_context / current_total_prompts
        current_history_avg = current_history / current_total_prompts
    else:
        current_system_avg = 0
        current_context_avg = 0
        current_history_avg = 0
    
    context_reduction = baseline_context_avg - current_context_avg
    context_reduction_percent = (context_reduction / baseline_context_avg) * 100 if baseline_context_avg > 0 else 0
    
    # Create comparison report
    comparison = {
        "timestamp": baseline.get("timestamp"),
        "baseline": {
            "average_tokens": baseline_avg,
            "system_tokens_avg": baseline_system_avg,
            "context_tokens_avg": baseline_context_avg,
            "history_tokens_avg": baseline_history_avg,
            "total_prompts": baseline_total_prompts
        },
        "current": {
            "average_tokens": current_avg,
            "system_tokens_avg": current_system_avg,
            "context_tokens_avg": current_context_avg,
            "history_tokens_avg": current_history_avg,
            "total_prompts": current_total_prompts
        },
        "comparison": {
            "token_reduction": token_reduction,
            "token_reduction_percent": token_reduction_percent,
            "context_reduction": context_reduction,
            "context_reduction_percent": context_reduction_percent,
            "target_reduction_percent": 30,  # 30-50% target
            "meets_target": token_reduction_percent >= 30
        },
        "status": "success" if token_reduction_percent >= 30 else "below_target"
    }
    
    # Save comparison
    with open(output_file, "w") as f:
        json.dump(comparison, f, indent=2)
    
    return comparison


def main():
    parser = argparse.ArgumentParser(description="Compare token usage between baseline and current metrics")
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline metrics JSON file"
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current metrics JSON file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output comparison report JSON file"
    )
    
    args = parser.parse_args()
    
    comparison = compare_token_usage(
        baseline_file=args.baseline,
        current_file=args.current,
        output_file=args.output
    )
    
    print(f"✅ Token usage comparison complete:")
    print(f"   Baseline average: {comparison['baseline']['average_tokens']:.0f} tokens")
    print(f"   Current average: {comparison['current']['average_tokens']:.0f} tokens")
    print(f"   Token reduction: {comparison['comparison']['token_reduction']:.0f} tokens ({comparison['comparison']['token_reduction_percent']:.1f}%)")
    print(f"   Context reduction: {comparison['comparison']['context_reduction']:.0f} tokens ({comparison['comparison']['context_reduction_percent']:.1f}%)")
    print(f"   Meets target (30%): {'✅ YES' if comparison['comparison']['meets_target'] else '❌ NO'}")
    print(f"   Comparison report saved to: {args.output}")


if __name__ == "__main__":
    main()
