#!/usr/bin/env python3
"""Generate reference embeddings for embedding compatibility testing.

Story 38.1: Embedding Compatibility Test Infrastructure

This script generates reference embeddings from the current sentence-transformers
version and saves them to the test fixtures directory. These reference embeddings
are used by the compatibility tests to verify that version upgrades don't break
embedding consistency.

Usage:
    # Generate reference embeddings for all models
    python scripts/generate_reference_embeddings.py

    # Generate for a specific model
    python scripts/generate_reference_embeddings.py --model all-MiniLM-L6-v2

    # Generate with custom output directory
    python scripts/generate_reference_embeddings.py --output-dir custom/path

Requirements:
    - sentence-transformers (current production version: 3.3.1)
    - numpy
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# Default paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "ml" / "fixtures"
REFERENCE_DIR = FIXTURES_DIR / "reference_embeddings"
SENTENCES_FILE = FIXTURES_DIR / "test_sentences.json"

# Model configurations matching test_embedding_compatibility.py
MODELS = {
    "all-MiniLM-L6-v2": {
        "dimension": 384,
        "description": "Default lightweight model for homeiq-memory",
    },
    "BAAI/bge-large-en-v1.5": {
        "dimension": 1024,
        "description": "Production model for openvino-service",
    },
}


def load_test_sentences(sentences_file: Path | None = None) -> list[str]:
    """Load test sentences from fixture file."""
    file_path = sentences_file or SENTENCES_FILE

    if not file_path.exists():
        print(f"Error: Test sentences file not found: {file_path}")
        sys.exit(1)

    with open(file_path, encoding="utf-8") as f:
        sentences = json.load(f)

    print(f"Loaded {len(sentences)} test sentences from {file_path}")
    return sentences


def generate_embeddings_for_model(
    model_name: str,
    sentences: list[str],
    output_dir: Path,
) -> bool:
    """Generate and save reference embeddings for a model.

    Returns:
        True if successful, False otherwise.
    """
    try:
        import sentence_transformers
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("Error: sentence-transformers not installed")
        print("Install with: pip install sentence-transformers==3.3.1")
        return False

    version = sentence_transformers.__version__
    print(f"\n{'='*60}")
    print(f"Model: {model_name}")
    print(f"sentence-transformers version: {version}")
    print(f"{'='*60}")

    # Load model
    print("Loading model...")
    model = SentenceTransformer(model_name)

    # Generate embeddings
    print(f"Generating embeddings for {len(sentences)} sentences...")
    embeddings = model.encode(
        sentences,
        convert_to_numpy=True,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    # Validate dimensions
    expected_dim = MODELS[model_name]["dimension"]
    actual_dim = embeddings.shape[1]
    if actual_dim != expected_dim:
        print("Warning: Dimension mismatch!")
        print(f"  Expected: {expected_dim}")
        print(f"  Actual: {actual_dim}")

    # Create metadata
    metadata = {
        "model_name": model_name,
        "sentence_transformers_version": version,
        "generated_at": datetime.now().isoformat(),
        "num_sentences": len(sentences),
        "embedding_dimension": actual_dim,
        "normalized": True,
        "description": MODELS[model_name]["description"],
    }

    # Sanitize model name for filename
    safe_name = model_name.replace("/", "-")
    output_file = output_dir / f"{safe_name}_v{version}.npz"

    # Save embeddings
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_file,
        embeddings=embeddings,
        metadata=json.dumps(metadata),
    )

    print("\nSaved reference embeddings:")
    print(f"  File: {output_file}")
    print(f"  Shape: {embeddings.shape}")
    print(f"  Dimension: {actual_dim}")

    # Print sample statistics
    print("\nEmbedding statistics:")
    print(f"  Mean norm: {np.linalg.norm(embeddings, axis=1).mean():.4f}")
    print(f"  Min value: {embeddings.min():.4f}")
    print(f"  Max value: {embeddings.max():.4f}")

    return True


def verify_reference_embeddings(
    model_name: str,
    sentences: list[str],
    output_dir: Path,
) -> bool:
    """Verify saved reference embeddings can be loaded correctly."""
    try:
        import sentence_transformers
        version = sentence_transformers.__version__
    except ImportError:
        return False

    safe_name = model_name.replace("/", "-")
    ref_file = output_dir / f"{safe_name}_v{version}.npz"

    if not ref_file.exists():
        print(f"Error: Reference file not found: {ref_file}")
        return False

    data = np.load(ref_file, allow_pickle=True)
    embeddings = data["embeddings"]
    metadata = json.loads(str(data["metadata"]))

    print(f"\nVerification for {model_name}:")
    print(f"  Sentences: {len(sentences)}")
    print(f"  Embeddings shape: {embeddings.shape}")
    print(f"  Metadata version: {metadata['sentence_transformers_version']}")

    if embeddings.shape[0] != len(sentences):
        print("  ERROR: Count mismatch!")
        return False

    print("  VERIFIED")
    return True


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate reference embeddings for compatibility testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        help="Generate for specific model only",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REFERENCE_DIR,
        help=f"Output directory (default: {REFERENCE_DIR})",
    )

    parser.add_argument(
        "--sentences-file",
        type=Path,
        help=f"Test sentences file (default: {SENTENCES_FILE})",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing reference embeddings",
    )

    args = parser.parse_args()

    # Load test sentences
    sentences = load_test_sentences(args.sentences_file)

    # Determine which models to process
    models_to_process = [args.model] if args.model else list(MODELS.keys())

    if args.verify_only:
        print("\nVerifying existing reference embeddings...")
        all_verified = True
        for model_name in models_to_process:
            if not verify_reference_embeddings(model_name, sentences, args.output_dir):
                all_verified = False

        if all_verified:
            print("\n All reference embeddings verified successfully")
        else:
            print("\n Some reference embeddings failed verification")
            sys.exit(1)
        return

    # Generate embeddings
    print(f"\nGenerating reference embeddings for {len(models_to_process)} model(s)")
    print(f"Output directory: {args.output_dir}")

    success_count = 0
    for model_name in models_to_process:
        if generate_embeddings_for_model(model_name, sentences, args.output_dir):
            success_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Models processed: {len(models_to_process)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(models_to_process) - success_count}")

    if success_count < len(models_to_process):
        sys.exit(1)

    # Verify
    print("\nVerifying saved embeddings...")
    for model_name in models_to_process:
        verify_reference_embeddings(model_name, sentences, args.output_dir)

    print("\n Reference embeddings generated successfully!")
    print("\nNext steps:")
    print(f"  1. Commit the reference files in {args.output_dir}")
    print("  2. Run: pytest tests/ml/test_embedding_compatibility.py -v")


if __name__ == "__main__":
    main()
