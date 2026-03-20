#!/usr/bin/env python3
"""LLM Provider Benchmark — GPT-5.2 vs Claude with Prompt Caching.

Epic 97, Story 97.5: Cost & Quality Benchmarking

Usage:
    python scripts/benchmark_llm_providers.py

Requires:
    OPENAI_API_KEY and ANTHROPIC_API_KEY environment variables.

Runs 20 representative automation prompts through both providers,
comparing token usage, cost, cache hit rate, response quality, and YAML validity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "domains" / "automation-core" / "ha-ai-agent-service"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 20 representative automation prompts
# ---------------------------------------------------------------------------

BENCHMARK_PROMPTS = [
    # Simple (1-5)
    "Turn on the office lights at sunset",
    "Set the thermostat to 72 degrees when I get home",
    "Turn off all lights at midnight",
    "Send me a notification when the front door opens",
    "Turn on the porch light at 6pm every day",
    # Medium (6-10)
    "When motion is detected in the hallway after dark, turn on the hallway lights at 30%",
    "If the temperature drops below 65, turn on the heating and send me a notification",
    "Turn off the TV and dim the living room lights to 10% at 11pm on weekdays",
    "When I leave home, turn off all lights and set thermostat to eco mode",
    "Flash the kitchen lights blue when my favorite team scores a goal",
    # Complex (11-15)
    "If motion in the office and it's after sunset, turn on office lights unless they're already on, then set temperature to 72",
    "Create a bedtime routine: at 10pm dim all lights to 20%, lock the front door, set thermostat to 68, and arm the alarm",
    "When the washing machine power drops below 5W for 3 minutes, send a notification that laundry is done",
    "If no motion detected in any room for 30 minutes and it's between 10pm and 6am, turn off all lights and set heating to night mode",
    "When it starts raining and any window is open, send an urgent notification listing which windows are open",
    # Multi-entity / sports (16-20)
    "Set up game day mode: 30 minutes before kickoff, turn on the TV, set living room lights to team colors, and turn on the sound system",
    "Create a morning routine sequence: turn on bedroom lights gradually over 10 minutes, then start the coffee maker, then turn on the bathroom heater",
    "If electricity price is above 30p/kWh and the battery is above 80%, switch to battery power and reduce non-essential loads",
    "When a guest arrives (doorbell rings), turn on porch and hallway lights, unlock the front door for 5 minutes, and send me a photo notification",
    "Create a cinema mode: close the blinds, turn off all living room lights except the TV backlight at 5% warm white, set volume to 40%, and set do-not-disturb on all phones",
]

SYSTEM_PROMPT = (
    "You are a Home Assistant YAML automation specialist. "
    "Generate valid HA automation YAML for the user's request. "
    "Return only the YAML, no explanation."
)


@dataclass
class BenchmarkResult:
    prompt: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    latency_ms: float = 0
    yaml_valid: bool = False
    response_text: str = ""
    error: str | None = None


async def benchmark_anthropic(prompts: list[str]) -> list[BenchmarkResult]:
    """Run prompts through Anthropic Claude."""
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping Anthropic benchmark")
        return []

    client = anthropic.AsyncAnthropic(api_key=api_key)
    model = "claude-sonnet-4-6"
    results: list[BenchmarkResult] = []

    for i, prompt in enumerate(prompts):
        result = BenchmarkResult(prompt=prompt, provider="anthropic", model=model)
        try:
            start = time.monotonic()
            response = await client.messages.create(
                model=model,
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            result.latency_ms = (time.monotonic() - start) * 1000

            result.response_text = response.content[0].text if response.content else ""
            result.input_tokens = getattr(response.usage, "input_tokens", 0)
            result.output_tokens = getattr(response.usage, "output_tokens", 0)
            result.cached_tokens = getattr(response.usage, "cache_read_input_tokens", 0) or 0
            result.cache_creation_tokens = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
            result.yaml_valid = _is_valid_yaml(result.response_text)

            logger.info(
                "[%d/20] Anthropic: %d in, %d out, %d cached (%.0fms) yaml=%s",
                i + 1, result.input_tokens, result.output_tokens,
                result.cached_tokens, result.latency_ms, result.yaml_valid,
            )
        except Exception as e:
            result.error = str(e)
            logger.error("[%d/20] Anthropic error: %s", i + 1, e)

        results.append(result)

    return results


async def benchmark_openai(prompts: list[str]) -> list[BenchmarkResult]:
    """Run prompts through OpenAI GPT-5.2."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package not installed")
        return []

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — skipping OpenAI benchmark")
        return []

    client = AsyncOpenAI(api_key=api_key)
    model = "gpt-5.2-codex"
    results: list[BenchmarkResult] = []

    for i, prompt in enumerate(prompts):
        result = BenchmarkResult(prompt=prompt, provider="openai", model=model)
        try:
            start = time.monotonic()
            response = await client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=[{"type": "message", "role": "user", "content": prompt}],
                max_output_tokens=2048,
                store=False,
            )
            result.latency_ms = (time.monotonic() - start) * 1000

            result.response_text = response.output_text or ""
            if response.usage:
                result.input_tokens = getattr(response.usage, "input_tokens", 0)
                result.output_tokens = getattr(response.usage, "output_tokens", 0)
            result.yaml_valid = _is_valid_yaml(result.response_text)

            logger.info(
                "[%d/20] OpenAI: %d in, %d out (%.0fms) yaml=%s",
                i + 1, result.input_tokens, result.output_tokens,
                result.latency_ms, result.yaml_valid,
            )
        except Exception as e:
            result.error = str(e)
            logger.error("[%d/20] OpenAI error: %s", i + 1, e)

        results.append(result)

    return results


