"""
GPT-5.1 Parameter Utilities

Provides utility functions for constructing GPT-5.1 API parameters
with correct nested structure per OpenAI API specifications.

GPT-5.1 Parameter Structure:
- reasoning: { effort: "none" | "low" | "medium" | "high" }
- text: { verbosity: "low" | "medium" | "high" }
- prompt_cache_retention: "24h" (optional, for caching)

Critical Rules:
- When reasoning.effort != "none": temperature, top_p, logprobs NOT allowed
- When reasoning.effort == "none": temperature, top_p, logprobs ARE allowed
- text.verbosity can be used in all modes

Created: 2025 - GPT-5.1 parameter standardization
"""

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)


def _get_settings():
    """
    Get settings with defensive import to avoid circular dependencies.
    
    Returns:
        Settings object or None if not available
    """
    try:
        from ...config import settings
        return settings
    except ImportError:
        logger.debug("Settings not available (circular import or not initialized)")
        return None


def is_gpt51_model(model: str) -> bool:
    """
    Check if model is a GPT-5.1 variant.
    
    Args:
        model: Model name (e.g., 'gpt-5.1', 'gpt-5.1-instant', etc.)
    
    Returns:
        True if model is GPT-5.1 variant, False otherwise
    """
    if not model or not isinstance(model, str):
        return False
    return model.startswith('gpt-5')


def get_gpt51_params_for_use_case(
    model: str,
    use_case: Literal["deterministic", "creative", "structured", "extraction"],
    enable_prompt_caching: bool | None = None
) -> dict[str, Any]:
    """
    Get GPT-5.1 parameters optimized for specific use case.
    
    Args:
        model: Model name (e.g., 'gpt-5.1')
        use_case: Use case type:
            - "deterministic": Low temperature, needs temperature control (reasoning='none')
            - "creative": Higher reasoning, no temperature control (reasoning='medium')
            - "structured": Structured output, balanced (reasoning='none' for temperature)
            - "extraction": Extraction tasks, low temperature (reasoning='none')
        enable_prompt_caching: Whether to enable prompt caching (default: from settings)
    
    Returns:
        Dictionary with properly nested GPT-5.1 parameters
        Empty dict if not GPT-5.1 model
    """
    if not is_gpt51_model(model):
        return {}
    
    if enable_prompt_caching is None:
        settings_obj = _get_settings()
        enable_prompt_caching = getattr(settings_obj, 'enable_prompt_caching', True) if settings_obj else True
    
    params: dict[str, Any] = {}
    
    # Validate use_case
    valid_use_cases = {"deterministic", "creative", "structured", "extraction"}
    if use_case not in valid_use_cases:
        logger.warning(
            f"Invalid use_case '{use_case}'. Valid options: {valid_use_cases}. "
            f"Using default 'deterministic'."
        )
        use_case = "deterministic"
    
    # Set reasoning effort based on use case
    if use_case == "deterministic":
        # Deterministic tasks need temperature control, so reasoning='none'
        params['reasoning'] = {'effort': 'none'}
        params['text'] = {'verbosity': 'low'}  # Concise output
    elif use_case == "creative":
        # Creative tasks benefit from reasoning, so no temperature control
        params['reasoning'] = {'effort': 'medium'}  # Balanced reasoning
        params['text'] = {'verbosity': 'medium'}  # Balanced detail
    elif use_case == "structured":
        # Structured output needs temperature control for consistency
        params['reasoning'] = {'effort': 'none'}  # Enable temperature
        params['text'] = {'verbosity': 'low'}  # Concise structured output
    elif use_case == "extraction":
        # Extraction tasks need temperature control for consistency
        params['reasoning'] = {'effort': 'none'}  # Enable temperature
        params['text'] = {'verbosity': 'low'}  # Concise extraction
    
    # Add prompt caching if enabled
    if enable_prompt_caching:
        params['prompt_cache_retention'] = '24h'
    
    logger.debug(f"GPT-5.1 params for {use_case}: {params}")
    return params


