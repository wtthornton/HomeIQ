#!/usr/bin/env python3
"""Assess sentence-transformers upgrade from 3.3.1 to 5.x.

Story 38.2: sentence-transformers Upgrade Assessment

This script evaluates the feasibility of upgrading sentence-transformers by:
1. Checking API compatibility (breaking changes)
2. Running embedding consistency tests
3. Documenting findings in a decision document

Usage:
    # Run full assessment
    python scripts/assess_sentence_transformers_upgrade.py

    # Check API compatibility only (no model download)
    python scripts/assess_sentence_transformers_upgrade.py --api-only

    # Run with specific version
    python scripts/assess_sentence_transformers_upgrade.py --target-version 5.2.2

Requirements:
    - sentence-transformers (any version)
    - numpy
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "ml" / "fixtures"
REFERENCE_DIR = FIXTURES_DIR / "reference_embeddings"
OUTPUT_DIR = PROJECT_ROOT / "implementation" / "analysis"

CURRENT_VERSION = "3.3.1"
TARGET_VERSION = "5.2.2"

HOMEIQ_MODELS = {
    "all-MiniLM-L6-v2": {
        "dimension": 384,
        "usage": "homeiq-memory default model",
        "services": ["homeiq-memory"],
    },
    "BAAI/bge-large-en-v1.5": {
        "dimension": 1024,
        "usage": "openvino-service production model",
        "services": ["openvino-service"],
    },
}

HOMEIQ_API_PATTERNS = [
    {
        "pattern": "SentenceTransformer(model_name)",
        "used_in": ["openvino-service", "homeiq-memory"],
        "v5_compatible": True,
        "notes": "Basic initialization unchanged",
    },
    {
        "pattern": "model.encode(texts)",
        "used_in": ["openvino-service", "homeiq-memory"],
        "v5_compatible": True,
        "notes": "Core encode method unchanged",
    },
    {
        "pattern": "model.encode(texts, convert_to_numpy=True)",
        "used_in": ["homeiq-memory"],
        "v5_compatible": True,
        "notes": "Parameter still supported",
    },
    {
        "pattern": "model.get_sentence_embedding_dimension()",
        "used_in": ["homeiq-memory"],
        "v5_compatible": True,
        "notes": "Method unchanged",
    },
    {
        "pattern": "SentenceTransformer(model_name, cache_folder=path)",
        "used_in": ["openvino-service"],
        "v5_compatible": True,
        "notes": "Cache folder parameter unchanged",
    },
    {
        "pattern": "encode_multi_process()",
        "used_in": [],
        "v5_compatible": False,
        "notes": "DEPRECATED in v5 - use encode() with device list",
    },
]


@dataclass
class AssessmentResult:
    """Container for upgrade assessment results."""

    current_version: str
    target_version: str
    installed_version: str
    api_compatible: bool = True
    api_issues: list[str] = field(default_factory=list)
    embedding_compatible: bool | None = None
    embedding_results: dict = field(default_factory=dict)
    recommendation: str = ""
    decision: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def check_sentence_transformers() -> tuple[bool, str]:
    """Check if sentence-transformers is installed and get version."""
    try:
        import sentence_transformers
        return True, sentence_transformers.__version__
    except ImportError:
        return False, ""


def check_api_compatibility() -> tuple[bool, list[str]]:
    """Check API compatibility based on known patterns."""
    issues = []

    for pattern in HOMEIQ_API_PATTERNS:
        if not pattern["v5_compatible"] and pattern["used_in"]:
            issues.append(
                f"BREAKING: {pattern['pattern']} used in {pattern['used_in']} - "
                f"{pattern['notes']}"
            )

    # All HomeIQ patterns are v5 compatible
    compatible = len(issues) == 0
    return compatible, issues


def load_test_sentences() -> list[str]:
    """Load test sentences from fixtures."""
    sentences_file = FIXTURES_DIR / "test_sentences.json"
    if not sentences_file.exists():
        print(f"Warning: Test sentences not found at {sentences_file}")
        return [
            "Turn on the living room lights",
            "Set the thermostat to 72 degrees",
            "When motion is detected",
            "Every morning at 7am",
        ]

    with sentences_file.open(encoding="utf-8") as f:
        return json.load(f)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def test_embedding_consistency(
    model_name: str, sentences: list[str], reference_file: Path | None = None
) -> dict:
    """Test embedding consistency for a model.

    If reference_file is provided, compares against reference embeddings.
    Otherwise, just tests that embeddings can be generated.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return {"error": "sentence-transformers not installed"}

    result = {
        "model_name": model_name,
        "sentences_tested": len(sentences),
        "embeddings_generated": False,
        "reference_comparison": None,
    }

    try:
        print(f"  Loading model: {model_name}...")
        model = SentenceTransformer(model_name)

        print(f"  Generating embeddings for {len(sentences)} sentences...")
        embeddings = model.encode(sentences, convert_to_numpy=True, show_progress_bar=True)

        result["embeddings_generated"] = True
        result["dimension"] = embeddings.shape[1]
        result["expected_dimension"] = HOMEIQ_MODELS.get(model_name, {}).get("dimension")
        result["dimension_match"] = result["dimension"] == result["expected_dimension"]

        # Check normalization
        norms = np.linalg.norm(embeddings, axis=1)
        result["normalized"] = bool(np.all((norms > 0.99) & (norms < 1.01)))

        # Compare against reference if available
        if reference_file and reference_file.exists():
            ref_data = np.load(reference_file, allow_pickle=True)
            ref_embeddings = ref_data["embeddings"]

            if ref_embeddings.shape == embeddings.shape:
                similarities = [
                    cosine_similarity(embeddings[i], ref_embeddings[i])
                    for i in range(len(sentences))
                ]
                result["reference_comparison"] = {
                    "mean_similarity": float(np.mean(similarities)),
                    "min_similarity": float(np.min(similarities)),
                    "max_similarity": float(np.max(similarities)),
                    "threshold": 0.99,
                    "passed": float(np.min(similarities)) >= 0.99,
                }
            else:
                result["reference_comparison"] = {
                    "error": f"Shape mismatch: {embeddings.shape} vs {ref_embeddings.shape}"
                }

    except Exception as e:
        result["error"] = str(e)

    return result


