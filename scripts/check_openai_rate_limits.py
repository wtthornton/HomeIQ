#!/usr/bin/env python3
"""
Check OpenAI Rate Limits

Queries OpenAI API to get actual rate limits for your API key and models.
Uses both API endpoint and response headers to determine limits.

IMPORTANT: Rate limit headers are ONLY in successful responses (200 OK), NOT in 429 errors.
The script will automatically retry with exponential backoff if rate limited.

Usage:
    python scripts/check_openai_rate_limits.py
    python scripts/check_openai_rate_limits.py --project-id YOUR_PROJECT_ID
    python scripts/check_openai_rate_limits.py --method headers --models gpt-4o-mini
"""

import asyncio
import json
import logging
import os
import random
import sys
from typing import Any

import httpx

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, '..', 'services', 'ai-automation-service', 'src')
sys.path.insert(0, src_path)

try:
    from config import settings
except ImportError:
    # Fallback: use environment variable
    import os
    class Settings:
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
    settings = Settings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def check_rate_limits_via_api(api_key: str, project_id: str = "default") -> dict[str, Any]:
    """
    Check rate limits via OpenAI API endpoint.
    
    Note: This endpoint may require organization-level authentication or a valid project ID.
    If you get a 401 error, you may need to:
    1. Get your organization ID from https://platform.openai.com/account/org-settings
    2. Use the organization-level endpoint instead
    3. Or check your API key permissions
    
    Args:
        api_key: OpenAI API key
        project_id: Project ID (default: "default", or use your actual project ID)
    
    Returns:
        Dictionary with rate limits per model
    """
    # Try project-level endpoint first
    url = f"https://api.openai.com/v1/organization/projects/{project_id}/rate_limits"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(
                f"⚠️ Authentication failed (401) for project '{project_id}'. "
                f"This endpoint may require organization-level access or a valid project ID."
            )
            logger.warning(
                "   To fix: Get your organization ID from https://platform.openai.com/account/org-settings"
            )
            logger.warning(
                "   Or use response headers method instead (--method headers)"
            )
            raise
        elif e.response.status_code == 404:
            logger.warning(f"Project '{project_id}' not found. Trying organization-level endpoint...")
            # Try organization-level endpoint (requires organization ID in URL or header)
            # Note: This may also require organization-level authentication
            url = "https://api.openai.com/v1/organization/rate_limits"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e2:
                if e2.response.status_code == 401:
                    logger.error(
                        "❌ Organization-level endpoint also requires authentication. "
                        "Use --method headers to check rate limits via response headers instead."
                    )
                raise
            except Exception as e2:
                logger.error(f"Failed to get rate limits: {e2}")
                raise
        else:
            logger.error(f"Failed to get rate limits: {e}")
            raise
    except Exception as e:
        logger.error(f"Error checking rate limits: {e}")
        raise