def _is_valid_yaml(text: str) -> bool:
    """Check if response contains valid YAML."""
    import yaml as pyyaml
    try:
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:])
            if clean.rstrip().endswith("```"):
                clean = clean.rstrip()[:-3]

        result = pyyaml.safe_load(clean)
        if not isinstance(result, dict):
            return False
        # Must have at minimum alias or trigger
        return "alias" in result or "trigger" in result
    except Exception:
        return False


def _generate_report(
    anthropic_results: list[BenchmarkResult],
    openai_results: list[BenchmarkResult],
) -> str:
    """Generate markdown benchmark report."""
    lines = ["# LLM Provider Benchmark Report", "", f"Date: {time.strftime('%Y-%m-%d %H:%M')}", ""]

    for label, results in [("Anthropic Claude", anthropic_results), ("OpenAI GPT-5.2", openai_results)]:
        if not results:
            lines.append(f"## {label}\n\nNo results (API key not configured).\n")
            continue

        successful = [r for r in results if not r.error]
        total_in = sum(r.input_tokens for r in successful)
        total_out = sum(r.output_tokens for r in successful)
        total_cached = sum(r.cached_tokens for r in successful)
        total_cache_creation = sum(r.cache_creation_tokens for r in successful)
        avg_latency = sum(r.latency_ms for r in successful) / len(successful) if successful else 0
        yaml_pass = sum(1 for r in successful if r.yaml_valid)

        lines.extend([
            f"## {label}",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Prompts tested | {len(results)} |",
            f"| Successful | {len(successful)} |",
            f"| Errors | {len(results) - len(successful)} |",
            f"| Avg input tokens | {total_in // max(len(successful), 1)} |",
            f"| Avg output tokens | {total_out // max(len(successful), 1)} |",
            f"| Total cached tokens | {total_cached} |",
            f"| Total cache creation tokens | {total_cache_creation} |",
            f"| Avg latency (ms) | {avg_latency:.0f} |",
            f"| YAML valid | {yaml_pass}/{len(successful)} ({yaml_pass / max(len(successful), 1) * 100:.0f}%) |",
            "",
        ])

    lines.extend([
        "## Comparison",
        "",
        "| Provider | Avg Input | Avg Output | Cost/Request | Cache Savings |",
        "|----------|-----------|------------|-------------|---------------|",
    ])

    for label, results in [("Claude (cached)", anthropic_results), ("GPT-5.2", openai_results)]:
        successful = [r for r in results if not r.error]
        if successful:
            avg_in = sum(r.input_tokens for r in successful) // len(successful)
            avg_out = sum(r.output_tokens for r in successful) // len(successful)
            total_cached = sum(r.cached_tokens for r in successful)
            total_in = sum(r.input_tokens for r in successful)
            cache_pct = f"{total_cached / max(total_in + total_cached, 1) * 100:.0f}%" if total_cached else "N/A"
            lines.append(f"| {label} | {avg_in} | {avg_out} | — | {cache_pct} |")

    lines.append("")
    return "\n".join(lines)


async def main():
    logger.info("Starting LLM provider benchmark with %d prompts...", len(BENCHMARK_PROMPTS))

    # Run both providers
    anthropic_results = await benchmark_anthropic(BENCHMARK_PROMPTS)
    openai_results = await benchmark_openai(BENCHMARK_PROMPTS)

    # Generate report
    report = _generate_report(anthropic_results, openai_results)

    # Write report
    docs_dir = Path(__file__).resolve().parent.parent / "domains" / "automation-core" / "ha-ai-agent-service" / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "LLM_BENCHMARK.md"
    report_path.write_text(report, encoding="utf-8")

    print(report)
    logger.info("Report written to %s", report_path)


if __name__ == "__main__":
    asyncio.run(main())