def generate_decision_document(result: AssessmentResult) -> str:
    """Generate a markdown decision document."""
    doc = f"""# sentence-transformers Upgrade Assessment

**Story 38.2** | Generated: {result.timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Current Version | {result.current_version} |
| Target Version | {result.target_version} |
| Installed Version | {result.installed_version} |
| API Compatible | {"✅ Yes" if result.api_compatible else "❌ No"} |
| Embedding Compatible | {"✅ Yes" if result.embedding_compatible else "❓ Unknown" if result.embedding_compatible is None else "❌ No"} |

## Decision

**{result.decision}**

{result.recommendation}

## API Compatibility Analysis

Based on HomeIQ codebase analysis, the following API patterns are used:

| Pattern | Services | v5.x Compatible | Notes |
|---------|----------|-----------------|-------|
"""

    for pattern in HOMEIQ_API_PATTERNS:
        services = ", ".join(pattern["used_in"]) if pattern["used_in"] else "None"
        compat = "✅" if pattern["v5_compatible"] else "❌"
        doc += f"| `{pattern['pattern']}` | {services} | {compat} | {pattern['notes']} |\n"

    if result.api_issues:
        doc += "\n### API Issues Found\n\n"
        for issue in result.api_issues:
            doc += f"- {issue}\n"
    else:
        doc += "\n**No breaking API changes detected for HomeIQ usage patterns.**\n"

    doc += "\n## Embedding Compatibility Results\n\n"

    if result.embedding_results:
        for model_name, results in result.embedding_results.items():
            doc += f"### {model_name}\n\n"
            if "error" in results:
                doc += f"❌ Error: {results['error']}\n\n"
            else:
                doc += f"- Embeddings generated: {'✅' if results.get('embeddings_generated') else '❌'}\n"
                doc += f"- Dimension: {results.get('dimension')} (expected: {results.get('expected_dimension')})\n"
                doc += f"- Dimension match: {'✅' if results.get('dimension_match') else '❌'}\n"
                doc += f"- Normalized: {'✅' if results.get('normalized') else '❌'}\n"

                if results.get("reference_comparison"):
                    ref = results["reference_comparison"]
                    if "error" in ref:
                        doc += f"- Reference comparison: ❌ {ref['error']}\n"
                    else:
                        passed = "✅ PASS" if ref.get("passed") else "❌ FAIL"
                        doc += f"- Reference comparison: {passed}\n"
                        doc += f"  - Mean similarity: {ref.get('mean_similarity', 0):.6f}\n"
                        doc += f"  - Min similarity: {ref.get('min_similarity', 0):.6f}\n"
                        doc += f"  - Threshold: {ref.get('threshold', 0.99)}\n"
                doc += "\n"
    else:
        doc += "No embedding tests run (use `--full` to run embedding tests).\n\n"

    doc += """## Recommendations

### If Embedding Compatible (similarity >= 0.99)

1. **Proceed with upgrade** - Update requirements.txt:
   ```
   sentence-transformers>=5.0.0
   ```

2. **Code changes required**: None - all API patterns are compatible

3. **Re-indexing**: Not required if embeddings are compatible

### If Embedding Incompatible (similarity < 0.99)

1. **Option A: Pin version** - Keep `sentence-transformers==3.3.1`
   - Pro: No re-indexing, no code changes
   - Con: Technical debt, missing new features

2. **Option B: Re-index** - Upgrade and regenerate all stored embeddings
   - Pro: Latest features, clean slate
   - Con: Downtime, compute cost

## Next Steps

"""

    if result.embedding_compatible:
        doc += """1. ✅ Update requirements.txt in openvino-service and homeiq-memory
2. ✅ Run full test suite
3. ✅ Deploy to staging
4. ✅ Monitor embedding quality metrics
"""
    elif result.embedding_compatible is None:
        doc += """1. ⏳ Generate reference embeddings with v3.3.1
2. ⏳ Install v5.x and run embedding compatibility tests
3. ⏳ Make decision based on results
"""
    else:
        doc += """1. 🔄 Evaluate re-indexing effort
2. 🔄 Decide: pin version or re-index
3. 🔄 Create Story 38.4 if re-indexing chosen
"""

    return doc


