"""
Extract memory-worthy facts from user messages.

Story 30.1: Chat Memory Extraction
Analyzes user messages during chat to identify and persist memory-worthy facts
such as preferences, boundaries, and behavioral patterns.
"""

import json
import logging
from typing import Any

from homeiq_memory import MemoryClient, MemoryType, SourceChannel

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a memory extraction assistant for a smart home AI system.
Analyze the user message and extract any facts worth remembering for future interactions.

User message: {message}

If there are memorable facts, respond with JSON:
{{"facts": [
  {{"content": "...", "memory_type": "preference|boundary|behavioral", "entity_ids": ["entity.id"] or null}}
]}}

If nothing worth remembering, respond with: {{"facts": []}}

Memory types:
- preference: User likes/dislikes, preferences (e.g., "I like warm lighting", "I prefer 68°F")
- boundary: Hard constraints, "never do X" statements (e.g., "Never turn off the porch light")
- behavioral: Usage patterns, habits (e.g., "I work from home on Fridays", "I wake up at 7am")

Guidelines:
- Only extract clear, explicit facts. Do not infer or assume.
- Include relevant Home Assistant entity IDs if mentioned (e.g., light.living_room, climate.main_floor)
- Keep content concise but complete (max 200 characters per fact)
- Ignore greetings, questions about capabilities, or general conversation
- Focus on actionable information that would improve automation responses

Examples of extractable facts:
- "I hate when lights turn on automatically at night" -> boundary about light automation
- "Set the bedroom to 72 degrees, that's my preferred temperature" -> preference for temperature
- "I always watch TV in the evening after 8pm" -> behavioral pattern"""

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
        openai_client: Any,
        source_service: str = "ha-ai-agent-service",
    ) -> None:
        """
        Initialize the memory extractor.

        Args:
            memory_client: MemoryClient instance for persistence
            openai_client: OpenAI client for LLM extraction
            source_service: Service name for memory provenance
        """
        self.memory = memory_client
        self.openai = openai_client
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
                    saved_facts.append({
                        "content": fact.get("content"),
                        "memory_type": fact.get("memory_type"),
                        "entity_ids": fact.get("entity_ids"),
                        "memory_id": memory.id,
                    })

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
        prompt = EXTRACTION_PROMPT.format(message=user_message)

        try:
            response = await self.openai.chat_completion_simple(
                system_prompt="You are a JSON extraction assistant. Always respond with valid JSON only.",
                user_message=prompt,
            )

            if not response:
                return []

            response_text = response.strip()
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            parsed = json.loads(response_text)
            facts = parsed.get("facts", [])

            validated_facts = []
            for fact in facts:
                if self._validate_fact(fact):
                    validated_facts.append(fact)

            return validated_facts

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse extraction response as JSON: %s", e)
            return []
        except Exception as e:
            logger.error("LLM extraction call failed: %s", e)
            return []

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
