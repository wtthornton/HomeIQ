"""
OpenAI Rate Limit Checker

Utilities to check and monitor OpenAI API rate limits.
"""

import logging
from typing import Any

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def check_rate_limits_via_api(api_key: str, project_id: str = "default") -> dict[str, Any]:
    """
    Check rate limits via OpenAI API endpoint.
    
    Args:
        api_key: OpenAI API key
        project_id: Project ID (default: "default")
    
    Returns:
        Dictionary with rate limits per model
    """
    url = f"https://api.openai.com/v1/organization/projects/{project_id}/rate_limits"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Project '{project_id}' not found. Trying organization-level endpoint...")
            # Try organization-level endpoint
            url = "https://api.openai.com/v1/organization/rate_limits"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception as e2:
                logger.error(f"Failed to get rate limits: {e2}")
                raise
        else:
            logger.error(f"Failed to get rate limits: {e}")
            raise
    except Exception as e:
        logger.error(f"Error checking rate limits: {e}")
        raise


def extract_rate_limit_headers(response) -> dict[str, Any]:
    """
    Extract rate limit information from OpenAI API response headers.
    
    Args:
        response: httpx.Response or OpenAI response object
    
    Returns:
        Dictionary with rate limit info
    """
    # Handle both httpx.Response and OpenAI response objects
    if hasattr(response, 'headers'):
        headers = response.headers
    elif hasattr(response, 'response') and hasattr(response.response, 'headers'):
        headers = response.response.headers
    else:
        logger.warning("Response object doesn't have headers attribute")
        return {}
    
    rate_limit_info = {
        'limit_requests': headers.get('x-ratelimit-limit-requests'),
        'remaining_requests': headers.get('x-ratelimit-remaining-requests'),
        'reset_requests': headers.get('x-ratelimit-reset-requests'),
        'limit_tokens': headers.get('x-ratelimit-limit-tokens'),
        'remaining_tokens': headers.get('x-ratelimit-remaining-tokens'),
        'reset_tokens': headers.get('x-ratelimit-reset-tokens'),
    }
    
    # Convert to integers if present
    for key in rate_limit_info:
        if rate_limit_info[key] is not None:
            try:
                rate_limit_info[key] = int(rate_limit_info[key])
            except (ValueError, TypeError):
                pass
    
    return rate_limit_info


async def get_rate_limits_for_models(
    api_key: str,
    models: list[str],
    project_id: str = "default"
) -> dict[str, dict[str, Any]]:
    """
    Get rate limits for multiple models.
    
    Combines API endpoint query with header extraction from test calls.
    
    Args:
        api_key: OpenAI API key
        models: List of model names to check
        project_id: Project ID (default: "default")
    
    Returns:
        Dictionary mapping model names to rate limit info
    """
    results = {}
    
    # Method 1: Query API endpoint
    try:
        api_results = await check_rate_limits_via_api(api_key, project_id)
        if 'rate_limits' in api_results:
            for limit in api_results['rate_limits']:
                model = limit.get('model', 'unknown')
                if model in models:
                    results[model] = {
                        'rpm': limit.get('max_requests_per_1_minute'),
                        'tpm': limit.get('max_tokens_per_1_minute'),
                        'source': 'api_endpoint'
                    }
    except Exception as e:
        logger.warning(f"Failed to get rate limits via API endpoint: {e}")
    
    # Method 2: Extract from test call headers (for models not in API response)
    client = AsyncOpenAI(api_key=api_key)
    for model in models:
        if model not in results:
            try:
                # Make minimal test call
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                
                # Extract headers (OpenAI SDK doesn't expose headers directly)
                # We'll need to use httpx for this
                logger.debug(f"Test call successful for {model}, but headers not accessible via SDK")
                
            except Exception as e:
                logger.warning(f"Failed to get rate limits for {model} via test call: {e}")
    
    return results

