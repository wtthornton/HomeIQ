"""
Data Generation Manager

Orchestrates multi-home generation with caching, parallelization, and validation.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import DataGenerationConfig

logger = logging.getLogger(__name__)


class DataGenerationManager:
    """
    Data generation manager for orchestrating multi-home generation.
    
    Features:
    - Parallel generation support
    - Caching mechanism (reuse generated homes)
    - Cache invalidation (when parameters change)
    - Progress tracking and reporting
    - Validation of generated data
    """

    def __init__(
        self,
        config: DataGenerationConfig | None = None,
        home_generator: Any | None = None  # HomeGenerator wrapper
    ):
        """
        Initialize data generation manager.
        
        Args:
            config: Data generation configuration
            home_generator: Home generator wrapper instance
        """
        self.config = config or DataGenerationConfig()
        self.home_generator = home_generator
        self.generation_stats: dict[str, Any] = {
            "total_generated": 0,
            "total_cached": 0,
            "total_failed": 0,
            "generation_times": []
        }
        
        logger.info("DataGenerationManager initialized")

    def _generate_cache_key(
        self,
        home_type: str,
        event_days: int,
        home_index: int
    ) -> str:
        """
        Generate cache key for home generation.
        
        Args:
            home_type: Home type
            event_days: Number of event days
            home_index: Home index
            
        Returns:
            Cache key string
        """
        key_data = f"{home_type}_{event_days}_{home_index}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get cache file path for key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cache file path
        """
        return self.config.cache_directory / f"{cache_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """
        Check if cache entry is valid.
        
        Args:
            cache_path: Cache file path
            
        Returns:
            True if cache is valid
        """
        if not cache_path.exists():
            return False
        
        # Check TTL
        file_age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            cache_path.stat().st_mtime, tz=timezone.utc
        )
        return file_age < timedelta(hours=self.config.cache_ttl_hours)

    async def _load_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """
        Load home from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached home data or None
        """
        if not self.config.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            # Use asyncio.to_thread for blocking I/O in async function
            def _load_file() -> dict[str, Any] | None:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            data = await asyncio.to_thread(_load_file)
            logger.debug(f"Loaded from cache: {cache_key}")
            return data
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache {cache_key}: {e}")
            return None

    async def _save_to_cache(
        self,
        cache_key: str,
        home_data: dict[str, Any]
    ) -> None:
        """
        Save home to cache.
        
        Args:
            cache_key: Cache key
            home_data: Home data to cache
        """
        if not self.config.cache_enabled:
            return
        
        try:
            cache_path = self._get_cache_path(cache_key)
            # Ensure directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use asyncio.to_thread for blocking I/O in async function
            def _save_file() -> None:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(home_data, f, indent=2)
            
            await asyncio.to_thread(_save_file)
            logger.debug(f"Saved to cache: {cache_key}")
        except (OSError, TypeError) as e:
            logger.warning(f"Failed to save cache {cache_key}: {e}")

    def _validate_home_data(self, home_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate generated home data.
        
        Args:
            home_data: Home data to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not self.config.validate_generated_data:
            return True, ""
        
        # Check required fields
        required_fields = ["home_id", "home_type", "devices", "events"]
        for field in required_fields:
            if field not in home_data:
                return False, f"Missing required field: {field}"
        
        # Check minimum devices
        devices = home_data.get("devices", [])
        if len(devices) < self.config.min_devices_per_home:
            return False, f"Too few devices: {len(devices)} < {self.config.min_devices_per_home}"
        
        # Check minimum events
        events = home_data.get("events", [])
        if len(events) < self.config.min_events_per_home:
            return False, f"Too few events: {len(events)} < {self.config.min_events_per_home}"
        
        return True, ""

    async def _generate_single_home(
        self,
        home_type: str,
        event_days: int,
        home_index: int
    ) -> dict[str, Any] | None:
        """
        Generate a single home (with caching).
        
        Args:
            home_type: Home type
            event_days: Number of event days
            home_index: Home index
            
        Returns:
            Generated home data or None if failed
        """
        cache_key = self._generate_cache_key(home_type, event_days, home_index)
        
        # Try cache first
        cached_data = await self._load_from_cache(cache_key)
        if cached_data:
            self.generation_stats["total_cached"] += 1
            logger.debug(f"Using cached home: {home_type} #{home_index}")
            return cached_data
        
        # Generate new home
        if not self.home_generator:
            raise ValueError("Home generator not set")
        
        start_time = time.time()
        try:
            home_data = await self.home_generator.generate_home(
                home_type=home_type,
                event_days=event_days,
                home_index=home_index
            )
            
            # Validate
            is_valid, error_msg = self._validate_home_data(home_data)
            if not is_valid:
                logger.error(f"Validation failed for {home_type} #{home_index}: {error_msg}")
                self.generation_stats["total_failed"] += 1
                return None
            
            # Save to cache
            await self._save_to_cache(cache_key, home_data)
            
            generation_time = time.time() - start_time
            self.generation_stats["total_generated"] += 1
            self.generation_stats["generation_times"].append(generation_time)
            
            logger.info(f"Generated home: {home_type} #{home_index} ({generation_time:.2f}s)")
            return home_data
            
        except Exception as e:
            logger.error(f"Failed to generate {home_type} #{home_index}: {e}")
            self.generation_stats["total_failed"] += 1
            return None

    async def generate_homes(
        self,
        home_count: int | None = None,
        event_days: int | None = None,
        home_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate multiple homes with parallelization.
        
        Args:
            home_count: Number of homes to generate (default: from config)
            event_days: Number of event days per home (default: from config)
            home_types: Home types to generate (default: from config)
            
        Returns:
            List of generated home data
        """
        home_count = home_count or self.config.default_home_count
        event_days = event_days or self.config.default_event_days
        home_types = home_types or self.config.home_types
        
        logger.info(f"Generating {home_count} homes (types: {home_types}, days: {event_days})")
        
        # Distribute homes across types
        homes_per_type = home_count // len(home_types)
        remainder = home_count % len(home_types)
        
        generation_tasks = []
        home_index = 0
        
        for home_type in home_types:
            count = homes_per_type + (1 if remainder > 0 else 0)
            remainder -= 1
            
            for i in range(count):
                task = self._generate_single_home(
                    home_type=home_type,
                    event_days=event_days,
                    home_index=home_index
                )
                generation_tasks.append(task)
                home_index += 1
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_parallel_generations)
        
        async def bounded_generate(task: Any) -> dict[str, Any] | None:
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[bounded_generate(task) for task in generation_tasks])
        
        # Filter out None results
        homes = [h for h in results if h is not None]
        
        logger.info(
            f"Generation complete: {len(homes)}/{home_count} homes "
            f"(cached: {self.generation_stats['total_cached']}, "
            f"failed: {self.generation_stats['total_failed']})"
        )
        
        return homes

    def get_progress_report(self) -> dict[str, Any]:
        """
        Get generation progress report.
        
        Returns:
            Progress report dictionary
        """
        avg_time = (
            sum(self.generation_stats["generation_times"]) / len(self.generation_stats["generation_times"])
            if self.generation_stats["generation_times"]
            else 0.0
        )
        
        return {
            "total_generated": self.generation_stats["total_generated"],
            "total_cached": self.generation_stats["total_cached"],
            "total_failed": self.generation_stats["total_failed"],
            "average_generation_time": avg_time,
            "cache_enabled": self.config.cache_enabled,
            "cache_directory": str(self.config.cache_directory)
        }

