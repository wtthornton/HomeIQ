"""Blueprint matcher that generates multiple suggestions per blueprint."""

import logging
from datetime import datetime
from itertools import combinations
from typing import Any, Optional

from ..clients.blueprint_client import BlueprintClient
from ..clients.data_api_client import DataApiClient
from .suggestion_scorer import SuggestionScorer

logger = logging.getLogger(__name__)


class BlueprintMatcher:
    """
    Matches blueprints to devices and generates multiple suggestions per blueprint.
    
    For each blueprint, generates 3-5 suggestions with different device combinations.
    Each suggestion is scored independently.
    """
    
    def __init__(self):
        """Initialize blueprint matcher."""
        self.scorer = SuggestionScorer()
    
    async def generate_suggestions(
        self,
        min_score: float = 0.6,
        max_suggestions_per_blueprint: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Generate suggestions for all blueprints.
        
        Args:
            min_score: Minimum score threshold for suggestions
            max_suggestions_per_blueprint: Maximum suggestions per blueprint
            
        Returns:
            List of suggestion dictionaries
        """
        all_suggestions = []
        
        # Fetch blueprints and devices
        async with BlueprintClient() as blueprint_client, DataApiClient() as data_client:
            blueprints = await blueprint_client.get_all_blueprints(limit=200)
            entities = await data_client.get_all_entities(limit=1000)
            
            logger.info(f"Processing {len(blueprints)} blueprints against {len(entities)} entities")
            
            for blueprint in blueprints:
                suggestions = await self._generate_blueprint_suggestions(
                    blueprint=blueprint,
                    entities=entities,
                    min_score=min_score,
                    max_suggestions=max_suggestions_per_blueprint,
                )
                all_suggestions.extend(suggestions)
        
        # Sort by score (highest first)
        all_suggestions.sort(key=lambda x: x["suggestion_score"], reverse=True)
        
        logger.info(f"Generated {len(all_suggestions)} total suggestions")
        return all_suggestions
    
    async def generate_suggestions_with_params(
        self,
        device_ids: Optional[list[str]] = None,
        complexity: Optional[str] = None,
        use_case: Optional[str] = None,
        min_score: float = 0.6,
        max_suggestions: int = 10,
        min_quality_score: Optional[float] = None,
        domain: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Generate suggestions with user-defined parameters.
        
        Args:
            device_ids: Specific device entity IDs to use, or None for all
            complexity: Filter by complexity (simple/medium/high), or None for all
            use_case: Filter by use case (convenience/security/energy/comfort), or None for all
            min_score: Minimum score threshold
            max_suggestions: Maximum number of suggestions to generate
            min_quality_score: Minimum blueprint quality score
            domain: Filter by device domain
            
        Returns:
            List of suggestion dictionaries
        """
        all_suggestions = []
        
        # Fetch blueprints and devices
        async with BlueprintClient() as blueprint_client, DataApiClient() as data_client:
            # Fetch blueprints with quality filter
            blueprints = await blueprint_client.get_all_blueprints(
                limit=200,
                min_quality_score=min_quality_score or 0.5,
            )
            
            # Fetch entities
            entities = await data_client.get_all_entities(limit=1000)
            
            # Filter entities by device_ids if specified
            if device_ids:
                device_id_set = set(device_ids)
                entities = [
                    e for e in entities
                    if (e.get("entity_id") or e.get("id")) in device_id_set
                ]
            
            # Filter entities by domain if specified
            if domain:
                entities = [e for e in entities if e.get("domain") == domain]
            
            # Filter blueprints by complexity and use_case
            filtered_blueprints = []
            for blueprint in blueprints:
                # Filter by complexity
                if complexity:
                    blueprint_complexity = str(blueprint.get("complexity", "medium")).lower()
                    if blueprint_complexity != complexity.lower():
                        continue
                
                # Filter by use_case
                if use_case:
                    blueprint_use_case = blueprint.get("use_case")
                    if blueprint_use_case != use_case:
                        continue
                
                filtered_blueprints.append(blueprint)
            
            logger.info(
                f"Processing {len(filtered_blueprints)} blueprints against {len(entities)} entities "
                f"with filters: complexity={complexity}, use_case={use_case}, domain={domain}"
            )
            
            # Generate suggestions for each blueprint
            for blueprint in filtered_blueprints:
                suggestions = await self._generate_blueprint_suggestions(
                    blueprint=blueprint,
                    entities=entities,
                    min_score=min_score,
                    max_suggestions=5,  # Max per blueprint (will limit total later)
                )
                all_suggestions.extend(suggestions)
        
        # Sort by score (highest first) and limit to max_suggestions
        all_suggestions.sort(key=lambda x: x["suggestion_score"], reverse=True)
        all_suggestions = all_suggestions[:max_suggestions]
        
        logger.info(f"Generated {len(all_suggestions)} total suggestions")
        return all_suggestions
    
    async def _generate_blueprint_suggestions(
        self,
        blueprint: dict[str, Any],
        entities: list[dict[str, Any]],
        min_score: float,
        max_suggestions: int,
    ) -> list[dict[str, Any]]:
        """
        Generate multiple suggestions for a single blueprint.
        
        Args:
            blueprint: Blueprint dictionary
            entities: List of entity dictionaries
            min_score: Minimum score threshold
            max_suggestions: Maximum suggestions to generate
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = []
        
        # Find all entities that match blueprint requirements
        required_domains = set(blueprint.get("required_domains", []))
        required_classes = set(blueprint.get("required_device_classes", []))
        
        # Filter entities by domain
        matching_entities = [
            e for e in entities
            if e.get("domain") in required_domains or not required_domains
        ]
        
        # Filter by device class if specified
        if required_classes:
            matching_entities = [
                e for e in matching_entities
                if e.get("device_class") in required_classes or e.get("device_class") is None
            ]
        
        if not matching_entities:
            return suggestions
        
        # Generate different device combinations
        # Strategy: Try combinations of 1, 2, 3+ devices (up to required count)
        required_count = max(len(required_domains), len(required_classes), 1)
        
        # Generate combinations
        device_combinations = []
        
        # Single device suggestions (if blueprint only needs one domain)
        if required_count == 1 and matching_entities:
            for entity in matching_entities[:10]:  # Limit to top 10
                device_combinations.append([entity])
        
        # Two device combinations
        if required_count >= 2 and len(matching_entities) >= 2:
            # Group by domain to ensure diversity
            by_domain = {}
            for entity in matching_entities:
                domain = entity.get("domain")
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(entity)
            
            # Create combinations across domains
            domain_keys = list(by_domain.keys())
            for i, domain1 in enumerate(domain_keys):
                for domain2 in domain_keys[i:]:
                    if domain1 == domain2:
                        # Same domain: take 2 from same domain
                        if len(by_domain[domain1]) >= 2:
                            for combo in combinations(by_domain[domain1][:5], 2):
                                device_combinations.append(list(combo))
                    else:
                        # Different domains: take one from each
                        for e1 in by_domain[domain1][:3]:
                            for e2 in by_domain[domain2][:3]:
                                device_combinations.append([e1, e2])
        
        # Three+ device combinations (limit to avoid explosion)
        if required_count >= 3 and len(matching_entities) >= 3:
            # Limit to reasonable combinations
            for combo in combinations(matching_entities[:20], min(required_count, 3)):
                device_combinations.append(list(combo))
        
        # Score each combination
        scored_combinations = []
        for device_combo in device_combinations[:50]:  # Limit combinations to score
            score = self.scorer.calculate_suggestion_score(
                blueprint=blueprint,
                devices=device_combo,
                current_time=datetime.now(),
            )
            
            if score >= min_score:
                scored_combinations.append({
                    "devices": device_combo,
                    "score": score,
                })
        
        # Sort by score and take top N
        scored_combinations.sort(key=lambda x: x["score"], reverse=True)
        
        for combo_data in scored_combinations[:max_suggestions]:
            suggestion = {
                "blueprint_id": blueprint.get("id"),
                "blueprint_name": blueprint.get("name"),
                "blueprint_description": blueprint.get("description"),
                "blueprint_yaml": blueprint.get("yaml_content"),
                "blueprint_inputs": blueprint.get("blueprint_inputs", {}),
                "suggestion_score": combo_data["score"],
                "matched_devices": [
                    {
                        "entity_id": d.get("entity_id") or d.get("id"),
                        "domain": d.get("domain"),
                        "device_class": d.get("device_class"),
                        "area_id": d.get("area_id"),
                        "area_name": d.get("area_name"),
                        "device_id": d.get("device_id"),
                        "friendly_name": d.get("friendly_name") or d.get("name"),
                    }
                    for d in combo_data["devices"]
                ],
                "use_case": blueprint.get("use_case"),
            }
            suggestions.append(suggestion)
        
        return suggestions
