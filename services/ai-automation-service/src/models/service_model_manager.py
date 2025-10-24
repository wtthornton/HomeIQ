"""
Service-Based Model Manager
Uses containerized AI services instead of local models
Phase 1: Containerized AI Models
"""

import logging
import httpx
import os
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

class ServiceModelManager:
    """
    Manages AI models through containerized services
    Replaces local model loading with service calls
    """
    
    def __init__(self):
        # Service URLs from environment
        self.openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        self.ml_url = os.getenv("ML_SERVICE_URL", "http://ml-service:8020")
        self.ner_url = os.getenv("NER_SERVICE_URL", "http://ner-service:8019")
        self.openai_url = os.getenv("OPENAI_SERVICE_URL", "http://openai-service:8020")
        self.ai_core_url = os.getenv("AI_CORE_SERVICE_URL", "http://ai-core-service:8018")
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Service health status
        self.service_health = {
            "openvino": False,
            "ml": False,
            "ner": False,
            "openai": False,
            "ai_core": False
        }
        
        logger.info("ServiceModelManager initialized with containerized services")
    
    async def initialize(self):
        """Initialize service manager and check service health"""
        logger.info("🔄 Initializing service-based model manager...")
        await self._check_all_services()
        logger.info("✅ Service-based model manager initialized")
    
    async def _check_all_services(self):
        """Check health of all services"""
        services = [
            ("openvino", self.openvino_url),
            ("ml", self.ml_url),
            ("ner", self.ner_url),
            ("openai", self.openai_url),
            ("ai_core", self.ai_core_url)
        ]
        
        for service_name, url in services:
            try:
                response = await self.client.get(f"{url}/health", timeout=5.0)
                if response.status_code == 200:
                    self.service_health[service_name] = True
                    logger.info(f"✅ {service_name} service is healthy")
                else:
                    self.service_health[service_name] = False
                    logger.warning(f"⚠️ {service_name} service health check failed: {response.status_code}")
            except Exception as e:
                self.service_health[service_name] = False
                logger.warning(f"❌ {service_name} service is unavailable: {e}")
    
    async def generate_embeddings(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Generate embeddings using OpenVINO service
        Returns: (N, 384) numpy array
        """
        if not self.service_health["openvino"]:
            raise RuntimeError("OpenVINO service not available")
        
        try:
            response = await self.client.post(
                f"{self.openvino_url}/embeddings",
                json={
                    "texts": texts,
                    "normalize": normalize
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return np.array(data["embeddings"])
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def rerank(self, query: str, candidates: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Re-rank candidates using OpenVINO service
        """
        if not self.service_health["openvino"]:
            raise RuntimeError("OpenVINO service not available")
        
        try:
            response = await self.client.post(
                f"{self.openvino_url}/rerank",
                json={
                    "query": query,
                    "candidates": candidates,
                    "top_k": top_k
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data["ranked_candidates"]
            
        except Exception as e:
            logger.error(f"Error re-ranking candidates: {e}")
            raise
    
    async def classify_pattern(self, pattern_description: str) -> Dict[str, str]:
        """
        Classify pattern using OpenVINO service
        """
        if not self.service_health["openvino"]:
            raise RuntimeError("OpenVINO service not available")
        
        try:
            response = await self.client.post(
                f"{self.openvino_url}/classify",
                json={
                    "pattern_description": pattern_description
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                "category": data["category"],
                "priority": data["priority"]
            }
            
        except Exception as e:
            logger.error(f"Error classifying pattern: {e}")
            raise
    
    async def cluster_data(self, data: List[List[float]], algorithm: str = "kmeans", **kwargs) -> Dict[str, Any]:
        """
        Cluster data using ML service
        """
        if not self.service_health["ml"]:
            raise RuntimeError("ML service not available")
        
        try:
            response = await self.client.post(
                f"{self.ml_url}/cluster",
                json={
                    "data": data,
                    "algorithm": algorithm,
                    **kwargs
                }
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error clustering data: {e}")
            raise
    
    async def detect_anomalies(self, data: List[List[float]], contamination: float = 0.1) -> Dict[str, Any]:
        """
        Detect anomalies using ML service
        """
        if not self.service_health["ml"]:
            raise RuntimeError("ML service not available")
        
        try:
            response = await self.client.post(
                f"{self.ml_url}/anomaly",
                json={
                    "data": data,
                    "contamination": contamination
                }
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            raise
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities using NER service
        """
        if not self.service_health["ner"]:
            raise RuntimeError("NER service not available")
        
        try:
            response = await self.client.post(
                f"{self.ner_url}/extract",
                json={
                    "text": text
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data["entities"]
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            raise
    
    async def generate_with_openai(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> str:
        """
        Generate text using OpenAI service
        """
        if not self.service_health["openai"]:
            raise RuntimeError("OpenAI service not available")
        
        try:
            response = await self.client.post(
                f"{self.openai_url}/chat/completions",
                json={
                    "prompt": prompt,
                    "model": model,
                    **kwargs
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data["response"]
            
        except Exception as e:
            logger.error(f"Error generating with OpenAI: {e}")
            raise
    
    async def analyze_data(self, data: List[Dict[str, Any]], analysis_type: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis using AI Core service
        """
        if not self.service_health["ai_core"]:
            raise RuntimeError("AI Core service not available")
        
        try:
            response = await self.client.post(
                f"{self.ai_core_url}/analyze",
                json={
                    "data": data,
                    "analysis_type": analysis_type,
                    "options": options or {}
                }
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available services"""
        return {
            "service_based": True,
            "services": {
                "openvino": {
                    "url": self.openvino_url,
                    "healthy": self.service_health["openvino"],
                    "models": ["all-MiniLM-L6-v2", "bge-reranker-base", "flan-t5-small"]
                },
                "ml": {
                    "url": self.ml_url,
                    "healthy": self.service_health["ml"],
                    "algorithms": ["kmeans", "dbscan", "isolation_forest"]
                },
                "ner": {
                    "url": self.ner_url,
                    "healthy": self.service_health["ner"],
                    "models": ["dslim/bert-base-NER", "spaCy"]
                },
                "openai": {
                    "url": self.openai_url,
                    "healthy": self.service_health["openai"],
                    "models": ["gpt-4o-mini"]
                },
                "ai_core": {
                    "url": self.ai_core_url,
                    "healthy": self.service_health["ai_core"],
                    "purpose": "orchestrator"
                }
            }
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        logger.info("ServiceModelManager cleaned up")
