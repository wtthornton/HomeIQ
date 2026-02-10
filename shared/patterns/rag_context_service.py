"""
RAGContextService - Reusable Pattern A: Keyword RAG Context Injection

Epic: Reusable Pattern Framework, Story 1
Abstract base class for domain-specific RAG context services.

Pattern: Detect domain intent from user prompt via keyword matching;
load domain-specific corpus; inject into LLM prompt as context.

Usage:
    class EnergyRAGService(RAGContextService):
        name = "energy"
        keywords = {"solar", "battery", "kWh", "TOU", "peak"}
        corpus_path = Path("data/energy_patterns.md")
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class RAGContextService(ABC):
    """
    Abstract base class for keyword-triggered RAG context injection.

    Subclasses must define:
        - name: Human-readable domain name (e.g. "sports", "energy")
        - keywords: Set or sequence of keywords that trigger this service
        - corpus_path: Path to the corpus file (for static corpus)

    Subclasses may override:
        - load_corpus(): For dynamic corpus assembly
        - format_context(): For custom context formatting
    """

    name: str = ""
    keywords: Sequence[str] = ()
    corpus_path: Path | None = None

    def __init__(self) -> None:
        self._corpus_cache: str | None = None

    def detect_intent(self, prompt: str) -> bool:
        """
        Check if the user prompt matches this domain's keywords.

        Args:
            prompt: User message to check

        Returns:
            True if any keyword is found in the prompt
        """
        lower = prompt.lower()
        return any(kw in lower for kw in self.keywords)

    def load_corpus(self) -> str:
        """
        Load the domain corpus from file. Override for dynamic corpus.

        Returns:
            Corpus text content, or empty string on failure
        """
        if self._corpus_cache is not None:
            return self._corpus_cache

        if self.corpus_path is None:
            logger.warning(f"[{self.name}] No corpus_path configured")
            self._corpus_cache = ""
            return self._corpus_cache

        try:
            self._corpus_cache = self.corpus_path.read_text(encoding="utf-8")
            logger.debug(
                f"[{self.name}] Loaded corpus ({len(self._corpus_cache)} chars)"
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Could not load corpus: {e}")
            self._corpus_cache = ""

        return self._corpus_cache

    def format_context(self, corpus: str) -> str:
        """
        Format the corpus into a context block for prompt injection.

        Override for custom formatting. Default wraps with section header.

        Args:
            corpus: Raw corpus text

        Returns:
            Formatted context string
        """
        label = self.name.upper().replace(" ", "_")
        return (
            f"\n---\n\n"
            f"RAG CONTEXT ({self.name} patterns):\n"
            f"Use these proven patterns when generating {self.name} content:\n\n"
            f"{corpus}\n\n---\n"
        )

    async def get_context(self, prompt: str) -> str:
        """
        Get RAG context if the prompt matches this domain.

        This is the main entry point. Checks intent, loads corpus,
        and formats the context block.

        Args:
            prompt: User message

        Returns:
            Formatted context string, or empty string if no match
        """
        if not self.detect_intent(prompt):
            return ""

        corpus = self.load_corpus()
        if not corpus:
            return ""

        return self.format_context(corpus)
