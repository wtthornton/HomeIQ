"""
OpenVINO Model Manager
Manages OpenVINO INT8 models: embeddings, re-ranker, classifier

Models:
- BAAI/bge-large-en-v1.5 (1024-dim) - Embeddings [Epic 47]
- bge-reranker-base - Re-ranking
- flan-t5-small - Classification

Total: ~485MB, 230ms/pattern, 100% local
"""

import asyncio
import functools
import gc
import logging
import os
import shutil
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, TypeVar

import numpy as np

T = TypeVar("T")

MODEL_LOAD_TIMEOUT_SECONDS = float(os.getenv("OPENVINO_MODEL_LOAD_TIMEOUT", "180"))
INFERENCE_TIMEOUT_SECONDS = float(os.getenv("OPENVINO_INFERENCE_TIMEOUT", "30"))
CLEAN_CACHE_ON_SHUTDOWN = os.getenv("OPENVINO_CLEAN_CACHE_ON_SHUTDOWN", "true").lower() not in {"false", "0", "no"}

# HIGH-2: Max concurrent inference tasks to prevent OOM under load
MAX_CONCURRENT_INFERENCES = int(os.getenv("OPENVINO_MAX_CONCURRENT", "3"))

# Epic 47: BGE-M3 Embedding Model (Alpha - no backward compatibility)
# Using BAAI/bge-large-en-v1.5 (1024-dim) as BGE-M3-base requires authentication
# This model is publicly available and provides 1024-dim embeddings
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"  # 1024-dim, publicly available
EMBEDDING_MODEL_DIM = 1024

logger = logging.getLogger(__name__)


