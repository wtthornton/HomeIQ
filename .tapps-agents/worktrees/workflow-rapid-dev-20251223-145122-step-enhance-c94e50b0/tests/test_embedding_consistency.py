#!/usr/bin/env python3
"""
Test embedding consistency between sentence-transformers versions
Phase 3 AI/ML Stack Updates - Critical Decision Point

This script tests whether upgrading from sentence-transformers 3.3.1 to 5.1.2
will maintain embedding consistency for the all-MiniLM-L6-v2 model.

Usage:
    # Install old version and generate embeddings
    pip install sentence-transformers==3.3.1
    python test_embedding_consistency.py --generate old

    # Install new version and generate embeddings
    pip install sentence-transformers==5.1.2
    python test_embedding_consistency.py --generate new

    # Compare embeddings
    python test_embedding_consistency.py --compare

Author: HomeIQ Dependency Upgrade Analysis
Date: November 15, 2025
"""

import argparse
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import sys

# Test sentences covering various use cases in HomeIQ
TEST_SENTENCES = [
    # Device control scenarios
    "Turn on the living room lights",
    "Set the thermostat to 72 degrees",
    "Turn off all lights in the bedroom",
    "Open the garage door",

    # Time-based patterns
    "Every morning at 7am",
    "When I arrive home",
    "At sunset",
    "Between 10pm and 6am",

    # Conditional logic
    "If temperature is above 75 degrees",
    "When motion is detected",
    "If humidity exceeds 60%",
    "When door is opened",

    # Device types
    "light switch bedroom",
    "temperature sensor kitchen",
    "motion detector hallway",
    "smart plug office",

    # Actions
    "turn on",
    "turn off",
    "set to",
    "adjust",
    "toggle",

    # States
    "is on",
    "is off",
    "is open",
    "is closed",
    "is detected",

    # Complex automations
    "Turn on lights when motion is detected after sunset",
    "Set thermostat to 68 when leaving home",
    "Turn off all devices at bedtime",
    "Notify me when door opens while away",

    # Synergy patterns (multi-device)
    "lights and thermostat",
    "motion sensor triggers light",
    "temperature affects fan speed",
    "door sensor and security system",

    # Edge cases
    "",  # Empty string
    "a",  # Single character
    "The quick brown fox jumps over the lazy dog",  # Standard test
    "🏠 Smart home automation 🤖",  # Emojis
]

