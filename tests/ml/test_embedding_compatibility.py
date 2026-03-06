"""Embedding compatibility tests for sentence-transformers version upgrades.

Story 38.1: Embedding Compatibility Test Infrastructure

This module provides pytest-based tests to validate that embedding models produce
consistent results across sentence-transformers version upgrades. The tests
compare current embeddings against reference embeddings generated from production.

Usage:
    # Run all embedding tests
    pytest tests/ml/test_embedding_compatibility.py -v

    # Run only quick tests (no model download)
    pytest tests/ml/test_embedding_compatibility.py -v -m "not embedding_regression"

    # Run with coverage
    pytest tests/ml/test_embedding_compatibility.py --cov=tests/ml -v
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    pass

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REFERENCE_DIR = FIXTURES_DIR / "reference_embeddings"

# Model configurations for HomeIQ production
MODELS = {
    "all-MiniLM-L6-v2": {
        "dimension": 384,
        "reference_file": "all-MiniLM-L6-v2_v3.3.1.npz",
        "description": "Default lightweight model for homeiq-memory",
    },
    "BAAI/bge-large-en-v1.5": {
        "dimension": 1024,
        "reference_file": "bge-large-en-v1.5_v3.3.1.npz",
        "description": "Production model for openvino-service",
    },
}

# Similarity thresholds per Story 38.1 acceptance criteria
SIMILARITY_THRESHOLD = 0.99
DIMENSION_TOLERANCE = 0  # Dimensions must match exactly


@dataclass
class EmbeddingResult:
    """Container for embedding test results."""

    model_name: str
    embeddings: np.ndarray
    version: str
    dimension: int


@dataclass
class ComparisonResult:
    """Container for embedding comparison results."""

    model_name: str
    mean_similarity: float
    min_similarity: float
    max_similarity: float
    failed_indices: list[int]
    threshold: float
    passed: bool


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def load_reference_embeddings(model_name: str) -> tuple[np.ndarray, dict] | None:
    """Load reference embeddings for a model from fixtures.

    Returns:
        Tuple of (embeddings array, metadata dict) or None if not found.
    """
    config = MODELS.get(model_name)
    if not config:
        return None

    ref_file = REFERENCE_DIR / config["reference_file"]
    if not ref_file.exists():
        return None

    data = np.load(ref_file, allow_pickle=True)
    metadata = {}
    if "metadata" in data:
        metadata = json.loads(str(data["metadata"]))

    return data["embeddings"], metadata


def generate_embeddings(
    model_name: str, texts: list[str]
) -> EmbeddingResult | None:
    """Generate embeddings using current sentence-transformers version.

    Returns:
        EmbeddingResult or None if sentence-transformers not available.
    """
    try:
        import sentence_transformers
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    return EmbeddingResult(
        model_name=model_name,
        embeddings=embeddings,
        version=sentence_transformers.__version__,
        dimension=embeddings.shape[1],
    )


def compare_embeddings(
    current: np.ndarray,
    reference: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> ComparisonResult:
    """Compare current embeddings against reference embeddings.

    Returns:
        ComparisonResult with similarity metrics and pass/fail status.
    """
    if current.shape != reference.shape:
        return ComparisonResult(
            model_name="unknown",
            mean_similarity=0.0,
            min_similarity=0.0,
            max_similarity=0.0,
            failed_indices=list(range(len(current))),
            threshold=threshold,
            passed=False,
        )

    similarities = []
    failed_indices = []

    for i in range(len(current)):
        sim = cosine_similarity(current[i], reference[i])
        similarities.append(sim)
        if sim < threshold:
            failed_indices.append(i)

    similarities_arr = np.array(similarities)

    return ComparisonResult(
        model_name="comparison",
        mean_similarity=float(similarities_arr.mean()),
        min_similarity=float(similarities_arr.min()),
        max_similarity=float(similarities_arr.max()),
        failed_indices=failed_indices,
        threshold=threshold,
        passed=len(failed_indices) == 0,
    )


class TestEmbeddingDimensions:
    """Test embedding dimension consistency."""

    @pytest.mark.parametrize("model_name,config", MODELS.items())
    def test_expected_dimensions_documented(
        self, model_name: str, config: dict
    ) -> None:
        """Verify expected dimensions are documented for each model."""
        assert "dimension" in config, f"Missing dimension for {model_name}"
        assert config["dimension"] > 0, f"Invalid dimension for {model_name}"

    def test_minilm_dimension(self) -> None:
        """all-MiniLM-L6-v2 should produce 384-dim embeddings."""
        assert MODELS["all-MiniLM-L6-v2"]["dimension"] == 384

    def test_bge_dimension(self) -> None:
        """BAAI/bge-large-en-v1.5 should produce 1024-dim embeddings."""
        assert MODELS["BAAI/bge-large-en-v1.5"]["dimension"] == 1024


class TestReferenceEmbeddings:
    """Test reference embedding fixtures."""

    def test_fixtures_directory_exists(self, fixtures_dir: Path) -> None:
        """Fixtures directory should exist."""
        assert fixtures_dir.exists(), "Fixtures directory missing"

    def test_reference_directory_exists(
        self, reference_embeddings_dir: Path
    ) -> None:
        """Reference embeddings directory should exist."""
        assert reference_embeddings_dir.exists(), "Reference dir missing"

    def test_test_sentences_exist(self, test_sentences: list[str]) -> None:
        """Test sentences fixture should have content."""
        assert len(test_sentences) >= 100, "Need at least 100 test sentences"

    def test_test_sentences_coverage(self, test_sentences: list[str]) -> None:
        """Test sentences should cover various use cases."""
        text = " ".join(test_sentences).lower()

        # Device control keywords
        assert "turn on" in text, "Missing device control sentences"
        assert "thermostat" in text, "Missing thermostat sentences"

        # Time-based keywords
        assert "morning" in text, "Missing time-based sentences"
        assert "sunset" in text, "Missing sunset sentences"

        # Conditional keywords
        assert "if" in text, "Missing conditional sentences"
        assert "when" in text, "Missing trigger sentences"


class TestCosineSimlarityFunction:
    """Test the cosine similarity computation."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have similarity 1.0."""
        vec = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors should have similarity 0.0."""
        vec_a = np.array([1.0, 0.0, 0.0])
        vec_b = np.array([0.0, 1.0, 0.0])
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        """Opposite vectors should have similarity -1.0."""
        vec_a = np.array([1.0, 2.0, 3.0])
        vec_b = -vec_a
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(-1.0)

    def test_zero_vector_handling(self) -> None:
        """Zero vectors should return 0.0 similarity."""
        vec_a = np.array([1.0, 2.0, 3.0])
        vec_b = np.array([0.0, 0.0, 0.0])
        assert cosine_similarity(vec_a, vec_b) == 0.0

    def test_normalized_vectors(self) -> None:
        """Normalized vectors should work correctly."""
        vec_a = np.array([0.6, 0.8, 0.0])
        vec_b = np.array([0.8, 0.6, 0.0])
        expected = 0.6 * 0.8 + 0.8 * 0.6  # 0.96
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(expected)


class TestComparisonResult:
    """Test comparison result logic."""

    def test_comparison_passes_when_all_above_threshold(self) -> None:
        """Comparison should pass when all similarities >= threshold."""
        current = np.array([[1.0, 0.0], [0.0, 1.0]])
        reference = current.copy()

        result = compare_embeddings(current, reference, threshold=0.99)

        assert result.passed
        assert len(result.failed_indices) == 0
        assert result.mean_similarity == pytest.approx(1.0)

    def test_comparison_fails_when_below_threshold(self) -> None:
        """Comparison should fail when any similarity < threshold."""
        current = np.array([[1.0, 0.0], [0.0, 1.0]])
        reference = np.array([[1.0, 0.0], [1.0, 0.0]])  # Second is different

        result = compare_embeddings(current, reference, threshold=0.99)

        assert not result.passed
        assert 1 in result.failed_indices

    def test_comparison_fails_on_shape_mismatch(self) -> None:
        """Comparison should fail when shapes don't match."""
        current = np.array([[1.0, 0.0]])
        reference = np.array([[1.0, 0.0, 0.0]])

        result = compare_embeddings(current, reference)

        assert not result.passed