class OpenVINOManager:
    """
    Manages all OpenVINO models for pattern detection.
    Lazy-loads models on first use.
    """

    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Epic 47: BGE-M3 Embedding Model (Alpha)
        self.embedding_model_name = EMBEDDING_MODEL_NAME
        self.embedding_model_dim = EMBEDDING_MODEL_DIM

        # Model instances (lazy loaded)
        self._embed_model = None
        self._embed_tokenizer = None
        self._reranker_model = None
        self._reranker_tokenizer = None
        self._classifier_model = None
        self._classifier_tokenizer = None

        # MED-2: Create asyncio locks eagerly (safe in Python 3.10+)
        self._embed_lock = asyncio.Lock()
        self._reranker_lock = asyncio.Lock()
        self._classifier_lock = asyncio.Lock()

        # HIGH-2: Concurrency semaphore for inference (lazy-created per event loop)
        self._inference_semaphore: asyncio.Semaphore | None = None

        self.model_load_timeout = MODEL_LOAD_TIMEOUT_SECONDS
        self.inference_timeout = INFERENCE_TIMEOUT_SECONDS
        self.clear_cache_on_cleanup = CLEAN_CACHE_ON_SHUTDOWN

        # HIGH-4: Make use_openvino configurable via environment variable
        self.use_openvino = os.getenv("OPENVINO_USE_OPENVINO", "false").lower() in {"1", "true", "yes"}
        self._initialized = True  # Ready for lazy loading immediately
        self._startup_strategy = "lazy"

        logger.info(
            "OpenVINOManager initialized (BGE-large-en-v1.5, %d-dim, models will load on first use)",
            self.embedding_model_dim,
        )

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Lazily create the inference semaphore (must be created in event loop context)."""
        if self._inference_semaphore is None:
            self._inference_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INFERENCES)
        return self._inference_semaphore

    async def initialize(self):
        """Initialize the model manager by pre-loading all models.

        ENH-5: Graceful degradation -- if one model fails, the others are still
        attempted so the service can serve partial functionality.
        """
        logger.info("[INIT] Pre-loading OpenVINO models...")
        errors: list[str] = []

        # Load embedding model
        try:
            await self._load_embedding_model()
        except Exception:
            logger.exception("[FAIL] Failed to load embedding model during initialization")
            errors.append("embedding")

        # Load reranker model
        try:
            await self._load_reranker_model()
        except Exception:
            logger.exception("[FAIL] Failed to load reranker model during initialization")
            errors.append("reranker")

        # Load classifier model
        try:
            await self._load_classifier_model()
        except Exception:
            logger.exception("[FAIL] Failed to load classifier model during initialization")
            errors.append("classifier")

        self._initialized = True
        self._startup_strategy = "preloaded"

        if errors:
            logger.warning(
                "[WARN] Some models failed to load during initialization: %s",
                ", ".join(errors),
            )
        else:
            logger.info("[OK] All OpenVINO models loaded successfully")

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("[CLEANUP] Cleaning up OpenVINO models...")

        # Unload models to free memory
        self._embed_model = None
        self._embed_tokenizer = None
        self._reranker_model = None
        self._reranker_tokenizer = None
        self._classifier_model = None
        self._classifier_tokenizer = None

        self._initialized = False
        self._startup_strategy = "lazy"

        self._force_memory_cleanup()
        self._purge_model_cache()

        logger.info("[OK] OpenVINO models cleaned up")

    def is_ready(self) -> bool:
        """Check if service is ready to accept requests (lazy or preloaded)."""
        return self._initialized

    async def _load_embedding_model(self):
        """Load embedding model (lazy load with double-checked locking)."""
        if self._embed_model is not None:
            return

        async with self._embed_lock:
            if self._embed_model is not None:
                return

            logger.info("Loading embedding model: %s...", self.embedding_model_name)

            try:
                if self.use_openvino:
                    logger.debug("Attempting to load OpenVINO BGE model")

                    def _load_openvino():
                        from optimum.intel import OVModelForFeatureExtraction  # type: ignore
                        from transformers import AutoTokenizer  # type: ignore

                        # Check for HuggingFace token from environment
                        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

                        # Check if quantized model exists locally
                        model_path = self.models_dir / "bge-m3" / "bge-m3-base-int8"
                        if model_path.exists() and (model_path / "openvino_model.xml").exists():
                            logger.info("Loading quantized BGE model from %s", model_path)
                            model = OVModelForFeatureExtraction.from_pretrained(
                                str(model_path),
                                compile=True,
                            )
                            tokenizer = AutoTokenizer.from_pretrained(
                                self.embedding_model_name,
                                cache_dir=str(self.models_dir),
                                token=hf_token,
                            )
                        else:
                            # Download and quantize on-the-fly (fallback)
                            logger.info("Downloading and quantizing %s...", self.embedding_model_name)
                            model = OVModelForFeatureExtraction.from_pretrained(
                                self.embedding_model_name,
                                export=True,
                                compile=True,
                                cache_dir=str(self.models_dir),
                                token=hf_token,
                            )
                            tokenizer = AutoTokenizer.from_pretrained(
                                self.embedding_model_name,
                                cache_dir=str(self.models_dir),
                                token=hf_token,
                            )
                        return model, tokenizer

                    self._embed_model, self._embed_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout,
                    )
                    logger.info(
                        "[OK] Loaded OpenVINO optimized embedding model (%d-dim)",
                        self.embedding_model_dim,
                    )
                else:
                    raise ImportError("OpenVINO not available or disabled")

            except ImportError:
                logger.warning("OpenVINO not available, using standard embedding model")
                self.use_openvino = False

                def _load_standard():
                    from sentence_transformers import SentenceTransformer  # type: ignore
                    return SentenceTransformer(
                        self.embedding_model_name,
                        cache_folder=str(self.models_dir),
                    )

                self._embed_model = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout,
                )
                self._embed_tokenizer = None
                logger.info(
                    "[OK] Loaded standard embedding model (%d-dim)",
                    self.embedding_model_dim,
                )
            except Exception as exc:
                logger.exception("Failed to load embedding model")
                raise RuntimeError("Failed to load embedding model") from exc

    async def _load_reranker_model(self):
        """Load re-ranker model (lazy load with double-checked locking)."""
        if self._reranker_model is not None:
            return

        async with self._reranker_lock:
            if self._reranker_model is not None:
                return

            logger.info("Loading re-ranker model: bge-reranker-base...")

            try:
                if self.use_openvino:
                    logger.debug("Attempting to load OpenVINO re-ranker")

                    def _load_openvino():
                        from optimum.intel import OVModelForSequenceClassification  # type: ignore
                        from transformers import AutoTokenizer  # type: ignore
                        model = OVModelForSequenceClassification.from_pretrained(
                            "OpenVINO/bge-reranker-base-int8-ov",
                            cache_dir=str(self.models_dir),
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            "OpenVINO/bge-reranker-base-int8-ov",
                            cache_dir=str(self.models_dir),
                        )
                        return model, tokenizer

                    self._reranker_model, self._reranker_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout,
                    )
                    logger.info("[OK] Loaded OpenVINO re-ranker (280MB INT8)")
                else:
                    raise ImportError("OpenVINO not available or disabled")

            except ImportError:
                logger.warning("OpenVINO re-ranker not available, using standard model")

                def _load_standard():
                    from transformers import (  # type: ignore
                        AutoModelForSequenceClassification,
                        AutoTokenizer,
                    )
                    tokenizer = AutoTokenizer.from_pretrained(
                        "BAAI/bge-reranker-base",
                        cache_dir=str(self.models_dir),
                    )
                    model = AutoModelForSequenceClassification.from_pretrained(
                        "BAAI/bge-reranker-base",
                        cache_dir=str(self.models_dir),
                    )
                    return model, tokenizer

                self._reranker_model, self._reranker_tokenizer = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout,
                )
                logger.info("[OK] Loaded standard re-ranker (1.1GB)")
            except Exception as exc:
                logger.exception("Failed to load reranker model")
                raise RuntimeError("Failed to load reranker model") from exc

    async def _load_classifier_model(self):
        """Load classifier model (lazy load with double-checked locking)."""
        if self._classifier_model is not None:
            return

        async with self._classifier_lock:
            if self._classifier_model is not None:
                return

            logger.info("Loading classifier model: flan-t5-small...")

            try:
                if self.use_openvino:
                    logger.debug("Attempting to load OpenVINO classifier")

                    def _load_openvino():
                        from optimum.intel import OVModelForSeq2SeqLM  # type: ignore
                        from transformers import AutoTokenizer  # type: ignore
                        model = OVModelForSeq2SeqLM.from_pretrained(
                            "google/flan-t5-small",
                            export=True,
                            cache_dir=str(self.models_dir),
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            "google/flan-t5-small",
                            cache_dir=str(self.models_dir),
                        )
                        return model, tokenizer

                    self._classifier_model, self._classifier_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout,
                    )
                    logger.info("[OK] Loaded OpenVINO classifier (80MB INT8)")
                else:
                    raise ImportError("OpenVINO not available or disabled")

            except ImportError:
                logger.warning("OpenVINO not available, using standard classifier model")

                def _load_standard():
                    from transformers import T5ForConditionalGeneration, T5Tokenizer  # type: ignore
                    tokenizer = T5Tokenizer.from_pretrained(
                        "google/flan-t5-small",
                        cache_dir=str(self.models_dir),
                    )
                    model = T5ForConditionalGeneration.from_pretrained(
                        "google/flan-t5-small",
                        cache_dir=str(self.models_dir),
                    )
                    return model, tokenizer

                self._classifier_model, self._classifier_tokenizer = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout,
                )
                logger.info("[OK] Loaded standard classifier (300MB)")
            except Exception as exc:
                logger.exception("Failed to load classifier model")
                raise RuntimeError("Failed to load classifier model") from exc

    async def generate_embeddings(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for texts.
        Returns: (N, 1024) numpy array (BGE-large-en-v1.5 embeddings).
        """
        if not texts:
            raise ValueError("At least one text is required for embedding generation")

        await self._load_embedding_model()

        if self.use_openvino and self._embed_tokenizer is not None:
            # OpenVINO path
            def _encode_openvino() -> np.ndarray:
                inputs = self._embed_tokenizer(
                    texts,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=256,
                )
                outputs = None
                try:
                    outputs = self._embed_model(**inputs)
                    embeddings = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy()
                    return embeddings
                finally:
                    del inputs
                    if outputs is not None:
                        del outputs
                    gc.collect()

            embeddings = await self._run_blocking(_encode_openvino)
        else:
            # Standard sentence-transformers path
            embeddings = await self._run_blocking(
                self._embed_model.encode,
                texts,
                convert_to_numpy=True,
            )
            gc.collect()

        # Normalize for dot-product scoring
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.where(norms == 0, 1, norms)
            embeddings = embeddings / norms

        return embeddings

    async def rerank(self, query: str, candidates: list[dict], top_k: int = 10) -> list[dict]:
        """
        Re-rank candidates using bge-reranker.

        HIGH-5: Batched tokenization and forward passes for efficiency.

        Args:
            query: Query text (pattern description)
            candidates: List of candidate patterns (must have 'description' field)
            top_k: Number of top results to return

        Returns:
            Top K re-ranked candidates
        """
        if not candidates:
            return []

        await self._load_reranker_model()
        top_k = min(top_k, len(candidates))

        def _rerank() -> list[dict]:
            # HIGH-5: Batch all candidates at once instead of one-by-one
            texts = [candidate.get("description", str(candidate)) for candidate in candidates]
            pairs = ["%s [SEP] %s" % (query, text) for text in texts]

            # Batch tokenize all pairs at once
            inputs = self._reranker_tokenizer(
                pairs, return_tensors="pt", truncation=True,
                max_length=512, padding=True,
            )
            try:
                outputs = self._reranker_model(**inputs)
                scores_tensor = outputs.logits[:, 0]
                scores = scores_tensor.detach().cpu().tolist()
            finally:
                del inputs
                if "outputs" in dir() and outputs is not None:
                    del outputs
                gc.collect()

            scored = list(zip(candidates, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [candidate for candidate, _ in scored[:top_k]]

        return await self._run_blocking(_rerank)

    async def classify_pattern(self, pattern_description: str) -> dict[str, str]:
        """
        Classify pattern category and priority using flan-t5-small.

        MED-5: gc.collect() called once at end instead of per-generate call.

        Args:
            pattern_description: Natural language pattern description

        Returns:
            {'category': str, 'priority': str}
        """
        if not pattern_description or not pattern_description.strip():
            raise ValueError("Pattern description is required for classification")

        await self._load_classifier_model()

        category_prompt = (
            "Classify this smart home pattern into ONE category: "
            "energy, comfort, security, or convenience.\n\n"
            "Pattern: %s\n\n"
            "Respond with only the category name (one word).\n\n"
            "Category:" % pattern_description
        )

        def _classify() -> dict[str, str]:
            def _generate(prompt: str) -> str:
                """Run a single generate call (no gc.collect per call -- MED-5)."""
                local_inputs = self._classifier_tokenizer(
                    prompt, return_tensors="pt", max_length=512, truncation=True,
                )
                local_outputs = None
                try:
                    local_outputs = self._classifier_model.generate(
                        **local_inputs, max_new_tokens=5,
                    )
                    return self._classifier_tokenizer.decode(
                        local_outputs[0], skip_special_tokens=True,
                    )
                finally:
                    del local_inputs
                    if local_outputs is not None:
                        del local_outputs

            category_raw = _generate(category_prompt)
            category = self._parse_category(category_raw)

            priority_prompt = (
                "Rate priority (high, medium, or low) for this smart home pattern.\n\n"
                "Pattern: %s\n"
                "Category: %s\n\n"
                "Respond with only the priority level (one word).\n\n"
                "Priority:" % (pattern_description, category)
            )

            priority_raw = _generate(priority_prompt)
            priority = self._parse_priority(priority_raw)

            # MED-5: Single gc.collect after both generations
            gc.collect()

            return {
                "category": category,
                "priority": priority,
            }

        return await self._run_blocking(_classify)

    async def _run_blocking(self, func: Callable[..., T], *args, timeout: float | None = None, **kwargs) -> T:
        """Run blocking model operations in a thread pool with a timeout.

        HIGH-2: Uses a semaphore to limit concurrent inferences and prevent OOM.
        """
        semaphore = self._get_semaphore()
        async with semaphore:
            loop = asyncio.get_running_loop()
            bound = functools.partial(func, *args, **kwargs)
            return await asyncio.wait_for(
                loop.run_in_executor(None, bound),
                timeout or self.inference_timeout,
            )

    def _force_memory_cleanup(self) -> None:
        """Force Python and torch garbage collection to free tensor memory."""
        gc.collect()
        with suppress(ImportError, Exception):
            import torch  # type: ignore
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def _purge_model_cache(self) -> None:
        """Optionally clear cached model files to reclaim disk space."""
        if not self.clear_cache_on_cleanup or not self.models_dir.exists():
            return

        for child in list(self.models_dir.iterdir()):
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                else:
                    shutil.rmtree(child)
            except Exception as exc:
                logger.warning("Unable to remove cached model %s: %s", child, exc)

        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _parse_category(self, text: str) -> str:
        """Parse flan-t5 output to valid category with fallback."""
        text = text.strip().lower()
        valid = ["energy", "comfort", "security", "convenience"]

        # Direct match
        if text in valid:
            return text

        # Keyword matching
        for category in valid:
            if category in text:
                return category

        # Rule-based fallback
        if any(word in text for word in ["power", "electricity", "consumption"]):
            return "energy"
        if any(word in text for word in ["temperature", "thermostat", "climate", "heat", "cool", "lighting"]):
            return "comfort"
        if any(word in text for word in ["lock", "door", "alarm", "camera", "monitor", "safety"]):
            return "security"

        return "convenience"  # Default fallback

    def _parse_priority(self, text: str) -> str:
        """Parse flan-t5 output to valid priority with fallback."""
        text = text.strip().lower()
        valid = ["high", "medium", "low"]

        # Direct match
        if text in valid:
            return text

        # Keyword matching
        for priority in valid:
            if priority in text:
                return priority

        return "medium"  # Default fallback

    def get_model_status(self) -> dict[str, Any]:
        """Return a detailed snapshot of model readiness."""
        return {
            "embedding_model": self.embedding_model_name,
            "embedding_dimension": self.embedding_model_dim,
            "embedding_loaded": self._embed_model is not None,
            "reranker_model": "bge-reranker-base",
            "reranker_loaded": self._reranker_model is not None,
            "classifier_model": "flan-t5-small",
            "classifier_loaded": self._classifier_model is not None,
            "startup_strategy": self._startup_strategy,
            "ready_for_requests": self.is_ready(),
            "openvino_enabled": self.use_openvino,
            "inference_timeout_seconds": self.inference_timeout,
            "model_cache_dir": str(self.models_dir),
        }
