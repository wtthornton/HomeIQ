"""
Extract memory-worthy facts from user messages.

Story 30.1: Chat Memory Extraction
Analyzes user messages during chat to identify and persist memory-worthy facts
such as preferences, boundaries, and behavioral patterns.
"""

import logging
from typing import Any

from homeiq_memory import MemoryClient, MemoryType, SourceChannel

logger = logging.getLogger(__name__)


#: The shape `memory-extract` transcribes a chat message into.
#
# TAP-7275: this replaces the inline "respond with JSON" extraction prompt this
# module used to send to a provider. The gene behind the workflow is `hiq-extract`, whose contract is
# that a field the source does not state comes back null rather than guessed --
# which is the property this caller needs, because a guessed "fact" becomes a
# stored memory the assistant later treats as something the person said.
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "description": (
                "Facts the message explicitly states that are worth remembering. "
                "Empty when the message states none. Never infer or assume."
            ),
            "items": {
                "type": "object",
                "required": ["content", "memory_type"],
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The fact, at most 200 characters.",
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["preference", "boundary", "behavioral"],
                        "description": (
                            "preference = a like/dislike; boundary = a hard "
                            "'never do X' constraint; behavioral = a habit or pattern."
                        ),
                    },
                    "entity_ids": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Home Assistant entity ids the message named.",
                    },
                },
            },
        }
    },
}

MEMORY_TYPE_MAP = {
    "preference": MemoryType.PREFERENCE,
    "boundary": MemoryType.BOUNDARY,
    "behavioral": MemoryType.BEHAVIORAL,
}


class MemoryExtractor:
    """
    Extract and save memory-worthy facts from user chat messages.

    Uses an LLM to analyze user messages and identify facts that should be
    persisted in the memory system for future context injection.
    """

    def __init__(
        self,
        memory_client: MemoryClient,
        chat_client: Any,
        source_service: str = "automation-domain",
    ) -> None:
        """
        Initialize the memory extractor.

        Args:
            memory_client: MemoryClient instance for persistence
            chat_client: AgentForge-backed client (AgentChatClient)
            source_service: Service name for memory provenance
        """
        self.memory = memory_client
        self.chat = chat_client
        self.source_service = source_service

    async def extract_and_save(
        self,
        user_message: str,
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract memories from user message and save them.

        Args:
            user_message: The user's chat message to analyze
            conversation_id: Optional conversation ID for metadata

        Returns:
            List of saved fact dictionaries with 'content', 'memory_type',
            'entity_ids', and 'memory_id' keys. Empty list if no facts found
            or extraction fails.
        """
        if not user_message or not user_message.strip():
            return []

        if not self.memory.available:
            logger.warning(
                "Memory client not available, skipping extraction for conversation %s",
                conversation_id,
            )
            return []

        try:
            extracted_facts = await self._extract_facts(user_message)
            if not extracted_facts:
                logger.debug(
                    "No memorable facts found in message for conversation %s",
                    conversation_id,
                )
                return []

            saved_facts = []
            for fact in extracted_facts:
                memory = await self._save_fact(fact, conversation_id)
                if memory:
                    saved_facts.append(
                        {
                            "content": fact.get("content"),
                            "memory_type": fact.get("memory_type"),
                            "entity_ids": fact.get("entity_ids"),
                            "memory_id": memory.id,
                        }
                    )

            if saved_facts:
                logger.info(
                    "Extracted and saved %d memories from conversation %s",
                    len(saved_facts),
                    conversation_id,
                )

            return saved_facts

        except Exception as e:
            logger.error(
                "Memory extraction failed for conversation %s: %s",
                conversation_id,
                e,
                exc_info=True,
            )
            return []

    async def _extract_facts(self, user_message: str) -> list[dict[str, Any]]:
        """
        Call LLM to extract facts from the user message.

        Args:
            user_message: The user's chat message

        Returns:
            List of fact dictionaries or empty list if none found
        """
        try:
            instance = await self.chat.extract_json(user_message, EXTRACTION_SCHEMA)
        except Exception as e:  # noqa: BLE001 - degrade to "no facts", never fail a chat turn
            logger.error("AgentForge memory extraction failed: %s", e)
            return []

        facts = instance.get("facts") or []
        if not isinstance(facts, list):
            logger.warning("memory-extract returned a non-list 'facts' value")
            return []
        return [fact for fact in facts if isinstance(fact, dict) and self._validate_fact(fact)]

    def _validate_fact(self, fact: dict[str, Any]) -> bool:
        """
        Validate an extracted fact has required fields and valid values.

        Args:
            fact: Fact dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        content = fact.get("content")
        if not content or not isinstance(content, str) or len(content) < 5:
            return False

        memory_type = fact.get("memory_type")
        if memory_type not in MEMORY_TYPE_MAP:
            return False

        entity_ids = fact.get("entity_ids")
        return entity_ids is None or isinstance(entity_ids, list)

    async def _save_fact(
        self,
        fact: dict[str, Any],
        conversation_id: str | None,
    ) -> Any:
        """
        Save a single extracted fact to the memory store.

        Args:
            fact: Validated fact dictionary
            conversation_id: Optional conversation ID for metadata

        Returns:
            Saved Memory instance or None on failure
        """
        try:
            memory_type = MEMORY_TYPE_MAP.get(
                fact.get("memory_type", ""),
                MemoryType.PREFERENCE,
            )

            entity_ids = fact.get("entity_ids")
            if entity_ids:
                entity_ids = [str(eid) for eid in entity_ids if eid]

            metadata = {}
            if conversation_id:
                metadata["conversation_id"] = conversation_id

            memory = await self.memory.save(
                content=fact["content"][:1024],
                memory_type=memory_type,
                source_channel=SourceChannel.EXPLICIT,
                source_service=self.source_service,
                entity_ids=entity_ids if entity_ids else None,
                metadata=metadata if metadata else None,
                confidence=0.6,
            )

            logger.debug(
                "Saved memory id=%d type=%s: %s",
                memory.id,
                memory_type.value,
                fact["content"][:50],
            )
            return memory

        except Exception as e:
            logger.error("Failed to save memory: %s", e)
            return None