def can_use_temperature(model: str, gpt51_params: dict[str, Any] | None = None) -> bool:
    """
    Check if temperature parameter can be used with given GPT-5.1 parameters.
    
    Args:
        model: Model name
        gpt51_params: GPT-5.1 parameters dict (optional, will check if GPT-5.1 model)
    
    Returns:
        True if temperature can be used, False otherwise
    """
    if not is_gpt51_model(model):
        # Non-GPT-5.1 models can always use temperature
        return True
    
    if gpt51_params is None:
        # Default: assume reasoning='none' if not specified
        return True
    
    # Check reasoning effort
    reasoning = gpt51_params.get('reasoning', {})
    if isinstance(reasoning, dict):
        effort = reasoning.get('effort', 'none')
    else:
        # Legacy format (flat key)
        effort = gpt51_params.get('reasoning_effort', 'none')
    
    # Temperature only allowed when reasoning effort is 'none'
    return effort == 'none'


def merge_gpt51_params(base_params: dict[str, Any], gpt51_params: dict[str, Any]) -> dict[str, Any]:
    """
    Merge GPT-5.1 parameters into base API parameters, handling nested structure.
    
    Args:
        base_params: Base API parameters (model, messages, temperature, etc.)
        gpt51_params: GPT-5.1 specific parameters (with nested structure)
    
    Returns:
        Merged parameters dict
    """
    merged = base_params.copy()
    
    # Handle nested reasoning parameter
    if 'reasoning' in gpt51_params:
        merged['reasoning'] = gpt51_params['reasoning']
    
    # Handle nested text.verbosity parameter
    if 'text' in gpt51_params:
        merged['text'] = gpt51_params['text']
    
    # Handle prompt_cache_retention
    if 'prompt_cache_retention' in gpt51_params:
        merged['prompt_cache_retention'] = gpt51_params['prompt_cache_retention']
    
    # Remove temperature if reasoning.effort != 'none'
    reasoning = merged.get('reasoning', {})
    if isinstance(reasoning, dict):
        effort = reasoning.get('effort', 'none')
        if effort != 'none' and 'temperature' in merged:
            logger.info(
                f"Auto-removed temperature/top_p/logprobs (reasoning.effort={effort} doesn't support "
                f"these parameters. Set reasoning.effort='none' to enable temperature control.)"
            )
            merged.pop('temperature', None)
            merged.pop('top_p', None)
            merged.pop('logprobs', None)
    
    return merged


def remove_unsupported_gpt51_params(api_params: dict[str, Any]) -> dict[str, Any]:
    """
    Remove GPT-5.1 parameters that are not supported by the OpenAI Python SDK.
    
    The OpenAI Python SDK may not support GPT-5.1 parameters (reasoning, text, 
    prompt_cache_retention) in all versions. This function removes them to avoid
    TypeError when calling the API.
    
    Args:
        api_params: API parameters dict that may contain GPT-5.1 parameters
    
    Returns:
        API parameters dict with unsupported GPT-5.1 parameters removed
    """
    cleaned_params = api_params.copy()
    removed_params = []
    
    # Parameters that may not be supported by the SDK
    unsupported_params = ["reasoning", "text", "prompt_cache_retention"]
    
    for param in unsupported_params:
        if param in cleaned_params:
            removed_params.append(param)
            cleaned_params.pop(param)
    
    if removed_params:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(
            f"Removed GPT-5.1 parameters not supported by SDK: {removed_params}. "
            f"Model: {api_params.get('model', 'unknown')}"
        )
    
    return cleaned_params


# Legacy compatibility: flat parameter format
def get_gpt51_params_legacy(model: str, reasoning_effort: str = 'medium', verbosity: str = 'low') -> dict[str, Any]:
    """
    Get GPT-5.1 parameters in legacy flat format (for backward compatibility).
    
    DEPRECATED: Use get_gpt51_params_for_use_case() instead.
    
    Args:
        model: Model name
        reasoning_effort: Reasoning effort level
        verbosity: Verbosity level
    
    Returns:
        Dictionary with flat keys (for backward compatibility)
    """
    if not is_gpt51_model(model):
        return {}
    
    logger.warning(
        "Using deprecated get_gpt51_params_legacy(). "
        "Please use get_gpt51_params_for_use_case() instead."
    )
    
    return {
        'reasoning_effort': reasoning_effort,
        'verbosity': verbosity
    }

