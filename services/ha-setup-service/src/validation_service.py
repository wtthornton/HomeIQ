"""
Home Assistant Configuration Validation Service

Validates HA configuration and provides suggestions for fixes.
Epic 32: Home Assistant Configuration Validation & Suggestions
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from pydantic import BaseModel, Field

from .config import get_settings
from .suggestion_engine import SuggestionEngine

settings = get_settings()
logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    """A single validation issue with suggestions"""
    entity_id: str
    category: str
    current_area: str | None = None
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    device_id: str | None = None
    entity_name: str | None = None
    confidence: float = 0.0


class ValidationSummary(BaseModel):
    """Summary of validation results"""
    total_issues: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    scan_timestamp: datetime = Field(default_factory=datetime.now)
    ha_version: str | None = None


class ValidationResult(BaseModel):
    """Complete validation result"""
    summary: ValidationSummary
    issues: list[ValidationIssue] = Field(default_factory=list)


class ValidationService:
    """
    Service for validating Home Assistant configuration
    
    Detects:
    - Missing area assignments
    - Incorrect area assignments
    - Provides smart suggestions based on entity names
    """
    
    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.suggestion_engine = SuggestionEngine()
        
        # Cache for validation results (5 minute TTL)
        self._cache: dict[str, tuple[datetime, ValidationResult]] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_lock = asyncio.Lock()
        
    async def validate_ha_config(
        self,
        category: str | None = None,
        min_confidence: float = 0.0,
        use_cache: bool = True
    ) -> ValidationResult:
        """
        Validate Home Assistant configuration
        
        Args:
            category: Optional filter by issue category
            min_confidence: Minimum confidence score (0-100)
            use_cache: Whether to use cached results (default: True)
            
        Returns:
            ValidationResult with issues and suggestions
        """
        try:
            # Check cache first (only if no filters applied)
            cache_key = f"validation:{category or 'all'}:{min_confidence}"
            if use_cache and not category and min_confidence == 0:
                async with self._cache_lock:
                    if cache_key in self._cache:
                        cached_time, cached_result = self._cache[cache_key]
                        if datetime.now() - cached_time < self._cache_ttl:
                            logger.debug("Returning cached validation results")
                            return cached_result
                        else:
                            # Cache expired, remove it
                            del self._cache[cache_key]
            
            logger.info("Starting HA configuration validation...")
            
            # Fetch entities and areas from HA
            entities, areas, ha_version = await self._fetch_ha_data()
            
            logger.info(f"Fetched {len(entities)} entities and {len(areas)} areas")
            
            # Detect issues
            issues = await self._detect_issues(entities, areas)
            
            # Filter by category if specified
            if category:
                issues = [i for i in issues if i.category == category]
            
            # Filter by confidence
            if min_confidence > 0:
                filtered_issues = []
                for issue in issues:
                    # Keep issue if any suggestion meets confidence threshold
                    if issue.suggestions:
                        max_confidence = max(s.get("confidence", 0) for s in issue.suggestions)
                        if max_confidence >= min_confidence:
                            filtered_issues.append(issue)
                    elif issue.confidence >= min_confidence:
                        filtered_issues.append(issue)
                issues = filtered_issues
            
            # Generate summary
            summary = self._generate_summary(issues, ha_version)
            
            logger.info(f"Validation complete: {summary.total_issues} issues found")
            
            result = ValidationResult(
                summary=summary,
                issues=issues
            )
            
            # Cache result (only if no filters applied)
            if use_cache and not category and min_confidence == 0:
                async with self._cache_lock:
                    self._cache[cache_key] = (datetime.now(), result)
                    # Clean up old cache entries
                    now = datetime.now()
                    expired_keys = [
                        k for k, (t, _) in self._cache.items()
                        if now - t >= self._cache_ttl
                    ]
                    for k in expired_keys:
                        del self._cache[k]
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            raise
    
    def clear_cache(self):
        """Clear validation cache"""
        self._cache.clear()
        logger.info("Validation cache cleared")
    
    async def _fetch_ha_data(self) -> tuple[list[dict], list[dict], str]:
        """Fetch entities and areas from Home Assistant"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            
            # Fetch entities from entity registry
            async with session.get(
                f"{self.ha_url}/api/config/entity_registry/list",
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    entities = await response.json()
                else:
                    logger.warning(f"Entity registry API returned {response.status}, using states API")
                    # Fallback to states API
                    async with session.get(
                        f"{self.ha_url}/api/states",
                        headers=headers,
                        timeout=self.timeout
                    ) as states_response:
                        if states_response.status == 200:
                            states = await states_response.json()
                            entities = [
                                {
                                    "entity_id": s.get("entity_id"),
                                    "name": s.get("attributes", {}).get("friendly_name"),
                                    "area_id": s.get("attributes", {}).get("area_id"),
                                    "device_id": s.get("attributes", {}).get("device_id")
                                }
                                for s in states
                            ]
                        else:
                            raise Exception(f"Failed to fetch entities: {states_response.status}")
            
            # Fetch areas
            async with session.get(
                f"{self.ha_url}/api/config/area_registry/list",
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    areas = await response.json()
                else:
                    logger.warning(f"Area registry API returned {response.status}")
                    areas = []
            
            # Get HA version
            ha_version = None
            try:
                async with session.get(
                    f"{self.ha_url}/api/config",
                    headers=headers,
                    timeout=self.timeout
                ) as config_response:
                    if config_response.status == 200:
                        config = await config_response.json()
                        ha_version = config.get("version")
            except Exception as e:
                logger.warning(f"Could not fetch HA version: {e}")
            
            return entities, areas, ha_version
    
    async def _detect_issues(
        self,
        entities: list[dict],
        areas: list[dict]
    ) -> list[ValidationIssue]:
        """Detect validation issues in entities"""
        issues = []
        
        # Create area lookup
        area_map = {area.get("area_id"): area.get("name") for area in areas}
        area_ids = list(area_map.keys())
        
        for entity in entities:
            entity_id = entity.get("entity_id")
            if not entity_id:
                continue
            
            current_area_id = entity.get("area_id")
            entity_name = entity.get("name") or entity_id
            device_id = entity.get("device_id")
            
            # Check for missing area assignment
            if not current_area_id:
                # Generate suggestions
                suggestions = await self.suggestion_engine.suggest_area(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    areas=areas
                )
                
                if suggestions:
                    issues.append(ValidationIssue(
                        entity_id=entity_id,
                        category="missing_area_assignment",
                        current_area=None,
                        suggestions=suggestions,
                        device_id=device_id,
                        entity_name=entity_name,
                        confidence=max(s.get("confidence", 0) for s in suggestions) if suggestions else 0
                    ))
            
            # Check for incorrect area assignment (entity name suggests different area)
            elif current_area_id:
                suggestions = await self.suggestion_engine.suggest_area(
                    entity_id=entity_id,
                    entity_name=entity_name,
                    areas=areas
                )
                
                # If top suggestion is different from current, flag as incorrect
                if suggestions and suggestions[0].get("area_id") != current_area_id:
                    top_suggestion = suggestions[0]
                    # Only flag if confidence is high (>= 80%)
                    if top_suggestion.get("confidence", 0) >= 80:
                        issues.append(ValidationIssue(
                            entity_id=entity_id,
                            category="incorrect_area_assignment",
                            current_area=current_area_id,
                            suggestions=[top_suggestion],
                            device_id=device_id,
                            entity_name=entity_name,
                            confidence=top_suggestion.get("confidence", 0)
                        ))
        
        return issues
    
    def _generate_summary(
        self,
        issues: list[ValidationIssue],
        ha_version: str | None
    ) -> ValidationSummary:
        """Generate summary statistics"""
        by_category = {}
        for issue in issues:
            by_category[issue.category] = by_category.get(issue.category, 0) + 1
        
        return ValidationSummary(
            total_issues=len(issues),
            by_category=by_category,
            scan_timestamp=datetime.now(),
            ha_version=ha_version
        )
    
    async def apply_fix(
        self,
        entity_id: str,
        area_id: str
    ) -> dict[str, Any]:
        """
        Apply area assignment fix to Home Assistant
        
        Args:
            entity_id: Entity ID to update
            area_id: Area ID to assign
            
        Returns:
            Success response with details
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                
                # Update entity registry
                async with session.post(
                    f"{self.ha_url}/api/config/entity_registry/update/{entity_id}",
                    headers=headers,
                    json={"area_id": area_id},
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Successfully updated {entity_id} to area {area_id}")
                        return {
                            "success": True,
                            "entity_id": entity_id,
                            "area_id": area_id,
                            "applied_at": datetime.now().isoformat(),
                            "result": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to update entity: {response.status} - {error_text}")
                        raise Exception(f"HA API returned {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Error applying fix: {e}", exc_info=True)
            raise
    
    async def apply_bulk_fixes(
        self,
        fixes: list[dict[str, str]]
    ) -> dict[str, Any]:
        """
        Apply multiple area assignment fixes
        
        Args:
            fixes: List of dicts with entity_id and area_id
            
        Returns:
            Summary of applied fixes
        """
        results = []
        applied = 0
        failed = 0
        
        for fix in fixes:
            entity_id = fix.get("entity_id")
            area_id = fix.get("area_id")
            
            if not entity_id or not area_id:
                results.append({
                    "entity_id": entity_id or "unknown",
                    "success": False,
                    "error": "Missing entity_id or area_id"
                })
                failed += 1
                continue
            
            try:
                await self.apply_fix(entity_id, area_id)
                results.append({
                    "entity_id": entity_id,
                    "success": True
                })
                applied += 1
            except Exception as e:
                logger.error(f"Failed to apply fix for {entity_id}: {e}")
                results.append({
                    "entity_id": entity_id,
                    "success": False,
                    "error": str(e)
                })
                failed += 1
        
        return {
            "success": True,
            "applied": applied,
            "failed": failed,
            "results": results
        }

