"""
Token Counting Utility for OpenAI Models

Provides accurate token counting using tiktoken for GPT-5 models.
"""

import tiktoken
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def get_encoding(model: str) -> tiktoken.Encoding:
    """
    Get tiktoken encoding for a given model.
    
    Args:
        model: Model name (gpt-5.1, gpt-5-mini, gpt-5-nano)
    
    Returns:
        tiktoken.Encoding instance
    """
    model_lower = model.lower()
    
    # GPT-5 models use cl100k_base encoding
    # Map model names to encoding
    if "gpt-5" in model_lower:
        try:
            # Try to get encoding for the specific model
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (used by GPT-4 and GPT-5)
            logger.warning(f"Model {model} not found in tiktoken, using cl100k_base encoding")
            return tiktoken.get_encoding("cl100k_base")
    else:
        # Default to cl100k_base
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-5.1") -> int:
    """
    Count tokens for a given text and model.
    
    Args:
        text: Text to count tokens for
        model: Model name (gpt-5.1, gpt-5-mini, gpt-5-nano)
    
    Returns:
        Number of tokens
    """
    if not text:
        return 0
    
    encoding = get_encoding(model)
    return len(encoding.encode(text))


def count_message_tokens(messages: List[Dict], model: str = "gpt-5.1") -> int:
    """
    Count tokens in OpenAI message format.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model name (gpt-5.1, gpt-5-mini, gpt-5-nano)
    
    Returns:
        Total number of tokens
    """
    encoding = get_encoding(model)
    tokens_per_message = 3  # Every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = 1  # If there's a name, the role is omitted
    
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if isinstance(value, str):
                num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    
    num_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def get_token_breakdown(messages: List[Dict], model: str = "gpt-5.1") -> Dict:
    """
    Break down token usage by component.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model name (gpt-5.1, gpt-5-mini, gpt-5-nano)
    
    Returns:
        Dictionary with token breakdown by component
    """
    encoding = get_encoding(model)
    breakdown = {
        'system_prompt': 0,
        'user_prompt': 0,
        'developer_notes': 0,
        'entity_context': 0,
        'conversation_history': 0,
        'other': 0,
        'overhead': 0,
        'total': 0
    }
    
    overhead = 3  # Base overhead for message formatting
    
    for message in messages:
        role = message.get('role', '')
        content = message.get('content', '')
        
        if not content:
            continue
        
        tokens = len(encoding.encode(content))
        overhead += 3  # Per-message overhead
        
        if role == 'system':
            breakdown['system_prompt'] += tokens
        elif role == 'user':
            # Try to identify components in user prompt
            if 'entity context' in content.lower() or 'entities:' in content.lower():
                breakdown['entity_context'] += tokens
            elif 'conversation' in content.lower() or 'history' in content.lower():
                breakdown['conversation_history'] += tokens
            else:
                breakdown['user_prompt'] += tokens
        elif role == 'developer':
            breakdown['developer_notes'] += tokens
        else:
            breakdown['other'] += tokens
    
    breakdown['overhead'] = overhead
    breakdown['total'] = sum(breakdown.values())
    
    return breakdown

