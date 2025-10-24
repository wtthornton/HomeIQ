"""
Service Manager - Orchestrates calls to containerized AI services
Implements circuit breaker patterns and fallback mechanisms
"""

import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Manages communication with containerized AI services
    Implements circuit breaker patterns and fallback mechanisms
    """
    
    def __init__(self, openvino_url: str, ml_url: str, ner_url: str, openai_url: str):
        self.openvino_url = openvino_url
        self.ml_url = ml_url
        self.ner_url = ner_url
        self.openai_url = openai_url
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Service health status
        self.service_health = {
            "openvino": False,
            "ml": False,
            "ner": False,
            "openai": False
        }
        
        logger.info(f"ServiceManager initialized with URLs: OpenVINO={openvino_url}, ML={ml_url}, NER={ner_url}, OpenAI={openai_url}")
    
    async def initialize(self):
        """Initialize service manager and check service health"""
        logger.info("🔄 Initializing service manager...")
        
        # Check all services
        await self._check_all_services()
        
        logger.info("✅ Service manager initialized")
    
    async def _check_all_services(self):
        """Check health of all services"""
        services = [
            ("openvino", self.openvino_url),
            ("ml", self.ml_url),
            ("ner", self.ner_url),
            ("openai", self.openai_url)
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
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get detailed status of all services"""
        await self._check_all_services()
        
        return {
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
            }
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _call_service(self, service_name: str, url: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a service with retry logic"""
        try:
            response = await self.client.post(f"{url}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling {service_name} service: {e}")
            raise
    
    async def analyze_data(self, data: List[Dict[str, Any]], analysis_type: str, options: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Perform comprehensive data analysis using available services"""
        results = {}
        services_used = []
        
        try:
            # Step 1: Generate embeddings using OpenVINO service
            if self.service_health["openvino"]:
                try:
                    texts = [str(item) for item in data]
                    embedding_response = await self._call_service(
                        "openvino", 
                        self.openvino_url, 
                        "/embeddings",
                        {"texts": texts, "normalize": True}
                    )
                    results["embeddings"] = embedding_response["embeddings"]
                    services_used.append("openvino")
                except Exception as e:
                    logger.warning(f"OpenVINO service failed, skipping embeddings: {e}")
            
            # Step 2: Perform clustering using ML service
            if self.service_health["ml"] and "embeddings" in results:
                try:
                    clustering_response = await self._call_service(
                        "ml",
                        self.ml_url,
                        "/cluster",
                        {
                            "data": results["embeddings"],
                            "algorithm": "kmeans",
                            "n_clusters": options.get("n_clusters", 5)
                        }
                    )
                    results["clusters"] = clustering_response["labels"]
                    results["n_clusters"] = clustering_response["n_clusters"]
                    services_used.append("ml")
                except Exception as e:
                    logger.warning(f"ML service failed, skipping clustering: {e}")
            
            # Step 3: Detect anomalies using ML service
            if self.service_health["ml"] and "embeddings" in results:
                try:
                    anomaly_response = await self._call_service(
                        "ml",
                        self.ml_url,
                        "/anomaly",
                        {
                            "data": results["embeddings"],
                            "contamination": options.get("contamination", 0.1)
                        }
                    )
                    results["anomalies"] = anomaly_response["labels"]
                    results["anomaly_scores"] = anomaly_response["scores"]
                    results["n_anomalies"] = anomaly_response["n_anomalies"]
                    services_used.append("ml")
                except Exception as e:
                    logger.warning(f"ML service failed, skipping anomaly detection: {e}")
            
            return results, services_used
            
        except Exception as e:
            logger.error(f"Error in data analysis: {e}")
            raise
    
    async def detect_patterns(self, patterns: List[Dict[str, Any]], detection_type: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Detect patterns using available services"""
        detected_patterns = []
        services_used = []
        
        try:
            # Use OpenVINO service for pattern classification
            if self.service_health["openvino"]:
                for pattern in patterns:
                    try:
                        description = pattern.get("description", str(pattern))
                        classification_response = await self._call_service(
                            "openvino",
                            self.openvino_url,
                            "/classify",
                            {"pattern_description": description}
                        )
                        
                        detected_pattern = {
                            **pattern,
                            "category": classification_response["category"],
                            "priority": classification_response["priority"],
                            "confidence": 0.8  # Default confidence
                        }
                        detected_patterns.append(detected_pattern)
                        
                    except Exception as e:
                        logger.warning(f"Failed to classify pattern {pattern}: {e}")
                        # Add pattern without classification
                        detected_patterns.append(pattern)
                
                services_used.append("openvino")
            
            return detected_patterns, services_used
            
        except Exception as e:
            logger.error(f"Error in pattern detection: {e}")
            raise
    
    async def generate_suggestions(self, context: Dict[str, Any], suggestion_type: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Generate AI suggestions using available services"""
        suggestions = []
        services_used = []
        
        try:
            # Use OpenAI service for suggestion generation
            if self.service_health["openai"]:
                try:
                    # Prepare prompt based on context and suggestion type
                    prompt = self._build_suggestion_prompt(context, suggestion_type)
                    
                    openai_response = await self._call_service(
                        "openai",
                        self.openai_url,
                        "/chat/completions",
                        {
                            "prompt": prompt,
                            "model": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 500
                        }
                    )
                    
                    # Parse response into suggestions
                    suggestions = self._parse_suggestions(openai_response["response"])
                    services_used.append("openai")
                    
                except Exception as e:
                    logger.warning(f"OpenAI service failed: {e}")
                    # Fallback to basic suggestions
                    suggestions = self._generate_fallback_suggestions(context, suggestion_type)
            
            return suggestions, services_used
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            raise
    
    def _build_suggestion_prompt(self, context: Dict[str, Any], suggestion_type: str) -> str:
        """Build prompt for suggestion generation"""
        return f"""
        Generate {suggestion_type} suggestions based on the following context:
        
        Context: {context}
        
        Please provide 3-5 specific, actionable suggestions in JSON format.
        Each suggestion should include:
        - title: Brief title
        - description: Detailed description
        - priority: high/medium/low
        - category: energy/comfort/security/convenience
        """
    
    def _parse_suggestions(self, response: str) -> List[Dict[str, Any]]:
        """Parse OpenAI response into structured suggestions"""
        # Simple parsing - in production, use more robust JSON parsing
        try:
            import json
            return json.loads(response)
        except:
            # Fallback parsing
            return [
                {
                    "title": "AI Suggestion",
                    "description": response,
                    "priority": "medium",
                    "category": "convenience"
                }
            ]
    
    def _generate_fallback_suggestions(self, context: Dict[str, Any], suggestion_type: str) -> List[Dict[str, Any]]:
        """Generate fallback suggestions when AI services are unavailable"""
        return [
            {
                "title": "Basic Suggestion",
                "description": f"Consider reviewing your {suggestion_type} configuration",
                "priority": "medium",
                "category": "convenience"
            }
        ]
