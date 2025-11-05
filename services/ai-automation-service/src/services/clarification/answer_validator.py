"""
Answer Validator - Validates user answers to clarification questions
"""

import re
import logging
from typing import List, Dict, Any, Optional
from .models import ClarificationAnswer, ClarificationQuestion

logger = logging.getLogger(__name__)


class AnswerValidator:
    """Validates clarification answers"""
    
    def __init__(self):
        """Initialize answer validator"""
        pass
    
    async def validate_answer(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion,
        available_entities: Optional[List[Dict[str, Any]]] = None
    ) -> ClarificationAnswer:
        """
        Validate a user's answer to a clarification question.
        
        Args:
            answer: User's answer
            question: The question being answered
            available_entities: List of available entities for validation
            
        Returns:
            Validated ClarificationAnswer with validation results
        """
        validated_answer = ClarificationAnswer(
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            selected_entities=answer.selected_entities,
            confidence=0.0,
            validated=False
        )
        
        try:
            # Validate based on question type
            if question.question_type.value == "entity_selection":
                validated_answer = await self._validate_entity_selection(
                    answer, question, available_entities
                )
            elif question.question_type.value == "multiple_choice":
                validated_answer = self._validate_multiple_choice(answer, question)
            elif question.question_type.value == "boolean":
                validated_answer = self._validate_boolean(answer, question)
            else:  # text
                validated_answer = self._validate_text(answer, question)
            
            # Calculate confidence based on validation
            validated_answer.confidence = self._calculate_confidence(
                validated_answer, question
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            validated_answer.validation_errors = [str(e)]
            validated_answer.confidence = 0.0
        
        return validated_answer
    
    async def _validate_entity_selection(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion,
        available_entities: Optional[List[Dict[str, Any]]]
    ) -> ClarificationAnswer:
        """Validate entity selection answer"""
        validated_answer = ClarificationAnswer(
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            selected_entities=answer.selected_entities or [],
            validated=False
        )
        
        # If entities were selected, validate they exist
        if validated_answer.selected_entities:
            valid_entities = []
            invalid_entities = []
            
            if available_entities:
                entity_ids = {e.get('entity_id') for e in available_entities if e.get('entity_id')}
                
                for entity_id in validated_answer.selected_entities:
                    if entity_id in entity_ids:
                        valid_entities.append(entity_id)
                    else:
                        invalid_entities.append(entity_id)
            else:
                # No entities available for validation, assume valid
                valid_entities = validated_answer.selected_entities
            
            validated_answer.selected_entities = valid_entities
            
            if invalid_entities:
                validated_answer.validation_errors = [
                    f"Invalid entities: {', '.join(invalid_entities)}"
                ]
                validated_answer.validated = False
            else:
                validated_answer.validated = True
        else:
            # Try to extract entity IDs from answer text
            if available_entities:
                entity_ids = {e.get('entity_id') for e in available_entities if e.get('entity_id')}
                entity_names = {e.get('friendly_name', e.get('name', '')): e.get('entity_id') 
                               for e in available_entities if e.get('entity_id')}
                
                # Look for entity mentions in answer
                answer_lower = answer.answer_text.lower()
                found_entities = []
                
                for entity_id in entity_ids:
                    if entity_id.lower() in answer_lower:
                        found_entities.append(entity_id)
                
                for name, entity_id in entity_names.items():
                    if name.lower() in answer_lower and entity_id not in found_entities:
                        found_entities.append(entity_id)
                
                if found_entities:
                    validated_answer.selected_entities = found_entities
                    validated_answer.validated = True
                else:
                    validated_answer.validation_errors = [
                        "Could not find matching entities in your answer"
                    ]
                    validated_answer.validated = False
            else:
                # No way to validate, assume valid
                validated_answer.validated = True
        
        return validated_answer
    
    def _validate_multiple_choice(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion
    ) -> ClarificationAnswer:
        """Validate multiple choice answer"""
        validated_answer = ClarificationAnswer(
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            validated=False
        )
        
        if not question.options:
            validated_answer.validated = True  # No options to validate against
            return validated_answer
        
        # Check if answer matches any option (case-insensitive, partial match)
        answer_lower = answer.answer_text.lower().strip()
        
        matching_options = [
            opt for opt in question.options
            if answer_lower in opt.lower() or opt.lower() in answer_lower
        ]
        
        if matching_options:
            validated_answer.validated = True
            # Update answer text to match option
            validated_answer.answer_text = matching_options[0]
        else:
            validated_answer.validation_errors = [
                f"Answer doesn't match any option. Options: {', '.join(question.options)}"
            ]
            validated_answer.validated = False
        
        return validated_answer
    
    def _validate_boolean(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion
    ) -> ClarificationAnswer:
        """Validate boolean answer"""
        validated_answer = ClarificationAnswer(
            question_id=answer.question_id,
            answer_text=answer.answer_text,
            validated=False
        )
        
        answer_lower = answer.answer_text.lower().strip()
        
        # Check for yes/no patterns
        yes_patterns = ['yes', 'y', 'true', '1', 'sure', 'ok', 'okay', 'correct']
        no_patterns = ['no', 'n', 'false', '0', 'not', 'incorrect']
        
        if any(pattern in answer_lower for pattern in yes_patterns):
            validated_answer.answer_text = "yes"
            validated_answer.validated = True
        elif any(pattern in answer_lower for pattern in no_patterns):
            validated_answer.answer_text = "no"
            validated_answer.validated = True
        else:
            validated_answer.validation_errors = [
                "Please answer with yes or no"
            ]
            validated_answer.validated = False
        
        return validated_answer
    
    def _validate_text(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion
    ) -> ClarificationAnswer:
        """Validate text answer (minimal validation)"""
        validated_answer = ClarificationAnswer(
            question_id=answer.question_id,
            answer_text=answer.answer_text.strip(),
            validated=True  # Text answers are generally valid if not empty
        )
        
        if not validated_answer.answer_text:
            validated_answer.validation_errors = ["Answer cannot be empty"]
            validated_answer.validated = False
        
        return validated_answer
    
    def _calculate_confidence(
        self,
        answer: ClarificationAnswer,
        question: ClarificationQuestion
    ) -> float:
        """Calculate confidence in answer interpretation"""
        if not answer.validated:
            return 0.0
        
        confidence = 0.7  # Base confidence for validated answer
        
        # Increase confidence for structured answers
        if question.question_type.value == "multiple_choice" and answer.answer_text in (question.options or []):
            confidence = 0.95
        elif question.question_type.value == "entity_selection" and answer.selected_entities:
            confidence = 0.9
        elif question.question_type.value == "boolean":
            confidence = 0.85
        
        # Decrease if validation errors (even if validated)
        if answer.validation_errors:
            confidence *= 0.7
        
        return min(1.0, max(0.0, confidence))

