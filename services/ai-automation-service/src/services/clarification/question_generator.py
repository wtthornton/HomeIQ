"""
Question Generator - Generates structured clarification questions using OpenAI
"""

import json
import logging
from typing import Any

from .models import Ambiguity, AmbiguitySeverity, AmbiguityType, ClarificationQuestion, QuestionType

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates structured clarification questions"""

    def __init__(self, openai_client):
        """
        Initialize question generator.

        Args:
            openai_client: OpenAI client instance
        """
        self.openai_client = openai_client

    async def generate_questions(
        self,
        ambiguities: list[Ambiguity],
        query: str,
        context: dict[str, Any],
        previous_qa: list[dict[str, Any]] | None = None,  # NEW: Previous Q&A pairs
        asked_questions: list["ClarificationQuestion"] | None = None,  # NEW: Previously asked questions
    ) -> list[ClarificationQuestion]:
        """
        Generate questions based on detected ambiguities.

        Uses OpenAI to create natural, contextual questions.

        Args:
            ambiguities: List of detected ambiguities
            query: Original user query
            context: Additional context (devices, entities, etc.)

        Returns:
            List of ClarificationQuestion objects
        """
        if not ambiguities:
            return []

        # Prioritize ambiguities (critical first)
        prioritized_ambiguities = sorted(
            ambiguities,
            key=lambda a: (a.severity == AmbiguitySeverity.CRITICAL, a.severity == AmbiguitySeverity.IMPORTANT),
            reverse=True,
        )

        # Limit to top 3 ambiguities to avoid overwhelming user
        top_ambiguities = prioritized_ambiguities[:3]

        # Build prompt for OpenAI
        prompt = self._build_question_generation_prompt(
            top_ambiguities, query, context, previous_qa, asked_questions,
        )

        try:
            # Call OpenAI
            response = await self.openai_client.client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Home Assistant automation assistant helping users clarify their automation requests. Generate natural, helpful clarification questions. Respond ONLY with JSON, no markdown formatting.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,  # Consistent with existing patterns
                max_completion_tokens=400,  # Use max_completion_tokens for newer models
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            questions_data = json.loads(content)

            # Parse questions
            questions = self._parse_questions(questions_data, top_ambiguities)

            logger.info(f"✅ Generated {len(questions)} clarification questions")
            return questions

        except Exception as e:
            logger.error(f"Failed to generate questions: {e}", exc_info=True)
            # Fallback: Generate simple questions from ambiguities
            return self._generate_fallback_questions(top_ambiguities)

    def _build_question_generation_prompt(
        self,
        ambiguities: list[Ambiguity],
        query: str,
        context: dict[str, Any],
        previous_qa: list[dict[str, Any]] | None = None,
        asked_questions: list["ClarificationQuestion"] | None = None,
    ) -> str:
        """Build prompt for OpenAI question generation"""

        # Format ambiguities
        ambiguities_text = []
        for amb in ambiguities:
            amb_text = f"- {amb.type.value.upper()}: {amb.description}"
            if amb.context:
                if "matches" in amb.context:
                    matches = amb.context["matches"]
                    if isinstance(matches, list) and matches:
                        amb_text += f"\n  Found: {len(matches)} matching entities"
                        for match in matches[:5]:  # Show first 5
                            name = match.get("name", match.get("entity_id", "unknown"))
                            amb_text += f"\n    - {name}"
                if "suggestion" in amb.context:
                    amb_text += f"\n  Suggestion: {amb.context['suggestion']}"
            ambiguities_text.append(amb_text)

        # NEW: Add previous Q&A context to prompt
        previous_qa_section = ""
        if previous_qa:
            previous_qa_section = "\n\n**PREVIOUS CLARIFICATIONS (User has already answered these - DO NOT repeat):**\n"
            for i, qa in enumerate(previous_qa, 1):
                previous_qa_section += f"{i}. Q: {qa.get('question', '')}\n"
                previous_qa_section += f"   A: {qa.get('answer', '')}\n"
                if qa.get("selected_entities"):
                    previous_qa_section += f"   Selected entities: {', '.join(qa['selected_entities'])}\n"
            previous_qa_section += "\n⚠️ IMPORTANT: Do NOT ask questions that are similar to the ones above. Build on the user's answers to ask NEW questions about remaining ambiguities.\n"

        # NEW: List already-asked questions to avoid duplicates
        asked_questions_section = ""
        if asked_questions:
            asked_questions_section = "\n\n**ALREADY-ASKED QUESTIONS (DO NOT repeat these):**\n"
            for i, q in enumerate(asked_questions, 1):
                asked_questions_section += f"{i}. {q.question_text}\n"
            asked_questions_section += "\n⚠️ CRITICAL: Generate questions that are DIFFERENT from the ones above. Focus on remaining ambiguities that haven't been addressed yet.\n"

        # Format available devices summary
        devices_summary = "Available devices:\n"
        if "devices" in context:
            devices = context["devices"]
            if isinstance(devices, list):
                for device in devices[:10]:  # Show first 10
                    device_name = device.get("name", device.get("friendly_name", "unknown"))
                    device_id = device.get("entity_id", device.get("id", "unknown"))
                    devices_summary += f"- {device_name} ({device_id})\n"
        elif "entities_by_domain" in context:
            entities_by_domain = context["entities_by_domain"]
            for domain, entities in list(entities_by_domain.items())[:5]:
                devices_summary += f"\n{domain.upper()}:\n"
                for entity in entities[:5]:
                    name = entity.get("friendly_name", entity.get("entity_id", "unknown"))
                    devices_summary += f"  - {name}\n"

        return f"""You are a Home Assistant automation assistant helping users clarify their automation requests.

