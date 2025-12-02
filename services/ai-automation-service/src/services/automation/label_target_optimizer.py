"""
Label Target Optimization Utilities for Automation Actions

Optimizes action targets to use label_id when appropriate entities share
common labels, improving maintainability and cross-cutting organization.

Story AI10.2: Label Target Usage in YAML Generation
Epic AI-10: Home Assistant 2025 YAML Target Optimization & Voice Enhancement
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def optimize_action_labels(
    yaml_data: dict[str, Any],
    entities_metadata: dict[str, dict[str, Any]] | None = None,
    ha_client: Any | None = None
) -> dict[str, Any]:
    """
    Optimize action targets to use label_id when entities share common labels.
    
    Converts entity_id lists to:
    - label_id: when all entities share at least one common label
    
    Args:
        yaml_data: Parsed automation YAML data
        entities_metadata: Pre-fetched entity metadata with labels
        ha_client: Home Assistant client for label validation
        
    Returns:
        YAML data with optimized label targets (if applicable)
    """
    if not entities_metadata:
        logger.debug("No entity metadata available, skipping label optimization")
        return yaml_data
    
    try:
        actions = yaml_data.get("action", [])
        if not isinstance(actions, list):
            return yaml_data
        
        optimized_actions = []
        for action in actions:
            if not isinstance(action, dict):
                optimized_actions.append(action)
                continue
            
            # Check if action has target with entity_id list
            target = action.get("target")
            if not target or not isinstance(target, dict):
                optimized_actions.append(action)
                continue
            
            entity_id = target.get("entity_id")
            if not entity_id or not isinstance(entity_id, list) or len(entity_id) < 2:
                # Not a list or only one entity - no optimization needed
                optimized_actions.append(action)
                continue
            
            # Try to optimize to label_id
            optimized_action = await _optimize_single_action_label(
                action, entity_id, entities_metadata, ha_client
            )
            optimized_actions.append(optimized_action)
        
        yaml_data["action"] = optimized_actions
        return yaml_data
    
    except Exception as e:
        logger.debug(f"Could not optimize label targets: {e}")
        return yaml_data


async def _optimize_single_action_label(
    action: dict[str, Any],
    entity_ids: list[str],
    entities_metadata: dict[str, dict[str, Any]],
    ha_client: Any | None
) -> dict[str, Any]:
    """
    Optimize a single action's target to use label_id if applicable.
    
    Args:
        action: Action dictionary
        entity_ids: List of entity IDs in the target
        entities_metadata: Entity metadata with labels
        ha_client: Home Assistant client for label validation
        
    Returns:
        Optimized action dictionary or original if optimization not possible
    """
    try:
        # Collect labels for all entities
        entity_labels = {}
        for entity_id in entity_ids:
            metadata = entities_metadata.get(entity_id)
            if not metadata:
                # Missing metadata - skip optimization
                return action
            
            labels = metadata.get('labels', [])
            if not isinstance(labels, list):
                labels = []
            
            entity_labels[entity_id] = set(labels)
        
        if not entity_labels or len(entity_labels) != len(entity_ids):
            # Could not get labels for all entities - skip optimization
            return action
        
        # Find common labels across all entities
        all_entity_sets = list(entity_labels.values())
        if not all_entity_sets:
            return action
        
        common_labels = set.intersection(*all_entity_sets)
        
        if not common_labels:
            # No common labels - skip optimization
            logger.debug(f"No common labels found for {len(entity_ids)} entities")
            return action
        
        # Select the most specific/relevant common label using heuristic ranking
        selected_label = _rank_labels_by_relevance(common_labels, entity_ids, entities_metadata)
        
        # Validate label exists in Home Assistant (optional, requires Label API)
        if ha_client:
            try:
                # Note: Label API validation could be added here if needed
                # For now, we trust that labels from entity metadata are valid
                pass
            except Exception as e:
                logger.debug(f"Could not validate label in HA: {e}")
        
        logger.info(f"Optimized target to label_id: '{selected_label}' (from {len(entity_ids)} entities with {len(common_labels)} common labels)")
        
        # Create optimized action with label_id targeting
        optimized_action = dict(action)  # Create a new dict copy
        optimized_action["target"] = {"label_id": selected_label}
        
        return optimized_action
    
    except Exception as e:
        logger.debug(f"Could not optimize action label target: {e}")
        return action


def add_label_hint_to_description(
    description: str,
    label_id: str,
    entity_count: int
) -> str:
    """
    Add label hint to automation description.
    
    Args:
        description: Original description
        label_id: Label ID being used
        entity_count: Number of entities with this label
        
    Returns:
        Enhanced description with label hint
    """
    if not description:
        description = f"Automation using '{label_id}' labeled devices"
    
    # Add label hint
    label_hint = f" (uses '{label_id}' label - {entity_count} devices)"
    
    # Avoid duplicate hints
    if label_hint not in description and f"'{label_id}'" not in description:
        description = description.rstrip('.') + label_hint
    
    return description


def get_common_labels(entities: list[dict[str, Any]]) -> set[str]:
    """
    Get labels that are common across all provided entities.
    
    Args:
        entities: List of entity dictionaries with 'labels' field
        
    Returns:
        Set of common label IDs
    """
    if not entities:
        return set()
    
    # Collect label sets for each entity
    label_sets = []
    for entity in entities:
        labels = entity.get('labels', [])
        if not isinstance(labels, list):
            labels = []
        label_sets.append(set(labels))
    
    if not label_sets:
        return set()
    
    # Find intersection (common labels)
    common_labels = set.intersection(*label_sets)
    return common_labels


def should_use_label_targeting(
    entity_ids: list[str],
    entities_metadata: dict[str, dict[str, Any]]
) -> tuple[bool, str | None]:
    """
    Determine if label targeting should be used for given entities.
    
    Args:
        entity_ids: List of entity IDs
        entities_metadata: Entity metadata with labels
        
    Returns:
        Tuple of (should_use_label, label_id)
    """
    if len(entity_ids) < 2:
        return False, None
    
    # Collect entities
    entities = []
    for entity_id in entity_ids:
        metadata = entities_metadata.get(entity_id)
        if metadata:
            entities.append(metadata)
    
    if len(entities) != len(entity_ids):
        # Missing metadata for some entities
        return False, None
    
    # Get common labels
    common_labels = get_common_labels(entities)
    
    if not common_labels:
        return False, None
    
    # Select best label using heuristic ranking
    selected_label = _rank_labels_by_relevance(common_labels, entity_ids, entities_metadata)
    
    return True, selected_label


def _rank_labels_by_relevance(
    labels: set[str],
    entity_ids: list[str],
    entities_metadata: dict[str, dict[str, Any]]
) -> str:
    """
    Rank labels by relevance using heuristic scoring.
    
    Scoring criteria (highest score wins):
    1. Specificity (longer, hyphenated labels are more specific)
    2. Domain relevance (matches entity domains)
    3. Common patterns (holiday, outdoor, security, energy, etc.)
    4. Alphabetical (tiebreaker)
    
    Args:
        labels: Set of common labels to rank
        entity_ids: Entity IDs being targeted
        entities_metadata: Entity metadata for context
        
    Returns:
        Best label ID based on heuristic ranking
    """
    if len(labels) == 1:
        return list(labels)[0]
    
    # Get entity domains for relevance scoring
    domains = set()
    for entity_id in entity_ids:
        if '.' in entity_id:
            domain = entity_id.split('.', 1)[0]
            domains.add(domain)
    
    # Score each label
    label_scores = {}
    for label in labels:
        score = 0
        label_lower = label.lower()
        
        # 1. Specificity score (longer, hyphenated labels are more specific)
        # Examples: "holiday-lights" (14 chars, 1 hyphen) > "outdoor" (7 chars)
        score += len(label) * 2  # Length bonus
        score += label.count('-') * 10  # Hyphen bonus (compound labels)
        score += label.count('_') * 10  # Underscore bonus
        
        # 2. High-value pattern matching (domain-specific, user-created labels)
        high_value_patterns = {
            'holiday': 30,  # Seasonal/event-based
            'christmas': 30,
            'outdoor': 25,  # Location-based (not generic "area")
            'indoor': 20,
            'security': 35,  # Function-based (critical)
            'safety': 35,
            'energy': 30,  # Optimization-based
            'entertainment': 25,  # Activity-based
            'kids': 25,  # User-segment
            'guest': 25,
            'office': 25,  # Room-specific (more specific than area)
            'bedroom': 25,
            'kitchen': 25,
        }
        
        for pattern, bonus in high_value_patterns.items():
            if pattern in label_lower:
                score += bonus
        
        # 3. Domain relevance (label relates to entity types)
        # Examples: "lights" label with light.* entities
        domain_patterns = {
            'light': ['light', 'lamp', 'bulb', 'lighting'],
            'switch': ['switch', 'outlet', 'plug'],
            'climate': ['climate', 'hvac', 'temperature', 'thermostat'],
            'media_player': ['media', 'tv', 'entertainment', 'audio'],
            'lock': ['lock', 'security'],
            'cover': ['cover', 'blind', 'shade', 'curtain'],
        }
        
        for domain in domains:
            patterns = domain_patterns.get(domain, [])
            for pattern in patterns:
                if pattern in label_lower:
                    score += 20  # Domain match bonus
        
        # 4. Penalize generic labels (too broad)
        generic_penalties = {
            'all': -15,
            'misc': -15,
            'other': -15,
            'temp': -10,
            'test': -20,
        }
        
        for pattern, penalty in generic_penalties.items():
            if pattern in label_lower:
                score += penalty
        
        label_scores[label] = score
    
    # Sort by score (descending), then alphabetically for tiebreaker
    sorted_labels = sorted(
        labels,
        key=lambda x: (label_scores[x], x.lower()),
        reverse=True
    )
    
    best_label = sorted_labels[0]
    logger.debug(f"Label ranking: {[(l, label_scores[l]) for l in sorted_labels[:3]]} → selected '{best_label}'")
    
    return best_label

