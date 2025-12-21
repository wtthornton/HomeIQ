"""
Clarification handler for automatically answering clarification questions.

Extracts context from prompts and generates appropriate answers to clarification
questions based on the original prompt content.
"""
import re
from typing import Any


class ClarificationHandler:
    """Auto-answer clarification questions based on prompt context"""
    
    def __init__(self, original_prompt: str):
        self.original_prompt = original_prompt.lower()
        # Extract context from prompt dynamically
        self.prompt_context = self._extract_prompt_context(original_prompt)
    
    def _extract_prompt_context(self, prompt: str) -> dict[str, Any]:
        """Extract context from prompt text dynamically"""
        prompt_lower = prompt.lower()
        context: dict[str, Any] = {}
        
        # Extract device/location mentions
        device_keywords = ['wled', 'light', 'thermostat', 'speaker', 'door', 'motion']
        location_keywords = ['office', 'kitchen', 'living room', 'bedroom', 'hallway']
        
        for keyword in device_keywords:
            if keyword in prompt_lower:
                context['device'] = keyword
                break
        
        for keyword in location_keywords:
            if keyword in prompt_lower:
                context['location'] = keyword
                break
        
        # Extract time intervals
        if '15 min' in prompt_lower or '15 minute' in prompt_lower:
            context['interval'] = '15 minutes'
        elif 'every' in prompt_lower and 'min' in prompt_lower:
            # Try to extract any minute value
            match = re.search(r'(\d+)\s*min', prompt_lower)
            if match:
                context['interval'] = f"{match.group(1)} minutes"
        
        # Extract duration
        if '15 sec' in prompt_lower or '15 second' in prompt_lower:
            context['duration'] = '15 seconds'
        elif 'second' in prompt_lower:
            match = re.search(r'(\d+)\s*second', prompt_lower)
            if match:
                context['duration'] = f"{match.group(1)} seconds"
        
        # Extract brightness
        if '100%' in prompt_lower or '100 percent' in prompt_lower:
            context['brightness'] = '100%'
        elif 'brightness' in prompt_lower:
            match = re.search(r'(\d+)%', prompt_lower)
            if match:
                context['brightness'] = f"{match.group(1)}%"
        
        # Extract effect/color preferences
        if 'random' in prompt_lower:
            context['effect'] = 'random'
            context['colors'] = 'random'
        
        # Extract time-based triggers
        if '7:00' in prompt_lower or '7 am' in prompt_lower:
            context['time'] = '7:00 AM'
        elif 'am' in prompt_lower or 'pm' in prompt_lower:
            match = re.search(r'(\d+):?(\d+)?\s*(am|pm)', prompt_lower)
            if match:
                context['time'] = f"{match.group(1)}:{match.group(2) or '00'} {match.group(3).upper()}"
        
        return context
    
    def answer_question(self, question: dict[str, Any]) -> dict[str, Any]:
        """
        Generate answer for a clarification question based on prompt context.
        Returns answer in format: {question_id, answer_text, selected_entities}
        """
        question_id = question.get('id', '')
        question_text = question.get('question_text', '').lower()
        question_type = question.get('question_type', '')
        options = question.get('options', [])
        related_entities = question.get('related_entities', [])
        
        answer = {
            'question_id': question_id,
            'answer_text': '',
            'selected_entities': None
        }
        
        # Entity selection questions
        if question_type == 'entity_selection':
            if related_entities:
                # Try to match entities based on prompt context
                device = self.prompt_context.get('device', '').lower()
                location = self.prompt_context.get('location', '').lower()
                
                # Priority: 1) device + location match, 2) device match, 3) location match, 4) first entity
                if device and location:
                    matched = [e for e in related_entities 
                              if device in e.lower() and location in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                if device:
                    matched = [e for e in related_entities if device in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                if location:
                    matched = [e for e in related_entities if location in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                # Default: first entity
                answer['selected_entities'] = related_entities[:1]
                answer['answer_text'] = related_entities[0]
                return answer
        
        # Multiple choice questions
        elif question_type == 'multiple_choice':
            if options:
                # Try to match options with prompt context
                for option in options:
                    option_lower = str(option).lower()
                    # Match device
                    if self.prompt_context.get('device') and self.prompt_context['device'] in option_lower:
                        answer['answer_text'] = str(option)
                        return answer
                    # Match location
                    if self.prompt_context.get('location') and self.prompt_context['location'] in option_lower:
                        answer['answer_text'] = str(option)
                        return answer
                    # Match time
                    if self.prompt_context.get('time') and self.prompt_context['time'].lower() in option_lower:
                        answer['answer_text'] = str(option)
                        return answer
                    # Match brightness
                    if self.prompt_context.get('brightness') and self.prompt_context['brightness'] in option_lower:
                        answer['answer_text'] = str(option)
                        return answer
                
                # Default: first option
                answer['answer_text'] = str(options[0])
                return answer
        
        # Text input questions
        elif question_type == 'text_input':
            # Use context values if available
            if 'time' in question_text:
                if self.prompt_context.get('time'):
                    answer['answer_text'] = self.prompt_context['time']
                    return answer
            if 'brightness' in question_text or 'percent' in question_text:
                if self.prompt_context.get('brightness'):
                    answer['answer_text'] = self.prompt_context['brightness']
                    return answer
            if 'duration' in question_text or 'second' in question_text:
                if self.prompt_context.get('duration'):
                    answer['answer_text'] = self.prompt_context['duration']
                    return answer
            if 'interval' in question_text or 'minute' in question_text:
                if self.prompt_context.get('interval'):
                    answer['answer_text'] = self.prompt_context['interval']
                    return answer
            
            # Default: generic answer
            answer['answer_text'] = "Yes"
            return answer
        
        # Boolean questions
        elif question_type == 'boolean':
            # Default to "Yes" for most questions
            answer['answer_text'] = "Yes"
            return answer
        
        # Default fallback
        answer['answer_text'] = "Yes"
        return answer

