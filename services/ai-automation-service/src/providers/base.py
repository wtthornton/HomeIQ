"""
Base Provider Interface for LLM Providers
All providers must implement this interface for deterministic JSON generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """
    Base provider interface for LLM providers.
    
    All providers must implement:
    - provider_id() - unique identifier
    - model_id() - model identifier
    - generate_json() - generate schema-valid JSON
    """
    
    @abstractmethod
    def provider_id(self) -> str:
        """
        Get provider identifier (e.g., 'openai', 'anthropic', 'google').
        
        Returns:
            Provider identifier string
        """
        pass
    
    @abstractmethod
    def model_id(self) -> str:
        """
        Get model identifier (e.g., 'gpt-4o-mini', 'claude-3-sonnet').
        
        Returns:
            Model identifier string
        """
        pass
    
    @abstractmethod
    async def generate_json(
        self,
        *,
        schema: Dict[str, Any],
        prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate JSON output conforming to the provided schema.
        
        This method MUST:
        1. Use structured output (JSON mode, function calling, or structured output API)
        2. Validate output against schema before returning
        3. Raise ValueError if output doesn't conform
        4. Return only valid JSON (no free-text, no extra fields)
        
        Args:
            schema: JSON Schema definition for expected output
            prompt: User prompt/instruction
            tools: Optional list of tool definitions (for function calling)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Validated JSON dict conforming to schema
            
        Raises:
            ValueError: If output doesn't conform to schema
            RuntimeError: If provider API call fails
        """
        pass
    
    def get_metadata(self) -> Dict[str, str]:
        """
        Get provider and model metadata.
        
        Returns:
            Dict with provider_id and model_id
        """
        return {
            "provider_id": self.provider_id(),
            "model_id": self.model_id()
        }

