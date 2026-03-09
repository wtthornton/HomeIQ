"""HomeIQ Memory Brain library.

Semantic memory store with hybrid search, confidence decay, and LLM prompt injection.
"""

from homeiq_memory.client import MemoryClient
from homeiq_memory.domains import (
    DOMAIN_TAXONOMY,
    VALID_DOMAINS,
    classify_domain,
    classify_domains,
)
from homeiq_memory.consolidator import (
    ConsolidationAction,
    ConsolidationResult,
    MemoryConsolidator,
)
from homeiq_memory.decay import (
    ACCESS_CONFIDENCE_BUMP,
    HALF_LIVES,
    MAX_CONFIDENCE,
    contradict,
    effective_confidence,
    record_access,
    reinforce,
    should_archive,
)
from homeiq_memory.embeddings import EmbeddingGenerator
from homeiq_memory.health import HealthStatus, MemoryHealthCheck
from homeiq_memory.injector import MemoryInjector
from homeiq_memory.models import (
    Base,
    Memory,
    MemoryArchive,
    MemoryType,
    SourceChannel,
)
from homeiq_memory import metrics as memory_metrics
from homeiq_memory.search import MemorySearch, MemorySearchResult

__all__ = [
    "ACCESS_CONFIDENCE_BUMP",
    "Base",
    "ConsolidationAction",
    "ConsolidationResult",
    "DOMAIN_TAXONOMY",
    "EmbeddingGenerator",
    "HALF_LIVES",
    "HealthStatus",
    "MAX_CONFIDENCE",
    "Memory",
    "MemoryArchive",
    "MemoryClient",
    "MemoryConsolidator",
    "MemoryHealthCheck",
    "MemoryInjector",
    "MemorySearch",
    "memory_metrics",
    "MemorySearchResult",
    "MemoryType",
    "SourceChannel",
    "VALID_DOMAINS",
    "classify_domain",
    "classify_domains",
    "contradict",
    "effective_confidence",
    "record_access",
    "reinforce",
    "should_archive",
]
