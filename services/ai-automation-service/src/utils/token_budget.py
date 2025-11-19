"""
Token Budget Enforcement Utilities

Enforces token budgets for different prompt components to prevent exceeding rate limits.
"""

import logging
from typing import Dict, List, Optional
from ..utils.token_counter import count_tokens, count_message_tokens

logger = logging.getLogger(__name__)


def enforce_token_budget(
    prompt_dict: Dict[str, str],
    budget: Dict[str, int],
    model: str = "gpt-5.1"
) -> Dict[str, str]:
    """
    Enforce token budget limits on prompt components.
    
    Args:
        prompt_dict: Dictionary with prompt components (system_prompt, user_prompt, etc.)
        budget: Dictionary with token limits per component
        model: Model name for token counting
    
    Returns:
        Modified prompt_dict with components truncated to fit budget
    """
    result = prompt_dict.copy()
    
    # Enforce conversation history limit
    if 'conversation_history' in prompt_dict and 'max_conversation_history_tokens' in budget:
        history = prompt_dict.get('conversation_history', '')
        if history:
            history_tokens = count_tokens(history, model)
            max_tokens = budget['max_conversation_history_tokens']
            
            if history_tokens > max_tokens:
                logger.warning(
                    f"Conversation history exceeds budget: {history_tokens} > {max_tokens} tokens. "
                    f"Truncating to last {max_tokens} tokens."
                )
                # Truncate by keeping last N tokens (simple approach)
                # In production, you might want to summarize older context
                result['conversation_history'] = _truncate_text_to_tokens(history, max_tokens, model)
    
    # Enforce enrichment context limit
    if 'enrichment_context' in prompt_dict and 'max_enrichment_context_tokens' in budget:
        enrichment = prompt_dict.get('enrichment_context', '')
        if enrichment:
            enrichment_tokens = count_tokens(enrichment, model)
            max_tokens = budget['max_enrichment_context_tokens']
            
            if enrichment_tokens > max_tokens:
                logger.warning(
                    f"Enrichment context exceeds budget: {enrichment_tokens} > {max_tokens} tokens. "
                    f"Truncating."
                )
                result['enrichment_context'] = _truncate_text_to_tokens(enrichment, max_tokens, model)
    
    # Enforce entity context limit (in user_prompt)
    if 'user_prompt' in prompt_dict and 'max_entity_context_tokens' in budget:
        user_prompt = prompt_dict.get('user_prompt', '')
        if 'entity context' in user_prompt.lower() or 'entities:' in user_prompt.lower():
            # Extract entity context section
            entity_context = _extract_entity_context(user_prompt)
            if entity_context:
                entity_tokens = count_tokens(entity_context, model)
                max_tokens = budget['max_entity_context_tokens']
                
                if entity_tokens > max_tokens:
                    logger.warning(
                        f"Entity context exceeds budget: {entity_tokens} > {max_tokens} tokens. "
                        f"Truncating."
                    )
                    truncated_context = _truncate_text_to_tokens(entity_context, max_tokens, model)
                    result['user_prompt'] = user_prompt.replace(entity_context, truncated_context)
    
    return result


def _truncate_text_to_tokens(text: str, max_tokens: int, model: str) -> str:
    """
    Truncate text to fit within token budget.
    
    Simple approach: Keep the last N tokens.
    For better results, you might want to summarize or prioritize important sections.
    """
    encoding = None
    try:
        from tiktoken import encoding_for_model
        encoding = encoding_for_model(model)
    except (KeyError, ImportError):
        from tiktoken import get_encoding
        encoding = get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    # Keep last max_tokens tokens
    truncated_tokens = tokens[-max_tokens:]
    return encoding.decode(truncated_tokens)


def _extract_entity_context(user_prompt: str) -> Optional[str]:
    """
    Extract entity context section from user prompt.
    
    Returns:
        Entity context string or None if not found
    """
    # Look for common patterns
    patterns = [
        r'ENTITY CONTEXT:.*?(?=USER QUERY:|$)',
        r'Entities:.*?(?=Query:|$)',
        r'Available entities:.*?(?=Request:|$)',
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, user_prompt, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0)
    
    return None


def check_token_budget(
    messages: List[Dict],
    budget: Dict[str, int],
    model: str = "gpt-5.1"
) -> Dict[str, any]:
    """
    Check if messages fit within token budget and return status.
    
    Args:
        messages: List of message dicts
        budget: Dictionary with token limits
        model: Model name for token counting
    
    Returns:
        Dictionary with budget status and recommendations
    """
    total_tokens = count_message_tokens(messages, model)
    max_total = budget.get('max_total_tokens', 30_000)  # Default OpenAI limit
    
    breakdown = {}
    for message in messages:
        role = message.get('role', '')
        content = message.get('content', '')
        if content:
            tokens = count_tokens(content, model)
            breakdown[role] = breakdown.get(role, 0) + tokens
    
    status = {
        'total_tokens': total_tokens,
        'max_tokens': max_total,
        'within_budget': total_tokens <= max_total,
        'usage_percent': (total_tokens / max_total) * 100 if max_total > 0 else 0,
        'breakdown': breakdown,
        'warnings': []
    }
    
    # Add warnings
    if total_tokens > max_total * 0.9:
        status['warnings'].append(f"Token usage at {status['usage_percent']:.1f}% of budget")
    
    if total_tokens > max_total:
        status['warnings'].append(f"Token usage exceeds budget by {total_tokens - max_total} tokens")
    
    return status

