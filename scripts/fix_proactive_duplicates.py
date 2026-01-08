#!/usr/bin/env python3
"""
Fix duplicate proactive suggestions and verify temperature data.

This script:
1. Lists all suggestions via API
2. Identifies duplicate suggestions (same prompt text)
3. Deletes duplicates, keeping the oldest one (or highest quality if same time)
4. Verifies temperature data matches current weather API

Usage:
    python scripts/fix_proactive_duplicates.py [--yes]
    
    --yes: Delete duplicates without prompting

Refactored: January 2026
- Single async entry point (no multiple asyncio.run() calls)
- Connection pooling with httpx.AsyncClient context manager
- Retry logic for network operations
- Proper error handling and logging
"""
import argparse
import asyncio
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# API Configuration
DEFAULT_PROACTIVE_API_BASE = "http://localhost:8031/api/v1/suggestions"
DEFAULT_WEATHER_API_URL = "http://localhost:8009/current-weather"


@dataclass
class DuplicateAnalysis:
    """Results of duplicate analysis."""
    
    total_suggestions: int = 0
    duplicate_prompts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    total_duplicates: int = 0
    
    @property
    def has_duplicates(self) -> bool:
        return self.total_duplicates > 0


@dataclass
class TemperatureAnalysis:
    """Results of temperature analysis."""
    
    current_temp: float | None = None
    location: str = "Unknown"
    suggestion_temps: list[float] = field(default_factory=list)
    avg_suggestion_temp: float | None = None
    temp_difference: float | None = None
    has_significant_difference: bool = False


