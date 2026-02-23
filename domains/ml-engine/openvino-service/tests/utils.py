"""
Test helpers for OpenVINO service.

Provides deterministic fake models so we can exercise the async OpenVINOManager
logic without downloading hundreds of megabytes of weights during CI.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

try:
    from src.models.openvino_manager import OpenVINOManager
except ImportError:
    # Fallback for when path setup hasn't run yet
    import sys
    from pathlib import Path
    test_dir = Path(__file__).resolve().parent
    service_dir = test_dir.parent
    src_dir = service_dir / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from models.openvino_manager import OpenVINOManager


# Epic 47: BGE-M3 Embedding Model (1024-dim)
EMBEDDING_DIMENSION = 1024


def _stable_seed(text: str) -> int:
    """Create a deterministic seed for a given piece of text."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def deterministic_embedding(text: str, dimension: int = EMBEDDING_DIMENSION) -> np.ndarray:
    """
    Return a normalized, deterministic embedding for the provided text.

    The randomness is derived from the SHA256 hash which keeps results stable
    across test runs while still producing varied vectors.
    """
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        tokens = [text.lower()]

    vectors = []
    for token in tokens:
        rng = np.random.default_rng(_stable_seed(token))
        vectors.append(rng.standard_normal(dimension))

    vector = np.mean(vectors, axis=0)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return np.zeros(dimension)
    return vector / norm


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Cosine similarity for numpy vectors."""
    a = np.asarray(vec_a)
    b = np.asarray(vec_b)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


class FakeSentenceTransformer:
    """Minimal stand-in for sentence-transformers SentenceTransformer."""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        """Initialize with embedding dimension (1024 for BGE-large-en-v1.5)."""
        self.dimension = dimension

    def encode(self, texts: Iterable[str], convert_to_numpy: bool = True) -> np.ndarray:
        vectors = [deterministic_embedding(text, dimension=self.dimension) for text in texts]
        return np.stack(vectors)


class _FakeScalar:
    def __init__(self, value: float):
        self._value = value

    def item(self) -> float:
        return self._value


class _FakeTensor:
    """Fake tensor that supports indexing and detach/cpu/tolist for batched logits."""

    def __init__(self, values: list[list[float]]):
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, tuple):
            # Handle [:, 0] style indexing
            rows, col = key
            if isinstance(rows, slice) and col == 0:
                return _FakeColumn([row[0] for row in self._values])
        return self._values[key]


class _FakeColumn:
    """Fake column tensor that supports detach().cpu().tolist()."""

    def __init__(self, values: list[float]):
        self._values = values

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self) -> list[float]:
        return self._values


class _FakeLogits:
    """Fake model output supporting both single and batch modes."""

    def __init__(self, values: list[list[float]]):
        self.logits = _FakeTensor(values)


class FakeRerankerTokenizer:
    """Tokenizer stand-in that supports both single-pair and batch-pair modes (HIGH-5)."""

    def __call__(self, pairs, **_: Any) -> dict[str, Any]:
        # Support both single string and list of strings
        if isinstance(pairs, str):
            pairs = [pairs]
        return {"pairs": pairs}


class FakeRerankerModel:
    """Produces similarity-based scores without Torch dependencies.

    HIGH-5: Updated to support batched inference -- accepts a list of pairs
    and returns logits with shape (N, 1).
    """

    def __call__(self, **inputs: Any) -> _FakeLogits:
        pairs = inputs["pairs"]
        values = []
        for pair in pairs:
            if "[SEP]" in pair:
                query, candidate = [segment.strip() for segment in pair.split("[SEP]", 1)]
            else:
                query, candidate = pair, pair

            query_vec = deterministic_embedding(query)
            candidate_vec = deterministic_embedding(candidate)
            score = cosine_similarity(query_vec, candidate_vec)
            values.append([score])
        return _FakeLogits(values)


class FakeClassifierTokenizer:
    """Tokenizer that only needs to round-trip prompt text."""

    def __call__(self, prompt: str, **_: Any) -> dict[str, str]:
        return {"prompt": prompt}

    def decode(self, generated: str, skip_special_tokens: bool = True) -> str:
        return generated


class FakeClassifierModel:
    """Rule-based responses for category/priority prompts."""

    def generate(self, *, prompt: str, **_: Any) -> list[str]:
        prompt_lower = prompt.lower()
        pattern_segment = self._extract_pattern_segment(prompt_lower)
        if "priority" in prompt_lower:
            return [self._priority_for_prompt(pattern_segment)]
        return [self._category_for_prompt(pattern_segment)]

    def _extract_pattern_segment(self, prompt_lower: str) -> str:
        if "pattern:" in prompt_lower:
            segment = prompt_lower.split("pattern:", 1)[1]
            if "respond with" in segment:
                segment = segment.split("respond with", 1)[0]
            if "category:" in segment:
                segment = segment.split("category:", 1)[0]
            if "priority:" in segment:
                segment = segment.split("priority:", 1)[0]
            return segment
        return prompt_lower

    def _category_for_prompt(self, prompt_lower: str) -> str:
        tokens = set(re.findall(r"\w+", prompt_lower))
        if tokens.intersection({"power", "battery", "charger", "energy", "solar", "usage"}):
            return "energy"
        if tokens.intersection({"comfort", "climate", "temperature", "lighting", "thermostat"}):
            return "comfort"
        if tokens.intersection({"lock", "door", "alarm", "camera", "security", "motion"}):
            return "security"
        return "convenience"

    def _priority_for_prompt(self, prompt_lower: str) -> str:
        tokens = set(re.findall(r"\w+", prompt_lower))
        if "water leak" in prompt_lower:
            return "high"
        if tokens.intersection({"fire", "alarm", "intruder", "leak", "door", "panic"}):
            return "high"
        if tokens.intersection({"routine", "reminder", "calendar", "notification"}):
            return "low"
        return "medium"


class TestOpenVINOManager(OpenVINOManager):
    """
    OpenVINO manager variant that wires in fake models for deterministic testing.
    """

    def __init__(self, models_dir: str):
        super().__init__(models_dir=models_dir)
        # Lazily populated -- the overridden _load_* methods will assign them.

    async def _load_embedding_model(self):
        if self._embed_model is None:
            self._embed_model = FakeSentenceTransformer(dimension=1024)
            self._embed_tokenizer = None

    async def _load_reranker_model(self):
        if self._reranker_model is None:
            self._reranker_model = FakeRerankerModel()
            self._reranker_tokenizer = FakeRerankerTokenizer()

    async def _load_classifier_model(self):
        if self._classifier_model is None:
            self._classifier_model = FakeClassifierModel()
            self._classifier_tokenizer = FakeClassifierTokenizer()

    async def _run_blocking(self, func, *args, timeout=None, **kwargs):
        """Bypass threadpool and semaphore to keep tests fast."""
        result = func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result
