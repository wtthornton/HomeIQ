"""Embedding generation for memory content using sentence-transformers.

This module provides async-compatible embedding generation with lazy model loading
and support for air-gapped environments via local model paths.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_thread_pool: ThreadPoolExecutor | None = None


def _get_thread_pool() -> ThreadPoolExecutor:
    """Get or create the shared thread pool for embedding generation."""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embedding")
    return _thread_pool


class EmbeddingGenerator:
    """Generate embeddings for memory content using sentence-transformers.

    Supports lazy loading, air-gapped environments (local model paths),
    and automatic device detection (CPU/CUDA).

    Example:
        >>> generator = EmbeddingGenerator()
        >>> embedding = await generator.generate("Hello world")
        >>> len(embedding)
        384

    Example with custom model:
        >>> generator = EmbeddingGenerator(model_name="nomic-ai/nomic-embed-text-v1.5")
        >>> embedding = await generator.generate("Hello world")
        >>> len(embedding)
        768
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"  # 384-dim, fast
    ALTERNATIVE_MODEL = "nomic-ai/nomic-embed-text-v1.5"  # 768-dim, better quality

    MODEL_DIMENSIONS: dict[str, int] = {
        "all-MiniLM-L6-v2": 384,
        "nomic-ai/nomic-embed-text-v1.5": 768,
    }

    def __init__(
        self,
        model_name: str | None = None,
        model_path: str | None = None,
        device: str | None = None,
    ) -> None:
        """Initialize the embedding generator.

        Args:
            model_name: HuggingFace model identifier. Defaults to all-MiniLM-L6-v2.
            model_path: Local path to model files for air-gapped environments.
                        If provided, takes precedence over model_name.
            device: Device to run model on ("cpu" or "cuda"). Auto-detects if None.
        """
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model_path = model_path
        self._device = device
        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None

    def _load_model(self) -> None:
        """Load the SentenceTransformer model on first use.

        Raises:
            ImportError: If sentence-transformers is not installed.
        """
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for embedding generation. "
                "Install with: pip install homeiq-memory[embeddings] "
                "or: pip install sentence-transformers torch"
            ) from e

        model_source = self._model_path or self._model_name
        device = self._device or self._detect_device()

        logger.info(
            "Loading embedding model: %s on device: %s",
            model_source,
            device,
        )

        self._model = SentenceTransformer(model_source, device=device)
        self._dimension = self._model.get_sentence_embedding_dimension()

        logger.info(
            "Embedding model loaded. Dimension: %d",
            self._dimension,
        )

    def _detect_device(self) -> str:
        """Auto-detect the best available device."""
        try:
            import torch

            if torch.cuda.is_available():
                logger.info("CUDA available, using GPU")
                return "cuda"
        except ImportError:
            pass

        logger.debug("Using CPU for embeddings")
        return "cpu"

    @property
    def dimension(self) -> int:
        """Return the embedding dimension.

        Returns known dimension for standard models without loading,
        otherwise loads the model to determine dimension.

        Returns:
            Embedding vector dimension (e.g., 384 for MiniLM, 768 for nomic).
        """
        if self._dimension is not None:
            return self._dimension

        if self._model_path is None and self._model_name in self.MODEL_DIMENSIONS:
            return self.MODEL_DIMENSIONS[self._model_name]

        self._load_model()
        if self._dimension is None:
            raise RuntimeError("Model loaded but dimension not set")
        return self._dimension

    async def generate(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text content to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            ImportError: If sentence-transformers is not installed.
            RuntimeError: If model fails to load.
        """
        self._load_model()
        if self._model is None:
            raise RuntimeError("Model failed to load")

        import time

        start = time.perf_counter()
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            _get_thread_pool(),
            self._encode_single,
            text,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        from . import metrics

        metrics.emit_histogram("memory_embedding_latency_ms", duration_ms)
        return embedding.tolist()

    def _encode_single(self, text: str) -> Any:
        """Synchronous encoding for a single text (runs in thread pool)."""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model.encode(text, convert_to_numpy=True)

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        More efficient than calling generate() multiple times as it
        batches the encoding operation.

        Args:
            texts: List of text content to embed.

        Returns:
            List of embedding vectors (list of floats each).

        Raises:
            ImportError: If sentence-transformers is not installed.
            RuntimeError: If model fails to load.
        """
        if not texts:
            return []

        self._load_model()
        if self._model is None:
            raise RuntimeError("Model failed to load")

        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            _get_thread_pool(),
            self._encode_batch,
            texts,
        )
        return [e.tolist() for e in embeddings]

    def _encode_batch(self, texts: list[str]) -> Any:
        """Synchronous batch encoding (runs in thread pool)."""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    @cached_property
    def model_name(self) -> str:
        """Return the model name or path being used."""
        return self._model_path or self._model_name

    async def preload(self) -> bool:
        """Preload the embedding model at startup.

        Loads the model in a background thread to avoid blocking the event loop.
        Should be called during service lifespan startup.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._model is not None:
            return True

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(_get_thread_pool(), self._load_model)
            logger.info(
                "Embedding model preloaded: %s (dim=%d)",
                self.model_name,
                self._dimension,
            )
            return True
        except Exception as e:
            logger.error("Embedding model preload failed: %s", e)
            return False

    def status(self) -> dict[str, Any]:
        """Return model status for health checks.

        Returns:
            Dict with model_name, loaded, dimension, device.
        """
        return {
            "model_name": self.model_name,
            "loaded": self.is_loaded(),
            "dimension": self._dimension,
            "device": self._device or "auto",
        }

    def is_loaded(self) -> bool:
        """Check if the model has been loaded."""
        return self._model is not None
