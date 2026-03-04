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
import re
from abc import ABC
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
        - score_relevance(): For custom relevance scoring
    """

    name: str = ""
    keywords: Sequence[str] = ()
    corpus_path: Path | None = None
    min_score: float = 0.1  # Minimum relevance score to trigger context injection

    def __init__(self) -> None:
        self._corpus_cache: str | None = None

    def score_relevance(self, prompt: str) -> float:
        """
        Score how relevant this domain is to the given prompt (0.0 - 1.0).

        Scoring rules:
        - Whole-word keyword match: 1.0 weight
        - Substring-only match: 0.3 weight
        - Multi-word keywords (2+ words) get 1.5x multiplier
        - Normalized by factor of 3.0 (so 3 whole-word matches = score 1.0)

        Override for custom relevance scoring logic.

        Args:
            prompt: User message to score

        Returns:
            Relevance score between 0.0 and 1.0
        """
        lower = prompt.lower()
        total_weight = 0.0

        for kw in self.keywords:
            kw_lower = kw.lower()
            if kw_lower not in lower:
                continue

            # Check for whole-word match using word boundaries
            pattern = r'\b' + re.escape(kw_lower) + r'\b'
            is_whole_word = bool(re.search(pattern, lower))

            base_weight = 1.0 if is_whole_word else 0.3
            # Multi-word keywords are more specific, give 1.5x
            if ' ' in kw_lower:
                base_weight *= 1.5

            total_weight += base_weight

        return round(min(1.0, total_weight / 3.0), 2)

    def detect_intent(self, prompt: str) -> bool:
        """
        Check if the user prompt matches this domain's keywords.

        Uses score_relevance() internally — returns True if score >= min_score.

        Args:
            prompt: User message to check

        Returns:
            True if relevance score meets or exceeds min_score
        """
        return self.score_relevance(prompt) >= self.min_score

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
