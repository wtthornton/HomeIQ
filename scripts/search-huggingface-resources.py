#!/usr/bin/env python3
"""
HuggingFace Resource Search for Home Assistant Pattern Detection

This script searches HuggingFace for relevant models and datasets that could
be used in the AI Automation Pattern Detection system.

Usage:
    pip install huggingface_hub
    python scripts/search-huggingface-resources.py

Output:
    - JSON files in docs/kb/huggingface-research/
    - Summary report with recommendations
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from huggingface_hub import HfApi
except ImportError:
    print("ERROR: huggingface_hub not installed")
    print("Install with: pip install huggingface_hub")
    sys.exit(1)

# Initialize API
api = HfApi()

def export(query: str, kind: str = "model", limit: int = 2000) -> list[dict[str, Any]]:
    """
    Search HuggingFace for models or datasets

    Args:
        query: Search query (supports logical operators: OR, AND)
        kind: "model" or "dataset"
        limit: Maximum results to return

    Returns:
        List of results with metadata
    """
    print(f"Searching {kind}s: {query[:80]}...")

    try:
        if kind == "model":
            it = api.list_models(search=query, sort="downloads", direction=-1)
        else:
            it = api.list_datasets(search=query, sort="downloads", direction=-1)

        out = []
        for item in it:
            try:
                # Safely extract attributes with None checks
                card_data = None
                if hasattr(item, "cardData") and item.cardData:
                    card_data = item.cardData.get("summary") or item.cardData.get("description")

                out.append({
                    "id": getattr(item, "id", "unknown"),
                    "type": kind,
                    "pipeline_tag": getattr(item, "pipeline_tag", None),
                    "tags": list(getattr(item, "tags", []) or []),
                    "likes": getattr(item, "likes", 0),
                    "downloads": getattr(item, "downloads", 0),
                    "lastModified": str(getattr(item, "lastModified", "")),
                    "cardData": card_data,
                    "library_name": getattr(item, "library_name", None),
                    "model_size": getattr(item, "safetensors", {}).get("total", None) if hasattr(item, "safetensors") else None,
                })
                if len(out) >= limit:
                    break
            except Exception:
                # Skip problematic items
                continue

        print(f"  Found {len(out)} results")
        return out

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []


def save_results(results: dict[str, list[dict]], output_dir: Path):
    """Save search results to JSON files"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual category files
    for category, items in results.items():
        if items:
            filename = output_dir / f"{category}.json"
            with open(filename, "w") as f:
                json.dump(items, f, indent=2)
            print(f"Saved {len(items)} items to {filename}")

    # Save combined results
    combined_file = output_dir / "all_results.json"
    with open(combined_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved combined results to {combined_file}")


def generate_summary(results: dict[str, list[dict]], output_dir: Path):
    """Generate human-readable summary report"""

    summary_lines = [
        "# HuggingFace Resource Search Results",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n---\n",
        "## Summary by Category\n",
    ]

    total_models = 0
    total_datasets = 0

    for category, items in results.items():
        if not items:
            continue

        item_type = items[0]["type"]
        if item_type == "model":
            total_models += len(items)
        else:
            total_datasets += len(items)

        summary_lines.append(f"### {category.replace('_', ' ').title()}")
        summary_lines.append(f"**Type:** {item_type}")
        summary_lines.append(f"**Count:** {len(items)}\n")

        # Top 5 by downloads/likes
        top_items = sorted(items, key=lambda x: x.get("downloads") or x.get("likes") or 0, reverse=True)[:5]

        if top_items:
            summary_lines.append("**Top 5 Results:**\n")
            for i, item in enumerate(top_items, 1):
                downloads = item.get("downloads", "N/A")
                likes = item.get("likes", "N/A")
                summary_lines.append(f"{i}. **{item['id']}**")
                summary_lines.append(f"   - Pipeline: {item.get('pipeline_tag', 'N/A')}")
                summary_lines.append(f"   - Downloads: {downloads:,}" if isinstance(downloads, int) else f"   - Downloads: {downloads}")
                summary_lines.append(f"   - Likes: {likes}")
                summary_lines.append(f"   - Updated: {item['lastModified'][:10]}")
                if item.get("cardData"):
                    summary_lines.append(f"   - Description: {item['cardData'][:100]}...")
                summary_lines.append("")

        summary_lines.append("---\n")

    # Overall summary
    summary_lines.insert(4, f"\n**Total Models Found:** {total_models}")
    summary_lines.insert(5, f"**Total Datasets Found:** {total_datasets}\n")

    # Recommendations
    summary_lines.extend([
        "\n## Recommendations\n",
        "### High Priority for Integration\n",
        "1. **Time Series Models** - Use for temporal pattern detection",
        "2. **Smart Home Datasets** - Use for fine-tuning if available",
        "3. **Energy Models** - Use for duration/anomaly detection\n",
        "### Evaluation Criteria\n",
        "- Model accuracy benchmarks (need >75%)",
        "- Inference speed (<500ms)",
        "- Model size (<2GB for local deployment)",
        "- Active maintenance (updated in last 6 months)",
        "- Good documentation and examples\n",
        "### Next Steps\n",
        "1. Review top 5 results in each category",
        "2. Read model cards for accuracy and use cases",
        "3. Test promising models on sample HA data",
        "4. Benchmark against rule-based approach (85-90% baseline)",
        "5. Integrate only if specialized model beats rules by 10%+\n",
    ])

    summary_file = output_dir / "SEARCH_SUMMARY.md"
    with open(summary_file, "w") as f:
        f.write("\n".join(summary_lines))

    print(f"\nSummary report saved to {summary_file}")


def main():
    """Execute comprehensive HuggingFace search"""

    print("\n" + "="*80)
    print("HuggingFace Resource Search for Home Assistant Pattern Detection")
    print("="*80 + "\n")

    # Output directory
    output_dir = Path("docs/kb/huggingface-research")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define Phase 1 Priority Searches
    # Focused on MVP needs: embeddings, classification, validation datasets
    searches = {
        # PHASE 1 CRITICAL: EMBEDDING MODELS (for pattern similarity)
        "embedding_models_sentence_transformers": {
            "query": "sentence-transformers OR sentence transformers",
            "kind": "model",
            "limit": 30,
        },
        "embedding_models_general": {
            "query": "pipeline_tag:feature-extraction",
            "kind": "model",
            "limit": 30,
        },

        # PHASE 1 CRITICAL: CLASSIFICATION MODELS (for categorization)
        "zero_shot_classification": {
            "query": "pipeline_tag:zero-shot-classification",
            "kind": "model",
            "limit": 20,
        },
        "text_classification": {
            "query": "pipeline_tag:text-classification",
            "kind": "model",
            "limit": 20,
        },

        # PHASE 1 HIGH: SMART HOME DATASETS (for validation)
        "smart_home_datasets": {
            "query": "smart home OR home automation",
            "kind": "dataset",
            "limit": 50,
        },
        "user_routine_datasets": {
            "query": "user routine OR user behavior OR EdgeWisePersona",
            "kind": "dataset",
            "limit": 30,
        },
        "home_assistant_datasets": {
            "query": "home assistant OR homeassistant OR hermes",
            "kind": "dataset",
            "limit": 30,
        },

        # PHASE 1 HIGH: ENERGY DATASETS (for duration/anomaly testing)
        "energy_datasets": {
            "query": "energy consumption OR smart meter",
            "kind": "dataset",
            "limit": 40,
        },
        "appliance_datasets": {
            "query": "appliance usage OR NILM",
            "kind": "dataset",
            "limit": 20,
        },

        # PHASE 1 MEDIUM: TIME SERIES MODELS (for validation)
        "time_series_forecasting": {
            "query": "pipeline_tag:time-series-forecasting",
            "kind": "model",
            "limit": 30,
        },

        # PHASE 1 MEDIUM: IOT DATASETS (for testing)
        "iot_sensor_datasets": {
            "query": "iot sensor OR sensor data",
            "kind": "dataset",
            "limit": 30,
        },

        # PHASE 1 LOW: ANOMALY DETECTION (nice to have)
        "anomaly_detection_models": {
            "query": "anomaly detection",
            "kind": "model",
            "limit": 15,
        },
        "anomaly_detection_datasets": {
            "query": "anomaly detection OR SmartHome-Bench",
            "kind": "dataset",
            "limit": 15,
        },
    }

    # Execute all searches
    results = {}
    for category, params in searches.items():
        results[category] = export(**params)

    # Save results
    print("\n" + "="*80)
    print("Saving Results")
    print("="*80 + "\n")
    save_results(results, output_dir)

    # Generate summary
    print("\n" + "="*80)
    print("Generating Summary")
    print("="*80 + "\n")
    generate_summary(results, output_dir)

    # Print quick stats
    print("\n" + "="*80)
    print("Quick Statistics")
    print("="*80 + "\n")

    total_models = sum(len(items) for cat, items in results.items() if items and items[0]["type"] == "model")
    total_datasets = sum(len(items) for cat, items in results.items() if items and items[0]["type"] == "dataset")

    print(f"Total Models Found: {total_models}")
    print(f"Total Datasets Found: {total_datasets}")
    print(f"\nResults saved to: {output_dir.absolute()}")
    print("\nReview SEARCH_SUMMARY.md for top findings and recommendations.")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