@pytest.mark.embedding_regression
@pytest.mark.slow
class TestEmbeddingCompatibility:
    """Embedding compatibility tests requiring model download.

    These tests compare current embeddings against reference embeddings
    to ensure version upgrades don't break embedding compatibility.

    Requires: sentence-transformers installed
    """

    @pytest.fixture(scope="class")
    def sentence_transformers_available(self) -> bool:
        """Check if sentence-transformers is available."""
        import importlib.util
        return importlib.util.find_spec("sentence_transformers") is not None

    @pytest.mark.parametrize("model_name", list(MODELS.keys()))
    def test_embedding_generation(
        self,
        model_name: str,
        test_sentences: list[str],
        sentence_transformers_available: bool,
    ) -> None:
        """Test that embeddings can be generated for each model."""
        if not sentence_transformers_available:
            pytest.skip("sentence-transformers not installed")

        result = generate_embeddings(model_name, test_sentences[:10])

        assert result is not None, f"Failed to generate embeddings for {model_name}"
        assert result.embeddings.shape[0] == 10
        expected_dim = MODELS[model_name]["dimension"]
        assert result.dimension == expected_dim, (
            f"Dimension mismatch: got {result.dimension}, expected {expected_dim}"
        )

    @pytest.mark.parametrize("model_name", list(MODELS.keys()))
    def test_embedding_compatibility_vs_reference(
        self,
        model_name: str,
        test_sentences: list[str],
        similarity_threshold: float,
        sentence_transformers_available: bool,
    ) -> None:
        """Test embedding compatibility against reference embeddings.

        This is the primary acceptance test for Story 38.1.
        Embeddings must have >=0.99 cosine similarity to reference.
        """
        if not sentence_transformers_available:
            pytest.skip("sentence-transformers not installed")

        # Load reference
        ref_data = load_reference_embeddings(model_name)
        if ref_data is None:
            pytest.skip(f"Reference embeddings not found for {model_name}")

        reference_embeddings, metadata = ref_data

        # Generate current embeddings
        result = generate_embeddings(model_name, test_sentences)
        assert result is not None

        # Compare
        comparison = compare_embeddings(
            result.embeddings,
            reference_embeddings,
            threshold=similarity_threshold,
        )

        # Report details on failure
        if not comparison.passed:
            failed_texts = [test_sentences[i] for i in comparison.failed_indices[:5]]
            pytest.fail(
                f"Embedding compatibility failed for {model_name}:\n"
                f"  Mean similarity: {comparison.mean_similarity:.4f}\n"
                f"  Min similarity: {comparison.min_similarity:.4f}\n"
                f"  Threshold: {similarity_threshold}\n"
                f"  Failed sentences ({len(comparison.failed_indices)} total): {failed_texts}"
            )

        assert comparison.passed, (
            f"Embeddings for {model_name} below {similarity_threshold} threshold"
        )

    @pytest.mark.parametrize("model_name", list(MODELS.keys()))
    def test_embedding_normalization(
        self,
        model_name: str,
        test_sentences: list[str],
        sentence_transformers_available: bool,
    ) -> None:
        """Test that embeddings are properly normalized (unit length)."""
        if not sentence_transformers_available:
            pytest.skip("sentence-transformers not installed")

        result = generate_embeddings(model_name, test_sentences[:20])
        assert result is not None

        norms = np.linalg.norm(result.embeddings, axis=1)

        # Allow small tolerance for numerical precision
        assert np.all(norms > 0.99), "Some embeddings have near-zero norm"
        assert np.all(norms < 1.01), "Some embeddings are not normalized"

    @pytest.mark.parametrize("model_name", list(MODELS.keys()))
    def test_embedding_determinism(
        self,
        model_name: str,
        sentence_transformers_available: bool,
    ) -> None:
        """Test that embedding generation is deterministic."""
        if not sentence_transformers_available:
            pytest.skip("sentence-transformers not installed")

        texts = ["Turn on the lights", "Set temperature to 72"]

        result1 = generate_embeddings(model_name, texts)
        result2 = generate_embeddings(model_name, texts)

        assert result1 is not None and result2 is not None

        for i in range(len(texts)):
            sim = cosine_similarity(result1.embeddings[i], result2.embeddings[i])
            assert sim == pytest.approx(1.0, abs=1e-6), (
                f"Non-deterministic embeddings for '{texts[i]}'"
            )


class TestModelMetadata:
    """Test model metadata and configuration."""

    def test_all_models_have_reference_file(self) -> None:
        """All models should have reference file configured."""
        for model_name, config in MODELS.items():
            assert "reference_file" in config, (
                f"Missing reference_file for {model_name}"
            )

    def test_all_models_have_description(self) -> None:
        """All models should have description."""
        for model_name, config in MODELS.items():
            assert "description" in config, (
                f"Missing description for {model_name}"
            )
            assert len(config["description"]) > 10, (
                f"Description too short for {model_name}"
            )


def test_similarity_threshold_is_strict() -> None:
    """Verify the similarity threshold meets Story 38.1 requirements."""
    assert SIMILARITY_THRESHOLD >= 0.99, (
        "Threshold must be >=0.99 per Story 38.1"
    )
