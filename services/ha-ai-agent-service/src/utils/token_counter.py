"""
Token Counting Utility for OpenAI Models
Epic AI-20 Story AI20.3

Provides accurate token counting using tiktoken for GPT-4o models.
"""

import logging

import tiktoken

logger = logging.getLogger(__name__)


def get_encoding(model: str) -> tiktoken.Encoding:
    """
    Get tiktoken encoding for a given model.

    Args:
        model: Model name (gpt-4o, gpt-4o-mini)

    Returns:
        tiktoken.Encoding instance
    """
    model_lower = model.lower()

    # GPT-4o models use cl100k_base encoding
    if "gpt-4" in model_lower or "gpt-3" in model_lower:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(
                f"Model {model} not found in tiktoken, using cl100k_base encoding"
            )
            return tiktoken.get_encoding("cl100k_base")
    else:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count tokens for a given text and model.

    Args:
        text: Text to count tokens for
        model: Model name (gpt-4o, gpt-4o-mini)

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    encoding = get_encoding(model)
    return len(encoding.encode(text))


def count_message_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """
    Count tokens in OpenAI message format.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model name (gpt-4o, gpt-4o-mini)

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

