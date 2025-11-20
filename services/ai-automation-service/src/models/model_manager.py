"""
Model Manager for Phase 1 Containerized Stack
Uses containerized AI services instead of local models

Services:
- OpenVINO Service - all-MiniLM-L6-v2, bge-reranker-base, flan-t5-small
- ML Service - scikit-learn algorithms
- NER Service - dslim/bert-base-NER
- OpenAI Service - gpt-4o-mini
- AI Core Service - orchestrator

Total: Distributed across 5 containers, better resource management
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .service_model_manager import ServiceModelManager

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Manages AI models through containerized services
    Delegates to ServiceModelManager for actual operations
    """

    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Use service-based model manager
        self.service_manager = ServiceModelManager()
        self._initialized = False

        logger.info("ModelManager initialized with containerized services")

    async def initialize(self):
        """Initialize the model manager"""
        if not self._initialized:
            await self.service_manager.initialize()
            self._initialized = True
            logger.info("✅ ModelManager initialized with containerized services")

    async def get_embedding_model(self):
        """Get embedding model (service-based)"""
        await self.initialize()
        return self.service_manager, None  # No local tokenizer needed

    async def get_reranker_model(self):
        """Get re-ranker model (service-based)"""
        await self.initialize()
        return self.service_manager, None  # No local tokenizer needed

    async def get_classifier_model(self):
        """Get classifier model (service-based)"""
        await self.initialize()
        return self.service_manager, None  # No local tokenizer needed

    async def generate_embeddings(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for texts using OpenVINO service
        Returns: (N, 384) numpy array
        """
        await self.initialize()
        return await self.service_manager.generate_embeddings(texts, normalize=True)

    async def rerank(self, query: str, candidates: list[dict], top_k: int = 10) -> list[dict]:
        """
        Re-rank candidates using OpenVINO service
        """
        await self.initialize()
        return await self.service_manager.rerank(query, candidates, top_k)

    async def classify_pattern(self, pattern_description: str) -> dict[str, str]:
        """
        Classify pattern using OpenVINO service
        """
        await self.initialize()
        return await self.service_manager.classify_pattern(pattern_description)

    async def cluster_data(self, data: list[list[float]], algorithm: str = "kmeans", **kwargs) -> dict[str, Any]:
        """
        Cluster data using ML service
        """
        await self.initialize()
        return await self.service_manager.cluster_data(data, algorithm, **kwargs)

    async def detect_anomalies(self, data: list[list[float]], contamination: float = 0.1) -> dict[str, Any]:
        """
        Detect anomalies using ML service
        """
        await self.initialize()
        return await self.service_manager.detect_anomalies(data, contamination)

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities using NER service
        """
        await self.initialize()
        return await self.service_manager.extract_entities(text)

    async def generate_with_openai(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> str:
        """
        Generate text using OpenAI service
        """
        await self.initialize()
        return await self.service_manager.generate_with_openai(prompt, model, **kwargs)

    async def analyze_data(self, data: list[dict[str, Any]], analysis_type: str, options: dict[str, Any] = None) -> dict[str, Any]:
        """
        Perform comprehensive analysis using AI Core service
        """
        await self.initialize()
        return await self.service_manager.analyze_data(data, analysis_type, options)

    def get_model_info(self) -> dict[str, Any]:
        """Get information about available services"""
        return self.service_manager.get_model_info()

    async def cleanup(self):
        """Cleanup resources"""
        await self.service_manager.cleanup()
        logger.info("ModelManager cleaned up")


# Global instance (singleton pattern)
_model_manager: ModelManager | None = None

def get_model_manager() -> ModelManager:
    """Get global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
