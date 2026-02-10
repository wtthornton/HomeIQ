"""
Blueprint RAG Context Service

Epic: High-Value Domain Extensions, Story 5
Extends RAGContextService to inject blueprint selection and usage patterns
when user prompts mention blueprint-related keywords.
"""

import logging
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[4])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.patterns import RAGContextService

logger = logging.getLogger(__name__)

BLUEPRINT_KEYWORDS = (
    # Direct references
    "blueprint", "blueprints",
    # Synonyms
    "template", "templates", "prebuilt", "pre-built", "pre-made", "premade",
    "starter", "ready-made", "readymade", "out-of-the-box",
    # Blueprint actions
    "import blueprint", "use blueprint", "apply blueprint",
    "blueprint suggestion", "suggest blueprint", "suggest blueprints",
    "recommend blueprint",
    # Blueprint discovery
    "blueprint exchange", "community blueprint",
)


class BlueprintRAGService(RAGContextService):
    """
    Injects blueprint selection and usage corpus when user prompt
    mentions blueprint-related keywords.
    """

    name = "blueprint"
    keywords = BLUEPRINT_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "blueprint_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        """Format blueprint corpus with domain-specific header."""
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Blueprint patterns):\n"
            "Use these patterns when suggesting or configuring blueprints:\n\n"
            f"{corpus}\n\n---\n"
        )