class ProactiveDuplicateFixer:
    """
    Fix duplicate proactive suggestions with proper async handling.
    
    Features:
    - Single async entry point (no multiple event loops)
    - Connection pooling via shared httpx.AsyncClient
    - Retry logic for network operations
    - Structured result objects
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 1.0
    
    def __init__(
        self,
        proactive_api_base: str = DEFAULT_PROACTIVE_API_BASE,
        weather_api_url: str = DEFAULT_WEATHER_API_URL,
        timeout: float = 30.0
    ):
        """
        Initialize the fixer.
        
        Args:
            proactive_api_base: Base URL for proactive suggestions API
            weather_api_url: URL for weather API
            timeout: HTTP timeout in seconds
        """
        self.proactive_api_base = proactive_api_base
        self.weather_api_url = weather_api_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self) -> "ProactiveDuplicateFixer":
        """Enter async context, create shared HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context, close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        last_error: Exception | None = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_SECONDS * (attempt + 1)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx, 5xx)
                raise
        
        raise last_error or httpx.RequestError(f"Request failed after {self.MAX_RETRIES} attempts")
    
    async def fetch_all_suggestions(self) -> list[dict[str, Any]]:
        """
        Fetch all suggestions from the API with pagination.
        
        Returns:
            List of suggestion dictionaries
        """
        suggestions: list[dict[str, Any]] = []
        offset = 0
        limit = 100
        
        while True:
            try:
                response = await self._request_with_retry(
                    "GET",
                    self.proactive_api_base,
                    params={"limit": limit, "offset": offset}
                )
                data = response.json()
                
                if not isinstance(data, dict):
                    logger.warning(f"Unexpected response format: expected dict, got {type(data)}")
                    break
                
                batch = data.get("suggestions", [])
                if not isinstance(batch, list):
                    logger.warning(f"Unexpected suggestions format: expected list, got {type(batch)}")
                    break
                
                if not batch:
                    break
                
                suggestions.extend(batch)
                offset += limit
                
                # If we got fewer than limit, we're done
                if len(batch) < limit:
                    break
                    
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch suggestions at offset {offset}: {e}")
                raise
        
        return suggestions
    
    async def get_current_weather(self) -> dict[str, Any] | None:
        """
        Get current weather from API.
        
        Returns:
            Weather data dictionary or None if unavailable
        """
        try:
            response = await self._request_with_retry("GET", self.weather_api_url)
            return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch weather API: {e}")
            return None
    
    async def delete_suggestion(self, suggestion_id: str) -> bool:
        """
        Delete a suggestion via API.
        
        Args:
            suggestion_id: ID of suggestion to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = await self._request_with_retry(
                "DELETE",
                f"{self.proactive_api_base}/{suggestion_id}"
            )
            return response.status_code == 200
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to delete {suggestion_id}: {e.response.status_code} {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error deleting {suggestion_id}: {e}")
            return False
    
    def find_duplicates(self, suggestions: list[dict[str, Any]]) -> DuplicateAnalysis:
        """
        Find duplicate suggestions by prompt text.
        
        Args:
            suggestions: List of suggestion dictionaries
            
        Returns:
            DuplicateAnalysis with results
        """
        prompt_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        for suggestion in suggestions:
            prompt_text = suggestion.get("prompt", "").strip()
            if prompt_text:
                prompt_map[prompt_text].append(suggestion)
        
        # Filter to only duplicates (more than one)
        duplicates = {prompt: sugs for prompt, sugs in prompt_map.items() if len(sugs) > 1}
        total_duplicates = sum(len(sugs) - 1 for sugs in duplicates.values())
        
        return DuplicateAnalysis(
            total_suggestions=len(suggestions),
            duplicate_prompts=duplicates,
            total_duplicates=total_duplicates
        )
    
    def analyze_temperature_data(
        self,
        suggestions: list[dict[str, Any]],
        current_weather: dict[str, Any] | None
    ) -> TemperatureAnalysis:
        """
        Analyze temperature data in suggestions vs current weather.
        
        Args:
            suggestions: List of suggestion dictionaries
            current_weather: Current weather data or None
            
        Returns:
            TemperatureAnalysis with results
        """
        analysis = TemperatureAnalysis()
        
        if not current_weather:
            return analysis
        
        analysis.current_temp = current_weather.get("temperature")
        analysis.location = current_weather.get("location", "Unknown")
        
        if analysis.current_temp is None:
            return analysis
        
        # Extract temperatures from weather suggestions
        weather_suggestions = [s for s in suggestions if s.get("context_type") == "weather"]
        
        for suggestion in weather_suggestions:
            temp = self._extract_temperature(suggestion)
            if temp is not None:
                analysis.suggestion_temps.append(temp)
        
        if analysis.suggestion_temps:
            analysis.avg_suggestion_temp = sum(analysis.suggestion_temps) / len(analysis.suggestion_temps)
            analysis.temp_difference = abs(analysis.avg_suggestion_temp - analysis.current_temp)
            analysis.has_significant_difference = analysis.temp_difference > 5.0
        
        return analysis
    
    def _extract_temperature(self, suggestion: dict[str, Any]) -> float | None:
        """Extract temperature from a suggestion."""
        # Try prompt_metadata
        prompt_metadata = suggestion.get("prompt_metadata", {})
        if prompt_metadata:
            temp = prompt_metadata.get("temperature")
            if temp is not None:
                return float(temp)
        
        # Try context_metadata
        context_metadata = suggestion.get("context_metadata", {})
        weather_data = context_metadata.get("weather", {})
        if isinstance(weather_data, dict):
            current = weather_data.get("current", {})
            if isinstance(current, dict):
                temp = current.get("temperature")
                if temp is not None:
                    return float(temp)
        
        # Try to extract from prompt text
        prompt = suggestion.get("prompt", "")
        match = re.search(r"(\d+\.?\d*)\s*°F", prompt)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def select_suggestions_for_deletion(
        self,
        duplicates: dict[str, list[dict[str, Any]]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Select which suggestions to keep and which to delete.
        
        Args:
            duplicates: Dictionary mapping prompt text to list of duplicate suggestions
            
        Returns:
            Tuple of (suggestions_to_keep, suggestions_to_delete)
        """
        to_keep: list[dict[str, Any]] = []
        to_delete: list[dict[str, Any]] = []
        
        for prompt_text, suggestion_list in duplicates.items():
            if not suggestion_list:
                continue
            
            # Sort by created_at (oldest first), then by quality_score (highest first)
            sorted_suggestions = sorted(
                suggestion_list,
                key=lambda s: (
                    s.get("created_at") or "",
                    -s.get("quality_score", 0.0)
                )
            )
            
            # Keep the first one (oldest, or highest quality if same time)
            to_keep.append(sorted_suggestions[0])
            to_delete.extend(sorted_suggestions[1:])
        
        return to_keep, to_delete
    
    async def delete_duplicates(
        self,
        to_delete: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """
        Delete duplicate suggestions.
        
        Args:
            to_delete: List of suggestions to delete
            
        Returns:
            Tuple of (successful_deletes, failed_deletes)
        """
        successful = 0
        failed = 0
        
        for suggestion in to_delete:
            suggestion_id = suggestion.get("id")
            if not suggestion_id:
                logger.warning("Skipping suggestion without id field")
                failed += 1
                continue
            
            if await self.delete_suggestion(suggestion_id):
                successful += 1
            else:
                failed += 1
        
        return successful, failed


def print_analysis_results(
    analysis: DuplicateAnalysis,
    temp_analysis: TemperatureAnalysis
) -> None:
    """Print analysis results to console."""
    print(f"   Found {analysis.total_suggestions} total suggestions")
    
    # Temperature analysis
    if temp_analysis.current_temp is not None:
        print("\nTemperature Analysis:")
        print(f"   Current weather API temperature: {temp_analysis.current_temp}F")
        print(f"   Location: {temp_analysis.location}")
        
        if temp_analysis.suggestion_temps:
            print(f"\n   Found {len(temp_analysis.suggestion_temps)} weather suggestions with temperature")
            print(f"   Average suggestion temperature: {temp_analysis.avg_suggestion_temp:.2f}F")
            print(f"   Difference from current: {temp_analysis.temp_difference:.2f}F")
            
            if temp_analysis.has_significant_difference:
                print("   [WARN] WARNING: Suggestion temperatures differ significantly from current weather!")
                print("      This suggests suggestions were created at different times or there's a data issue.")
    else:
        print("\n[WARN] Cannot analyze temperature: Weather API unavailable or no temperature data")
    
    # Duplicate analysis
    print("\nSearching for duplicates...")
    if not analysis.has_duplicates:
        print("[OK] No duplicate suggestions found")
    else:
        print(f"   Found {len(analysis.duplicate_prompts)} unique prompts with duplicates")
        print(f"   Total duplicate suggestions: {analysis.total_duplicates}")


def print_duplicates(duplicates: dict[str, list[dict[str, Any]]]) -> None:
    """Print duplicate details to console."""
    print("\nDuplicate prompts found:")
    for prompt_text, sugs in duplicates.items():
        print(f"\n   Prompt: {prompt_text[:80]}...")
        for sug in sugs:
            sug_id = sug.get("id", "")
            created_at = sug.get("created_at", "Unknown")
            quality = sug.get("quality_score", 0.0)
            status = sug.get("status", "unknown")
            id_display = sug_id[:8] if sug_id else "N/A"
            print(f"      - {id_display}...: status={status}, quality={quality}, created={created_at}")


async def async_main(auto_confirm: bool = False) -> int:
    """
    Async main function - single entry point for all async operations.
    
    Args:
        auto_confirm: If True, delete duplicates without prompting
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print("=" * 60)
    print("FIX PROACTIVE SUGGESTION DUPLICATES")
    print("=" * 60)
    print()
    
    async with ProactiveDuplicateFixer() as fixer:
        # Get current weather for comparison
        print("Fetching current weather...")
        current_weather = await fixer.get_current_weather()
        
        # Fetch all suggestions
        print("\nFetching suggestions from API...")
        try:
            suggestions = await fixer.fetch_all_suggestions()
        except Exception as e:
            print(f"[ERROR] ERROR: Failed to fetch suggestions: {e}")
            return 1
        
        # Analyze
        temp_analysis = fixer.analyze_temperature_data(suggestions, current_weather)
        dup_analysis = fixer.find_duplicates(suggestions)
        
        # Print results
        print_analysis_results(dup_analysis, temp_analysis)
        
        if not dup_analysis.has_duplicates:
            return 0
        
        # Show duplicates
        print_duplicates(dup_analysis.duplicate_prompts)
        
        # Confirm deletion
        if not auto_confirm:
            print("\n" + "=" * 60)
            try:
                response = input("Delete duplicates? (keep oldest/highest quality) [y/N]: ")
            except EOFError:
                response = "n"
            
            if response.lower() not in ['y', 'yes']:
                print("\n[SKIP] Deletion cancelled")
                return 0
        else:
            print("\n" + "=" * 60)
            print("Auto-deleting duplicates (--yes flag)")
        
        # Delete duplicates
        print("\nDeleting duplicates...")
        to_keep, to_delete = fixer.select_suggestions_for_deletion(dup_analysis.duplicate_prompts)
        
        for suggestion in to_keep:
            sug_id = suggestion.get("id", "")
            created_at = suggestion.get("created_at", "Unknown")
            quality = suggestion.get("quality_score", 0.0)
            id_display = sug_id[:8] if sug_id else "N/A"
            print(f"   Keeping: {id_display}... (created: {created_at}, quality: {quality})")
        
        successful, failed = await fixer.delete_duplicates(to_delete)
        
        print(f"\n[OK] Successfully deleted {successful} duplicate suggestions")
        if failed > 0:
            print(f"[WARN] Failed to delete {failed} suggestions")
        
        return 0 if failed == 0 else 1


def main() -> int:
    """Main function - parses args and runs async main."""
    parser = argparse.ArgumentParser(description="Fix duplicate proactive suggestions")
    parser.add_argument("--yes", "-y", action="store_true", help="Delete duplicates without prompting")
    args = parser.parse_args()
    
    return asyncio.run(async_main(auto_confirm=args.yes))


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[ERROR] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