async def check_rate_limits_via_test_call(api_key: str, model: str = "gpt-5.1-mini", max_retries: int = 5) -> dict[str, Any]:
    """
    Check rate limits by making a test API call and reading response headers.
    
    IMPORTANT: Rate limit headers are ONLY included in successful responses (200 OK),
    NOT in 429 error responses. This function will retry with exponential backoff
    if it hits a rate limit, waiting for a successful response to extract headers.
    
    Args:
        api_key: OpenAI API key
        model: Model to test (default: gpt-5.1-mini)
        max_retries: Maximum number of retries if rate limited (default: 5)
    
    Returns:
        Dictionary with rate limit info from headers
    """
    url = "https://api.openai.com/v1/chat/completions"
    request_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5  # Minimal tokens for test
    }
    
    # Validate API key format
    if not api_key.startswith('sk-'):
        logger.warning(f"⚠️ API key for model '{model}' doesn't start with 'sk-' - may not be valid")
    
    # Retry logic with exponential backoff for 429 errors
    for attempt in range(max_retries):
        try:
            logger.info(f"   Making API call for model: '{model}' (attempt {attempt + 1}/{max_retries})")
            logger.debug(f"   API URL: {url}")
            logger.debug(f"   Payload model: {payload['model']}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=request_headers, json=payload)
                
                # Success! Extract headers (headers are only in successful responses)
                if response.status_code == 200:
                    response_headers = response.headers
                    logger.info(f"   ✅ Successfully retrieved rate limit headers for {model}")
                    logger.info(f"   Response headers containing 'ratelimit':")
                    for key, value in sorted(response_headers.items()):
                        if 'ratelimit' in key.lower() or 'rate-limit' in key.lower():
                            logger.info(f"      {key}: {value}")
                    
                    # Extract all rate limit headers
                    all_ratelimit_headers = {
                        k: v for k, v in response_headers.items() 
                        if 'ratelimit' in k.lower() or 'rate-limit' in k.lower()
                    }
                    
                    # Check reset time to determine if it's RPM or RPD
                    reset_requests = response_headers.get('x-ratelimit-reset-requests')
                    limit_type = 'unknown'
                    if reset_requests:
                        try:
                            reset_seconds = int(reset_requests)
                            # If reset is > 3600 seconds (1 hour), likely RPD (daily limit)
                            # If reset is < 3600 seconds, likely RPM (per-minute limit)
                            if reset_seconds > 3600:
                                limit_type = 'RPD'  # Requests Per Day
                            else:
                                limit_type = 'RPM'  # Requests Per Minute
                        except (ValueError, TypeError):
                            pass
                    
                    rate_limit_info = {
                        'model': model,
                        'limit_requests': response_headers.get('x-ratelimit-limit-requests'),
                        'remaining_requests': response_headers.get('x-ratelimit-remaining-requests'),
                        'reset_requests': reset_requests,
                        'limit_type': limit_type,  # NEW: RPM or RPD
                        'limit_tokens': response_headers.get('x-ratelimit-limit-tokens'),
                        'remaining_tokens': response_headers.get('x-ratelimit-remaining-tokens'),
                        'reset_tokens': response_headers.get('x-ratelimit-reset-tokens'),
                        'all_ratelimit_headers': all_ratelimit_headers
                    }
                    
                    # Convert to integers if present
                    for key in rate_limit_info:
                        if rate_limit_info[key] is not None and key != 'model' and key != 'all_ratelimit_headers':
                            try:
                                rate_limit_info[key] = int(rate_limit_info[key])
                            except (ValueError, TypeError):
                                pass
                    
                    return rate_limit_info
                
                # Handle 429 Rate Limit Error
                elif response.status_code == 429:
                    # Check for retry-after header (OpenAI's recommended wait time)
                    retry_after = response.headers.get('retry-after')
                    base_wait_time = 60  # Default 60 seconds
                    
                    # Determine if this is RPM or RPD limit based on retry-after
                    limit_type = 'RPM'  # Default assumption
                    if retry_after:
                        try:
                            retry_seconds = int(retry_after)
                            base_wait_time = retry_seconds
                            # If retry-after is > 3600 seconds (1 hour), likely RPD
                            if retry_seconds > 3600:
                                limit_type = 'RPD'  # Requests Per Day
                                logger.warning(
                                    f"   ⚠️ Daily limit (RPD) hit - retry-after: {retry_seconds}s "
                                    f"({retry_seconds/3600:.1f} hours)"
                                )
                            else:
                                limit_type = 'RPM'  # Requests Per Minute
                        except (ValueError, TypeError):
                            pass
                    
                    # Also check error response body for more details
                    try:
                        error_body = response.json()
                        error_message = error_body.get('error', {}).get('message', '')
                        if 'day' in error_message.lower() or 'daily' in error_message.lower():
                            limit_type = 'RPD'
                            logger.warning(f"   ⚠️ Error message indicates daily limit: {error_message}")
                    except (json.JSONDecodeError, KeyError):
                        pass
                    
                    # Exponential backoff with jitter (OpenAI best practice)
                    # Formula: base_wait * (2^attempt) + random_jitter
                    # Jitter prevents synchronized retries across multiple clients
                    exponential_multiplier = 2 ** attempt
                    wait_time = base_wait_time * exponential_multiplier
                    
                    # Add jitter: random 0-10% of wait time
                    jitter = random.uniform(0, wait_time * 0.1)
                    wait_time = int(wait_time + jitter)
                    
                    # Cap maximum wait time at 5 minutes (300 seconds)
                    wait_time = min(wait_time, 300)
                    
                    if attempt < max_retries - 1:
                        # Log the actual model we're checking (not from error response)
                        logger.warning(
                            f"   ⚠️ Rate limit hit (429) for model '{model}' - {limit_type} limit. "
                            f"Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})..."
                        )
                        if limit_type == 'RPD':
                            logger.warning(
                                f"   ⚠️ Daily limit (RPD) exceeded. This will reset at midnight UTC or after 24 hours."
                            )
                        else:
                            logger.warning(
                                f"   Note: Rate limit headers are only in successful responses, "
                                f"not in 429 errors. Using exponential backoff with jitter..."
                            )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise httpx.HTTPStatusError(
                            f"Rate limit exceeded after {max_retries} attempts",
                            request=response.request,
                            response=response
                        )
                
                # Other HTTP errors
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Already handled above, but catch here for safety
                continue
            else:
                logger.error(f"Failed to make test call: {e}")
                raise
        except Exception as e:
            logger.error(f"Error checking rate limits via test call: {e}")
            raise
    
    # Should not reach here, but handle edge case
    raise Exception(f"Failed to get rate limits after {max_retries} attempts")


async def main():
    """Main function to check rate limits."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check OpenAI rate limits")
    parser.add_argument(
        '--project-id',
        type=str,
        default="default",
        help='OpenAI project ID (default: "default")'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API key (default: from settings)'
    )
    parser.add_argument(
        '--models',
        type=str,
        nargs='+',
        default=['gpt-5.1', 'gpt-5.1-mini'],
        help='Models to check (default: gpt-5.1 gpt-5.1-mini)'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['api', 'headers', 'both'],
        default='both',
        help='Method to use: api, headers, or both (default: both)'
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or settings.openai_api_key
    if not api_key:
        logger.error("❌ OpenAI API key not found. Set OPENAI_API_KEY environment variable or use --api-key")
        return 1
    
    # Validate API key format (OpenAI keys start with 'sk-')
    if not api_key.startswith('sk-'):
        logger.warning("⚠️ API key doesn't start with 'sk-' - this may not be a valid OpenAI API key")
    
    # Log API key info (masked for security)
    api_key_preview = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
    logger.info("🔍 Checking OpenAI rate limits...")
    logger.info(f"   API Key: {api_key_preview}")
    logger.info(f"   Project ID: {args.project_id}")
    logger.info(f"   Models: {', '.join(args.models)}")
    logger.info(f"   Method: {args.method}")
    logger.info(f"   API Endpoint: https://api.openai.com/v1/chat/completions")
    logger.info("")
    
    results = {}
    
    # Method 1: API Endpoint
    if args.method in ['api', 'both']:
        logger.info("📡 Method 1: Querying rate limits via API endpoint...")
        try:
            api_results = await check_rate_limits_via_api(api_key, args.project_id)
            results['api_endpoint'] = api_results
            logger.info("✅ Successfully retrieved rate limits via API")
            
            # Print results
            if 'rate_limits' in api_results:
                logger.info("\n📊 Rate Limits (API Endpoint):")
                for limit in api_results.get('rate_limits', []):
                    model = limit.get('model', 'unknown')
                    rpm = limit.get('max_requests_per_1_minute', 'N/A')
                    tpm = limit.get('max_tokens_per_1_minute', 'N/A')
                    logger.info(f"   {model}:")
                    logger.info(f"     - Requests/min: {rpm:,}" if isinstance(rpm, int) else f"     - Requests/min: {rpm}")
                    logger.info(f"     - Tokens/min: {tpm:,}" if isinstance(tpm, int) else f"     - Tokens/min: {tpm}")
            else:
                logger.info(f"   Response: {json.dumps(api_results, indent=2)}")
        except Exception as e:
            logger.error(f"❌ Failed to get rate limits via API: {e}")
            if args.method == 'api':
                return 1
    
    logger.info("")
    
    # Method 2: Response Headers
    if args.method in ['headers', 'both']:
        logger.info("📡 Method 2: Checking rate limits via response headers...")
        logger.info("   ⚠️ IMPORTANT: Headers are only in successful responses (200 OK), not in 429 errors.")
        logger.info("   If rate limited, script will wait and retry automatically.")
        logger.info("")
        for model in args.models:
            try:
                header_results = await check_rate_limits_via_test_call(api_key, model)
                results[f'headers_{model}'] = header_results
                logger.info(f"✅ Successfully retrieved rate limits for {model}")
                
                logger.info(f"\n📊 Rate Limits ({model} - Response Headers):")
                limit_type = header_results.get('limit_type', 'RPM')
                limit_label = 'Requests/day' if limit_type == 'RPD' else 'Requests/min'
                logger.info(f"   Limit Type: {limit_type}")
                logger.info(f"   {limit_label} limit: {header_results.get('limit_requests', 'N/A'):,}" 
                          if isinstance(header_results.get('limit_requests'), int) 
                          else f"   {limit_label} limit: {header_results.get('limit_requests', 'N/A')}")
                logger.info(f"   {limit_label} remaining: {header_results.get('remaining_requests', 'N/A'):,}"
                          if isinstance(header_results.get('remaining_requests'), int)
                          else f"   {limit_label} remaining: {header_results.get('remaining_requests', 'N/A')}")
                reset_seconds = header_results.get('reset_requests')
                if reset_seconds:
                    if isinstance(reset_seconds, int):
                        if reset_seconds > 3600:
                            reset_hours = reset_seconds / 3600
                            logger.info(f"   Requests reset in: {reset_hours:.1f} hours ({reset_seconds} seconds)")
                        else:
                            logger.info(f"   Requests reset in: {reset_seconds} seconds")
                    else:
                        logger.info(f"   Requests reset in: {reset_seconds} seconds")
                else:
                    logger.info(f"   Requests reset in: N/A")
                logger.info(f"   Tokens/min limit: {header_results.get('limit_tokens', 'N/A'):,}"
                          if isinstance(header_results.get('limit_tokens'), int)
                          else f"   Tokens/min limit: {header_results.get('limit_tokens', 'N/A')}")
                logger.info(f"   Tokens/min remaining: {header_results.get('remaining_tokens', 'N/A'):,}"
                          if isinstance(header_results.get('remaining_tokens'), int)
                          else f"   Tokens/min remaining: {header_results.get('remaining_tokens', 'N/A')}")
                logger.info(f"   Tokens reset in: {header_results.get('reset_tokens', 'N/A')} seconds")
            except Exception as e:
                logger.error(f"❌ Failed to get rate limits for {model}: {e}")
                if args.method == 'headers':
                    return 1
    
    logger.info("")
    logger.info("✅ Rate limit check complete!")
    
    # Save results to file
    output_file = "openai_rate_limits.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"📄 Results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