def run_assessment(api_only: bool = False, target_version: str = TARGET_VERSION) -> AssessmentResult:
    """Run the full upgrade assessment."""
    print("=" * 60)
    print("sentence-transformers Upgrade Assessment")
    print("=" * 60)

    # Check installation
    installed, version = check_sentence_transformers()

    result = AssessmentResult(
        current_version=CURRENT_VERSION,
        target_version=target_version,
        installed_version=version if installed else "Not installed",
    )

    # Check API compatibility
    print("\n[1/3] Checking API compatibility...")
    result.api_compatible, result.api_issues = check_api_compatibility()

    if result.api_compatible:
        print("  ✅ All HomeIQ API patterns are v5.x compatible")
    else:
        print(f"  ❌ Found {len(result.api_issues)} API compatibility issues")
        for issue in result.api_issues:
            print(f"     - {issue}")

    if api_only:
        print("\n[2/3] Skipping embedding tests (--api-only)")
        print("[3/3] Skipping embedding tests (--api-only)")
        result.recommendation = "Run full assessment with embedding tests to make final decision."
        result.decision = "PENDING - Embedding compatibility not tested"
        return result

    if not installed:
        print("\n[2/3] Cannot run embedding tests - sentence-transformers not installed")
        result.recommendation = "Install sentence-transformers to run embedding tests."
        result.decision = "PENDING - sentence-transformers not installed"
        return result

    # Load test sentences
    print("\n[2/3] Loading test sentences...")
    sentences = load_test_sentences()
    print(f"  Loaded {len(sentences)} test sentences")

    # Test embedding consistency for each model
    print("\n[3/3] Testing embedding consistency...")
    result.embedding_results = {}

    for model_name in HOMEIQ_MODELS:
        print(f"\n  Testing: {model_name}")
        safe_name = model_name.replace("/", "-")
        ref_file = REFERENCE_DIR / f"{safe_name}_v{CURRENT_VERSION}.npz"

        model_result = test_embedding_consistency(model_name, sentences, ref_file)
        result.embedding_results[model_name] = model_result

    # Determine overall embedding compatibility
    all_passed = all(
        r.get("reference_comparison", {}).get("passed", False)
        for r in result.embedding_results.values()
        if "error" not in r
    )

    any_tested = any(
        r.get("reference_comparison") is not None
        for r in result.embedding_results.values()
    )

    if any_tested:
        result.embedding_compatible = all_passed
    else:
        result.embedding_compatible = None  # No reference to compare against

    # Generate recommendation
    if result.api_compatible and result.embedding_compatible:
        result.decision = "✅ UPGRADE SAFE"
        result.recommendation = (
            "Proceed with sentence-transformers upgrade to v5.x. "
            "No breaking changes detected, embeddings are compatible."
        )
    elif result.api_compatible and result.embedding_compatible is None:
        result.decision = "⏳ PENDING - Generate reference embeddings first"
        result.recommendation = (
            "API is compatible. Generate reference embeddings with v3.3.1, "
            "then re-run assessment to verify embedding compatibility."
        )
    elif result.api_compatible and not result.embedding_compatible:
        result.decision = "⚠️ REQUIRES RE-INDEXING"
        result.recommendation = (
            "API is compatible but embeddings differ. "
            "Re-indexing of stored embeddings will be required."
        )
    else:
        result.decision = "❌ DO NOT UPGRADE"
        result.recommendation = (
            "Breaking API changes detected. "
            "Code changes required before upgrade can proceed."
        )

    return result


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Assess sentence-transformers upgrade feasibility",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Only check API compatibility (no model download)",
    )
    parser.add_argument(
        "--target-version",
        default=TARGET_VERSION,
        help=f"Target version to assess (default: {TARGET_VERSION})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for decision document",
    )

    args = parser.parse_args()

    # Run assessment
    result = run_assessment(api_only=args.api_only, target_version=args.target_version)

    # Generate decision document
    doc = generate_decision_document(result)

    # Output
    output_path = args.output or OUTPUT_DIR / "sentence-transformers-upgrade-assessment.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write(doc)

    print("\n" + "=" * 60)
    print("ASSESSMENT COMPLETE")
    print("=" * 60)
    print(f"\nDecision: {result.decision}")
    print(f"\nRecommendation: {result.recommendation}")
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()