**User Query:**
"{query}"

{previous_qa_section}

{asked_questions_section}

**Detected Ambiguities (REMAINING - need clarification):**
{chr(10).join(ambiguities_text)}

{devices_summary}

**Task:**
Generate 1-3 NEW clarification questions that will help clarify the REMAINING ambiguities above. Prioritize critical ambiguities.

**CRITICAL REQUIREMENTS:**
1. DO NOT repeat any questions that were already asked (see PREVIOUS CLARIFICATIONS and ALREADY-ASKED QUESTIONS above)
2. Build on the user's previous answers - use their selections to ask more specific follow-up questions
3. If the user already selected specific devices, ask about OTHER aspects (timing, actions, conditions, etc.)
4. Focus on ambiguities that haven't been resolved yet
5. If all ambiguities are about the same topic but different aspects, ask about the NEW aspect

**Guidelines:**
1. Ask ONE question per critical/important ambiguity (max 3 questions total)
2. Use natural, conversational language
3. Provide helpful context (e.g., "I found 4 Hue lights - which ones?")
4. Offer suggestions when possible (e.g., "Did you mean: presence sensor or motion sensor?")
5. Be specific but concise
6. For device selection, list available options when there are 5 or fewer

**Output Format (JSON):**
{{
  "questions": [
    {{
      "id": "q1",
      "category": "device",
      "question_text": "There are 4 Hue lights in your office. Did you want all four to flash, or specific ones?",
      "question_type": "multiple_choice",
      "options": ["All four lights", "Only specific lights (please specify)", "Just the main light"],
      "priority": 1,
      "related_entities": ["light.office_hue_1", "light.office_hue_2"]
    }}
  ]
}}

Generate questions now (respond ONLY with JSON, no other text):"""


    def _parse_questions(
        self,
        questions_data: dict[str, Any],
        ambiguities: list[Ambiguity],
    ) -> list[ClarificationQuestion]:
        """Parse questions from OpenAI response"""
        questions = []

        if "questions" not in questions_data:
            logger.warning("No 'questions' field in OpenAI response")
            return []

        # Create ambiguity lookup by type
        {amb.type: amb for amb in ambiguities}

        for i, q_data in enumerate(questions_data["questions"]):
            try:
                # Map question type string to enum
                question_type_str = q_data.get("question_type", "text").lower()
                if question_type_str == "multiple_choice":
                    question_type = QuestionType.MULTIPLE_CHOICE
                elif question_type_str == "entity_selection":
                    question_type = QuestionType.ENTITY_SELECTION
                elif question_type_str == "boolean":
                    question_type = QuestionType.BOOLEAN
                else:
                    question_type = QuestionType.TEXT

                # Find related ambiguity
                ambiguity_id = None
                category = q_data.get("category", "unknown")
                for amb in ambiguities:
                    if amb.type.value == category:
                        ambiguity_id = amb.id
                        break

                question = ClarificationQuestion(
                    id=q_data.get("id", f"q{i+1}"),
                    category=category,
                    question_text=q_data.get("question_text", ""),
                    question_type=question_type,
                    options=q_data.get("options"),
                    context=q_data.get("context", {}),
                    priority=q_data.get("priority", 2),
                    related_entities=q_data.get("related_entities"),
                    ambiguity_id=ambiguity_id,
                )
                questions.append(question)
            except Exception as e:
                logger.exception(f"Failed to parse question {i}: {e}")
                continue

        return questions

    def _generate_fallback_questions(
        self,
        ambiguities: list[Ambiguity],
    ) -> list[ClarificationQuestion]:
        """Generate simple fallback questions when OpenAI fails"""
        questions = []

        for i, amb in enumerate(ambiguities[:3]):  # Max 3
            if amb.type == AmbiguityType.DEVICE:
                question_text = f"Which device did you mean? {amb.description}"
                if amb.context.get("matches"):
                    matches = amb.context["matches"]
                    options = [f"{m.get('name', m.get('entity_id', 'unknown'))}" for m in matches[:5]]
                    question_type = QuestionType.MULTIPLE_CHOICE
                else:
                    options = None
                    question_type = QuestionType.TEXT
            elif amb.type == AmbiguityType.TRIGGER:
                question_text = f"Could you clarify the trigger? {amb.description}"
                question_type = QuestionType.TEXT
                options = None
            else:
                question_text = f"Could you clarify: {amb.description}"
                question_type = QuestionType.TEXT
                options = None

            question = ClarificationQuestion(
                id=f"q{i+1}",
                category=amb.type.value,
                question_text=question_text,
                question_type=question_type,
                options=options,
                priority=1 if amb.severity == AmbiguitySeverity.CRITICAL else 2,
                related_entities=amb.related_entities,
                ambiguity_id=amb.id,
            )
            questions.append(question)

        return questions

