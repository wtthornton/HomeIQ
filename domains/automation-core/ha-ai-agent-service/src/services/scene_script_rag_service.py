"""
Scene/Script RAG Context Service

Epic: Platform-Wide Pattern Rollout, Story 6
Extends RAGContextService to inject scene and script creation patterns when
user prompts mention scene/script keywords.
"""

import logging

from homeiq_patterns import RAGContextService

logger = logging.getLogger(__name__)

SCENE_SCRIPT_KEYWORDS = (
    # Scene
    "scene", "scenes", "activate scene", "create scene",
    # Script
    "script", "scripts", "run script", "create script",
    # Common scene names
    "movie night", "movie mode", "morning routine", "bedtime",
    "good night", "good morning", "party mode", "dinner",
    "reading", "romantic", "relax",
    # Sequence / workflow
    "sequence", "workflow", "step by step", "steps",
    # Actions
    "turn_on", "turn_off", "toggle",
)


class SceneScriptRAGService(RAGContextService):
    """
    Injects scene and script patterns when user prompt mentions
    scene/script-related keywords.
    """

    name = "scene_script"
    keywords = SCENE_SCRIPT_KEYWORDS
    corpus_path = Path(__file__).parent.parent / "data" / "scene_script_patterns.md"

    def __init__(self) -> None:
        super().__init__()

    def format_context(self, corpus: str) -> str:
        return (
            "\n---\n\nAUTOMATION RAG CONTEXT (Scene/Script patterns):\n"
            "Use these patterns when creating scenes or scripts:\n\n"
            f"{corpus}\n\n---\n"
        )
