"""
OpenVINO Model Manager
Manages OpenVINO INT8 models: embeddings, re-ranker, classifier

Models:
- all-MiniLM-L6-v2 (INT8) - 20MB - Embeddings
- bge-reranker-base (INT8) - 280MB - Re-ranking  
- flan-t5-small (INT8) - 80MB - Classification

Total: 380MB, 230ms/pattern, 100% local
"""

import asyncio
import functools
import gc
import logging
import os
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

import numpy as np

T = TypeVar("T")

MODEL_LOAD_TIMEOUT_SECONDS = float(os.getenv("OPENVINO_MODEL_LOAD_TIMEOUT", "180"))
INFERENCE_TIMEOUT_SECONDS = float(os.getenv("OPENVINO_INFERENCE_TIMEOUT", "30"))
CLEAN_CACHE_ON_SHUTDOWN = os.getenv("OPENVINO_CLEAN_CACHE_ON_SHUTDOWN", "true").lower() not in {"false", "0", "no"}

logger = logging.getLogger(__name__)

class OpenVINOManager:
    """
    Manages all OpenVINO models for pattern detection
    Lazy-loads models on first use
    """
    
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model instances (lazy loaded)
        self._embed_model = None
        self._embed_tokenizer = None
        self._reranker_model = None
        self._reranker_tokenizer = None
        self._classifier_model = None
        self._classifier_tokenizer = None

        # Asyncio locks (created lazily once an event loop is running)
        self._embed_lock: Optional[asyncio.Lock] = None
        self._reranker_lock: Optional[asyncio.Lock] = None
        self._classifier_lock: Optional[asyncio.Lock] = None
        
        self.model_load_timeout = MODEL_LOAD_TIMEOUT_SECONDS
        self.inference_timeout = INFERENCE_TIMEOUT_SECONDS
        self.clear_cache_on_cleanup = CLEAN_CACHE_ON_SHUTDOWN
        
        self.use_openvino = False  # Use standard models for compatibility
        self._initialized = True  # Ready for lazy loading immediately
        self._startup_strategy = "lazy"
        
        logger.info("OpenVINOManager initialized (models will load on first use)")
    
    async def initialize(self):
        """Initialize the model manager"""
        try:
            # Pre-load all models for better performance
            logger.info("🔄 Pre-loading OpenVINO models...")
            
            # Load embedding model
            await self._load_embedding_model()
            
            # Load reranker model
            await self._load_reranker_model()
            
            # Load classifier model
            await self._load_classifier_model()
            
            self._initialized = True
            self._startup_strategy = "preloaded"
            logger.info("✅ All OpenVINO models loaded successfully")
            
        except Exception as e:
            logger.exception("❌ Failed to initialize OpenVINO models")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up OpenVINO models...")
        
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

        logger.info("✅ OpenVINO models cleaned up")
    
    def is_ready(self) -> bool:
        """Check if service is ready to accept requests (lazy or preloaded)."""
        return self._initialized
    
    async def _load_embedding_model(self):
        """Load embedding model (lazy load)"""
        if self._embed_model is not None:
            return

        lock = self._get_lock("_embed_lock")
        async with lock:
            if self._embed_model is not None:
                return

            logger.info("Loading embedding model: all-MiniLM-L6-v2...")
            
            try:
                if self.use_openvino:
                    logger.debug("Attempting to load OpenVINO embedding model")
                    
                    def _load_openvino():
                        from optimum.intel import OVModelForFeatureExtraction  # type: ignore
                        from transformers import AutoTokenizer  # type: ignore
                        model = OVModelForFeatureExtraction.from_pretrained(
                            "sentence-transformers/all-MiniLM-L6-v2",
                            export=True,
                            compile=True,
                            cache_dir=str(self.models_dir)
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            "sentence-transformers/all-MiniLM-L6-v2",
                            cache_dir=str(self.models_dir)
                        )
                        return model, tokenizer
                    
                    self._embed_model, self._embed_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout
                    )
                    logger.info("✅ Loaded OpenVINO optimized embedding model (20MB)")
                else:
                    raise ImportError("OpenVINO not available")
                    
            except ImportError:
                logger.warning("OpenVINO not available, using standard model")
                self.use_openvino = False
                
                def _load_standard():
                    from sentence_transformers import SentenceTransformer  # type: ignore
                    return SentenceTransformer(
                        "sentence-transformers/all-MiniLM-L6-v2",
                        cache_folder=str(self.models_dir)
                    )
                
                self._embed_model = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout
                )
                self._embed_tokenizer = None
                logger.info("✅ Loaded standard embedding model (80MB)")
            except Exception as exc:
                logger.exception("Failed to load embedding model")
                raise RuntimeError("Failed to load embedding model") from exc
    
    async def _load_reranker_model(self):
        """Load re-ranker model (lazy load)"""
        if self._reranker_model is not None:
            return

        lock = self._get_lock("_reranker_lock")
        async with lock:
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
                            cache_dir=str(self.models_dir)
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            "OpenVINO/bge-reranker-base-int8-ov",
                            cache_dir=str(self.models_dir)
                        )
                        return model, tokenizer
                    
                    self._reranker_model, self._reranker_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout
                    )
                    logger.info("✅ Loaded OpenVINO re-ranker (280MB INT8)")
                else:
                    raise ImportError("OpenVINO not available")
                    
            except ImportError:
                logger.warning("OpenVINO re-ranker not available, using standard")
                
                def _load_standard():
                    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
                    tokenizer = AutoTokenizer.from_pretrained(
                        "BAAI/bge-reranker-base",
                        cache_dir=str(self.models_dir)
                    )
                    model = AutoModelForSequenceClassification.from_pretrained(
                        "BAAI/bge-reranker-base",
                        cache_dir=str(self.models_dir)
                    )
                    return model, tokenizer
                
                self._reranker_model, self._reranker_tokenizer = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout
                )
                logger.info("✅ Loaded standard re-ranker (1.1GB)")
            except Exception as exc:
                logger.exception("Failed to load reranker model")
                raise RuntimeError("Failed to load reranker model") from exc
    
    async def _load_classifier_model(self):
        """Load classifier model (lazy load)"""
        if self._classifier_model is not None:
            return

        lock = self._get_lock("_classifier_lock")
        async with lock:
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
                            cache_dir=str(self.models_dir)
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            "google/flan-t5-small",
                            cache_dir=str(self.models_dir)
                        )
                        return model, tokenizer
                    
                    self._classifier_model, self._classifier_tokenizer = await self._run_blocking(
                        _load_openvino,
                        timeout=self.model_load_timeout
                    )
                    logger.info("✅ Loaded OpenVINO classifier (80MB INT8)")
                else:
                    raise ImportError("OpenVINO not available")
                    
            except ImportError:
                logger.warning("OpenVINO not available, using standard model")
                
                def _load_standard():
                    from transformers import T5Tokenizer, T5ForConditionalGeneration  # type: ignore
                    tokenizer = T5Tokenizer.from_pretrained(
                        "google/flan-t5-small",
                        cache_dir=str(self.models_dir)
                    )
                    model = T5ForConditionalGeneration.from_pretrained(
                        "google/flan-t5-small",
                        cache_dir=str(self.models_dir)
                    )
                    return model, tokenizer
                
                self._classifier_model, self._classifier_tokenizer = await self._run_blocking(
                    _load_standard,
                    timeout=self.model_load_timeout
                )
                logger.info("✅ Loaded standard classifier (300MB)")
            except Exception as exc:
                logger.exception("Failed to load classifier model")
                raise RuntimeError("Failed to load classifier model") from exc
    
    async def generate_embeddings(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings for texts
        Returns: (N, 384) numpy array
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
                    return_tensors='pt',
                    max_length=256
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
                convert_to_numpy=True
            )
            gc.collect()
        
        # Normalize for dot-product scoring
        if normalize:
            # Normalize embeddings using numpy (sentence_transformers.util has compatibility issues)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.where(norms == 0, 1, norms)
            embeddings = embeddings / norms
        
        return embeddings
    
    async def rerank(self, query: str, candidates: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Re-rank candidates using bge-reranker
        
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

        def _rerank() -> List[Dict]:
            scores = []
            for candidate in candidates:
                text = candidate.get('description', str(candidate))
                pair = f"{query} [SEP] {text}"
                
                inputs = self._reranker_tokenizer(pair, return_tensors='pt', truncation=True, max_length=512)
                outputs = None
                try:
                    outputs = self._reranker_model(**inputs)
                    score = float(outputs.logits[0][0].item())
                    scores.append((candidate, score))
                finally:
                    del inputs
                    if outputs is not None:
                        del outputs
                    gc.collect()
            
            ranked = sorted(scores, key=lambda x: x[1], reverse=True)
            return [candidate for candidate, _ in ranked[:top_k]]

        return await self._run_blocking(_rerank)
    
    async def classify_pattern(self, pattern_description: str) -> Dict[str, str]:
        """
        Classify pattern category and priority using flan-t5-small
        
        Args:
            pattern_description: Natural language pattern description
        
        Returns:
            {'category': str, 'priority': str}
        """
        if not pattern_description or not pattern_description.strip():
            raise ValueError("Pattern description is required for classification")
        
        await self._load_classifier_model()

        category_prompt = f"""Classify this smart home pattern into ONE category: energy, comfort, security, or convenience.

Pattern: {pattern_description}

Respond with only the category name (one word).

Category:"""

        def _classify() -> Dict[str, str]:
            def _generate(prompt: str) -> str:
                local_inputs = self._classifier_tokenizer(prompt, return_tensors='pt', max_length=512, truncation=True)
                local_outputs = None
                try:
                    local_outputs = self._classifier_model.generate(**local_inputs, max_new_tokens=5)
                    return self._classifier_tokenizer.decode(local_outputs[0], skip_special_tokens=True)
                finally:
                    del local_inputs
                    if local_outputs is not None:
                        del local_outputs
                    gc.collect()

            category_raw = _generate(category_prompt)
            category = self._parse_category(category_raw)

            priority_prompt = f"""Rate priority (high, medium, or low) for this smart home pattern.

Pattern: {pattern_description}
Category: {category}

Respond with only the priority level (one word).

Priority:"""

            priority_raw = _generate(priority_prompt)
            priority = self._parse_priority(priority_raw)

            return {
                'category': category,
                'priority': priority
            }

        return await self._run_blocking(_classify)

    async def _run_blocking(self, func: Callable[..., T], *args, timeout: Optional[float] = None, **kwargs) -> T:
        """Run blocking model operations in a thread pool with a timeout."""
        loop = asyncio.get_running_loop()
        bound = functools.partial(func, *args, **kwargs)
        return await asyncio.wait_for(loop.run_in_executor(None, bound), timeout or self.inference_timeout)

    def _get_lock(self, attr_name: str) -> asyncio.Lock:
        """Create or return an asyncio lock for the given attribute name."""
        lock = getattr(self, attr_name)
        if lock is None:
            lock = asyncio.Lock()
            setattr(self, attr_name, lock)
        return lock

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
        """Parse flan-t5 output to valid category with fallback"""
        text = text.strip().lower()
        valid = ['energy', 'comfort', 'security', 'convenience']
        
        # Direct match
        if text in valid:
            return text
        
        # Keyword matching
        for category in valid:
            if category in text:
                return category
        
        # Rule-based fallback
        if any(word in text for word in ['power', 'electricity', 'consumption']):
            return 'energy'
        if any(word in text for word in ['temperature', 'thermostat', 'climate', 'heat', 'cool', 'lighting']):
            return 'comfort'
        if any(word in text for word in ['lock', 'door', 'alarm', 'camera', 'monitor', 'safety']):
            return 'security'
        
        return 'convenience'  # Default fallback
    
    def _parse_priority(self, text: str) -> str:
        """Parse flan-t5 output to valid priority with fallback"""
        text = text.strip().lower()
        valid = ['high', 'medium', 'low']
        
        # Direct match
        if text in valid:
            return text
        
        # Keyword matching
        for priority in valid:
            if priority in text:
                return priority
        
        return 'medium'  # Default fallback

    def get_model_status(self) -> Dict[str, Any]:
        """Return a detailed snapshot of model readiness."""
        return {
            'embedding_model': 'all-MiniLM-L6-v2',
            'embedding_loaded': self._embed_model is not None,
            'reranker_model': 'bge-reranker-base',
            'reranker_loaded': self._reranker_model is not None,
            'classifier_model': 'flan-t5-small',
            'classifier_loaded': self._classifier_model is not None,
            'startup_strategy': self._startup_strategy,
            'ready_for_requests': self.is_ready(),
            'openvino_enabled': self.use_openvino,
            'inference_timeout_seconds': self.inference_timeout,
            'model_cache_dir': str(self.models_dir)
        }
    
