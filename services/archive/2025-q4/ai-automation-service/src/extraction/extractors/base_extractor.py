"""
Base Extractor Interface (2025)

Defines the abstract base class for all context extractors.
"""

from abc import ABC, abstractmethod
from typing import Any
from ..models import AutomationContext

class BaseExtractor(ABC):
    """
    Abstract base class for extraction pipeline components.
    """
    
    def __init__(self, config: Any = None):
        self.config = config

    @abstractmethod
    async def extract(self, query: str, context: AutomationContext) -> AutomationContext:
        """
        Process the query and update the automation context.
        
        Args:
            query: The original user query.
            context: The current state of the automation context (accumulated results).
            
        Returns:
            Updated AutomationContext.
        """
        pass