def generate_embeddings(version: str, model_name: str = "all-MiniLM-L6-v2"):
    """Generate embeddings using current sentence-transformers version"""
    try:
        from sentence_transformers import SentenceTransformer
        import sentence_transformers

        print(f"\n{'='*80}")
        print(f"Generating Embeddings - sentence-transformers {sentence_transformers.__version__}")
        print(f"Model: {model_name}")
        print(f"{'='*80}\n")

        # Load model
        print(f"Loading model: {model_name}...")
        model = SentenceTransformer(model_name)
        print(f"✓ Model loaded successfully")

        # Generate embeddings
        print(f"\nGenerating embeddings for {len(TEST_SENTENCES)} test sentences...")
        embeddings = model.encode(TEST_SENTENCES, show_progress_bar=True)

        # Save results
        output_dir = Path("embedding_tests")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"embeddings_{version}.npz"
        np.savez(output_file, embeddings=embeddings)

        # Save metadata
        metadata = {
            "version": sentence_transformers.__version__,
            "model_name": model_name,
            "num_sentences": len(TEST_SENTENCES),
            "embedding_dim": embeddings.shape[1],
            "test_sentences": TEST_SENTENCES
        }

        metadata_file = output_dir / f"metadata_{version}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n✓ Embeddings saved to: {output_file}")
        print(f"✓ Metadata saved to: {metadata_file}")
        print(f"\nEmbedding shape: {embeddings.shape}")
        print(f"Embedding dimension: {embeddings.shape[1]}")
        print(f"Embedding dtype: {embeddings.dtype}")

        # Show sample embedding stats
        print(f"\nSample embedding statistics (first sentence):")
        print(f"  Mean: {embeddings[0].mean():.6f}")
        print(f"  Std:  {embeddings[0].std():.6f}")
        print(f"  Min:  {embeddings[0].min():.6f}")
        print(f"  Max:  {embeddings[0].max():.6f}")

        return embeddings, metadata

    except ImportError as e:
        print(f"❌ Error: sentence-transformers not installed or import failed")
        print(f"   {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        sys.exit(1)


def compare_embeddings():
    """Compare embeddings from old and new versions"""
    print(f"\n{'='*80}")
    print(f"Comparing Embeddings: sentence-transformers 3.3.1 vs 5.1.2")
    print(f"{'='*80}\n")

    output_dir = Path("embedding_tests")

    # Load old embeddings
    old_file = output_dir / "embeddings_old.npz"
    new_file = output_dir / "embeddings_new.npz"

    if not old_file.exists():
        print(f"❌ Error: Old embeddings not found at {old_file}")
        print(f"   Run: python test_embedding_consistency.py --generate old")
        sys.exit(1)

    if not new_file.exists():
        print(f"❌ Error: New embeddings not found at {new_file}")
        print(f"   Run: python test_embedding_consistency.py --generate new")
        sys.exit(1)

    # Load embeddings
    old_data = np.load(old_file)
    new_data = np.load(new_file)

    old_embeddings = old_data['embeddings']
    new_embeddings = new_data['embeddings']

    # Load metadata
    old_meta_file = output_dir / "metadata_old.json"
    new_meta_file = output_dir / "metadata_new.json"

    with open(old_meta_file) as f:
        old_meta = json.load(f)
    with open(new_meta_file) as f:
        new_meta = json.load(f)

    print(f"Old version: sentence-transformers {old_meta['version']}")
    print(f"New version: sentence-transformers {new_meta['version']}")
    print(f"Model: {old_meta['model_name']}")
    print(f"Test sentences: {len(TEST_SENTENCES)}")
    print(f"\nOld embedding shape: {old_embeddings.shape}")
    print(f"New embedding shape: {new_embeddings.shape}")

    # Check dimensions match
    if old_embeddings.shape != new_embeddings.shape:
        print(f"\n❌ CRITICAL: Embedding dimensions don't match!")
        print(f"   Old: {old_embeddings.shape}")
        print(f"   New: {new_embeddings.shape}")
        print(f"\n⚠️  RECOMMENDATION: DO NOT UPGRADE - Incompatible embeddings")
        return False

    print(f"\n✓ Embedding dimensions match: {old_embeddings.shape}")

    # Compute similarity metrics
    print(f"\n{'='*80}")
    print(f"Similarity Analysis")
    print(f"{'='*80}\n")

    similarities = []
    cosine_similarities = []
    euclidean_distances = []

    for i in range(len(TEST_SENTENCES)):
        old_emb = old_embeddings[i]
        new_emb = new_embeddings[i]

        # Cosine similarity
        cosine_sim = np.dot(old_emb, new_emb) / (np.linalg.norm(old_emb) * np.linalg.norm(new_emb))
        cosine_similarities.append(cosine_sim)

        # Euclidean distance
        euclidean_dist = np.linalg.norm(old_emb - new_emb)
        euclidean_distances.append(euclidean_dist)

        # L1 distance
        l1_dist = np.abs(old_emb - new_emb).sum()
        similarities.append(cosine_sim)

    cosine_similarities = np.array(cosine_similarities)
    euclidean_distances = np.array(euclidean_distances)

    # Print statistics
    print(f"Cosine Similarity Statistics:")
    print(f"  Mean:   {cosine_similarities.mean():.6f}")
    print(f"  Median: {np.median(cosine_similarities):.6f}")
    print(f"  Std:    {cosine_similarities.std():.6f}")
    print(f"  Min:    {cosine_similarities.min():.6f}")
    print(f"  Max:    {cosine_similarities.max():.6f}")

    print(f"\nEuclidean Distance Statistics:")
    print(f"  Mean:   {euclidean_distances.mean():.6f}")
    print(f"  Median: {np.median(euclidean_distances):.6f}")
    print(f"  Std:    {euclidean_distances.std():.6f}")
    print(f"  Min:    {euclidean_distances.min():.6f}")
    print(f"  Max:    {euclidean_distances.max():.6f}")

    # Show sentences with lowest similarity
    print(f"\n{'='*80}")
    print(f"Sentences with Lowest Cosine Similarity (Top 10)")
    print(f"{'='*80}\n")

    lowest_indices = np.argsort(cosine_similarities)[:10]
    for idx in lowest_indices:
        print(f"Similarity: {cosine_similarities[idx]:.6f} - \"{TEST_SENTENCES[idx]}\"")

    # Decision criteria
    print(f"\n{'='*80}")
    print(f"Compatibility Assessment")
    print(f"{'='*80}\n")

    mean_similarity = cosine_similarities.mean()
    min_similarity = cosine_similarities.min()

    print(f"Mean cosine similarity: {mean_similarity:.6f}")
    print(f"Min cosine similarity:  {min_similarity:.6f}")

    # Decision thresholds
    EXCELLENT_THRESHOLD = 0.999
    GOOD_THRESHOLD = 0.99
    ACCEPTABLE_THRESHOLD = 0.95
    RISKY_THRESHOLD = 0.90

    print(f"\n{'='*80}")
    print(f"RECOMMENDATION")
    print(f"{'='*80}\n")

    if mean_similarity >= EXCELLENT_THRESHOLD and min_similarity >= EXCELLENT_THRESHOLD:
        print(f"✅ EXCELLENT COMPATIBILITY")
        print(f"   Mean similarity: {mean_similarity:.6f} >= {EXCELLENT_THRESHOLD}")
        print(f"   Min similarity:  {min_similarity:.6f} >= {EXCELLENT_THRESHOLD}")
        print(f"\n   ✓ SAFE TO UPGRADE - Embeddings are virtually identical")
        print(f"   ✓ No re-indexing required")
        print(f"   ✓ Proceed with Phase 3A (full upgrade)")
        return True

    elif mean_similarity >= GOOD_THRESHOLD and min_similarity >= ACCEPTABLE_THRESHOLD:
        print(f"✓ GOOD COMPATIBILITY")
        print(f"   Mean similarity: {mean_similarity:.6f} >= {GOOD_THRESHOLD}")
        print(f"   Min similarity:  {min_similarity:.6f} >= {ACCEPTABLE_THRESHOLD}")
        print(f"\n   ✓ SAFE TO UPGRADE - Minor differences detected")
        print(f"   ⚠  Consider re-indexing stored embeddings for optimal performance")
        print(f"   ✓ Proceed with Phase 3A (with optional re-indexing)")
        return True

    elif mean_similarity >= ACCEPTABLE_THRESHOLD:
        print(f"⚠️  ACCEPTABLE COMPATIBILITY")
        print(f"   Mean similarity: {mean_similarity:.6f} >= {ACCEPTABLE_THRESHOLD}")
        print(f"   Min similarity:  {min_similarity:.6f}")
        print(f"\n   ⚠  UPGRADE WITH CAUTION - Noticeable differences detected")
        print(f"   ⚠  RE-INDEXING REQUIRED for stored embeddings")
        print(f"   ⚠  Test thoroughly before production deployment")
        print(f"   → Consider Phase 3B first (skip sentence-transformers)")
        return None  # Uncertain

    else:
        print(f"❌ POOR COMPATIBILITY")
        print(f"   Mean similarity: {mean_similarity:.6f} < {ACCEPTABLE_THRESHOLD}")
        print(f"   Min similarity:  {min_similarity:.6f}")
        print(f"\n   ❌ DO NOT UPGRADE - Significant differences detected")
        print(f"   ❌ Would break existing embedding-based features")
        print(f"   → Proceed with Phase 3B (pin sentence-transformers to 3.x)")
        print(f"   → Or plan major re-indexing effort")
        return False

    # Save comparison report
    report = {
        "old_version": old_meta['version'],
        "new_version": new_meta['version'],
        "model_name": old_meta['model_name'],
        "mean_cosine_similarity": float(mean_similarity),
        "min_cosine_similarity": float(min_similarity),
        "max_cosine_similarity": float(cosine_similarities.max()),
        "mean_euclidean_distance": float(euclidean_distances.mean()),
        "recommendation": "See script output"
    }

    report_file = output_dir / "comparison_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Comparison report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Test sentence-transformers embedding consistency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate embeddings with old version (3.3.1)
  pip install sentence-transformers==3.3.1
  python test_embedding_consistency.py --generate old

  # Generate embeddings with new version (5.1.2)
  pip install sentence-transformers==5.1.2
  python test_embedding_consistency.py --generate new

  # Compare embeddings
  python test_embedding_consistency.py --compare
        """
    )

    parser.add_argument(
        '--generate',
        choices=['old', 'new'],
        help='Generate embeddings for old or new version'
    )

    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare old and new embeddings'
    )

    parser.add_argument(
        '--model',
        default='all-MiniLM-L6-v2',
        help='Model name to use (default: all-MiniLM-L6-v2)'
    )

    args = parser.parse_args()

    if args.generate:
        generate_embeddings(args.generate, args.model)
    elif args.compare:
        compare_embeddings()
    else:
        parser.print_help()
        print("\n❌ Error: Must specify --generate or --compare")
        sys.exit(1)


if __name__ == "__main__":
    main()
