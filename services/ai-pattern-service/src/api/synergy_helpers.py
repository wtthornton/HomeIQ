"""
Synergy Router Helper Functions

Provides utility functions for synergy data parsing and transformation.
Reduces code duplication in synergy_router.py.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def safe_parse_json(
    value: Any,
    default: Any = None,
    field_name: str = "field",
    context_id: Optional[str] = None
) -> Any:
    """
    Safely parse a JSON string or return the value if already parsed.
    
    Args:
        value: Value to parse (string or already parsed)
        default: Default value if parsing fails
        field_name: Name of the field for logging
        context_id: Optional identifier for logging context
        
    Returns:
        Parsed value or default
    """
    if value is None:
        return default
    
    if isinstance(value, (dict, list)):
        return value
    
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError) as e:
            context_str = f" for {context_id}" if context_id else ""
            logger.warning(f"Failed to parse {field_name}{context_str}: {e}")
            return default
    
    return default


def extract_synergy_fields(
    synergy: Any,
    is_dict: bool = True
) -> dict[str, Any]:
    """
    Extract and normalize synergy fields from database result.
    
    Args:
        synergy: Synergy object or dictionary
        is_dict: Whether synergy is a dictionary
        
    Returns:
        Normalized synergy dictionary
    """
    if is_dict:
        return _extract_from_dict(synergy)
    return _extract_from_object(synergy)


def _extract_from_dict(synergy: dict[str, Any]) -> dict[str, Any]:
    """Extract fields from dictionary synergy."""
    synergy_id = synergy.get("synergy_id")
    
    metadata = safe_parse_json(
        synergy.get("opportunity_metadata"),
        default={},
        field_name="opportunity_metadata",
        context_id=synergy_id
    )
    
    device_ids = safe_parse_json(
        synergy.get("device_ids"),
        default=[],
        field_name="device_ids",
        context_id=synergy_id
    )
    
    chain_devices = safe_parse_json(
        synergy.get("chain_devices"),
        default=None,
        field_name="chain_devices",
        context_id=synergy_id
    )
    
    explanation = safe_parse_json(
        synergy.get("explanation") or metadata.get('explanation'),
        default=None,
        field_name="explanation",
        context_id=synergy_id
    )
    
    context_breakdown = safe_parse_json(
        synergy.get("context_breakdown") or metadata.get('context_breakdown'),
        default=None,
        field_name="context_breakdown",
        context_id=synergy_id
    )
    
    return {
        "id": synergy.get("id"),
        "synergy_id": synergy_id,
        "synergy_type": synergy.get("synergy_type"),
        "devices": device_ids,
        "chain_devices": chain_devices,
        "metadata": metadata,
        "impact_score": synergy.get("impact_score", 0.0),
        "confidence": synergy.get("confidence", 0.0),
        "complexity": synergy.get("complexity", "medium"),
        "area": synergy.get("area"),
        "synergy_depth": synergy.get("synergy_depth", 2),
        "explanation": explanation,
        "context_breakdown": context_breakdown,
        "context_metadata": metadata.get('context_metadata'),
        "created_at": synergy.get("created_at"),
        "updated_at": synergy.get("updated_at")
    }


def _extract_from_object(synergy: Any) -> dict[str, Any]:
    """Extract fields from SQLAlchemy synergy object."""
    synergy_id = synergy.synergy_id
    
    metadata = safe_parse_json(
        synergy.opportunity_metadata,
        default={},
        field_name="opportunity_metadata",
        context_id=synergy_id
    )
    
    device_ids = safe_parse_json(
        synergy.device_ids,
        default=[],
        field_name="device_ids",
        context_id=synergy_id
    )
    
    chain_devices = safe_parse_json(
        getattr(synergy, 'chain_devices', None),
        default=None,
        field_name="chain_devices",
        context_id=synergy_id
    )
    
    explanation = safe_parse_json(
        getattr(synergy, 'explanation', None) or metadata.get('explanation'),
        default=None,
        field_name="explanation",
        context_id=synergy_id
    )
    
    context_breakdown = safe_parse_json(
        getattr(synergy, 'context_breakdown', None) or metadata.get('context_breakdown'),
        default=None,
        field_name="context_breakdown",
        context_id=synergy_id
    )
    
    return {
        "id": synergy.id,
        "synergy_id": synergy_id,
        "synergy_type": synergy.synergy_type,
        "devices": device_ids,
        "chain_devices": chain_devices,
        "metadata": metadata,
        "impact_score": float(synergy.impact_score) if synergy.impact_score is not None else 0.0,
        "confidence": float(synergy.confidence) if synergy.confidence is not None else 0.0,
        "complexity": synergy.complexity or "medium",
        "area": synergy.area,
        "synergy_depth": getattr(synergy, 'synergy_depth', 2),
        "explanation": explanation,
        "context_breakdown": context_breakdown,
        "context_metadata": metadata.get('context_metadata'),
        "created_at": synergy.created_at.isoformat() if synergy.created_at else None,
        "updated_at": synergy.updated_at.isoformat() if hasattr(synergy, 'updated_at') and synergy.updated_at else None
    }


def find_synergy_by_id(
    synergies: list[Any],
    synergy_id: str
) -> Optional[Any]:
    """
    Find a synergy by its synergy_id.
    
    Args:
        synergies: List of synergy objects or dictionaries
        synergy_id: Synergy ID to find
        
    Returns:
        Synergy object/dict if found, None otherwise
    """
    for s in synergies:
        if isinstance(s, dict):
            if s.get("synergy_id") == synergy_id:
                return s
        else:
            if s.synergy_id == synergy_id:
                return s
    return None


def generate_xai_explanation(
    synergy_data: dict[str, Any],
    explainer: Any
) -> Optional[str]:
    """
    Generate XAI explanation for a synergy.
    
    Args:
        synergy_data: Normalized synergy dictionary
        explainer: ExplainableSynergyGenerator instance
        
    Returns:
        Generated explanation or None
    """
    try:
        metadata = synergy_data.get('metadata', {})
        synergy_for_explanation = {
            'synergy_id': synergy_data.get("synergy_id"),
            'relationship_type': metadata.get('relationship', ''),
            'trigger_entity': metadata.get('trigger_entity'),
            'trigger_name': metadata.get('trigger_name'),
            'action_entity': metadata.get('action_entity'),
            'action_name': metadata.get('action_name'),
            'area': synergy_data.get("area"),
            'impact_score': synergy_data.get("impact_score", 0.0),
            'confidence': synergy_data.get("confidence", 0.0),
            'complexity': synergy_data.get("complexity", "medium"),
            'opportunity_metadata': metadata
        }
        return explainer.generate_explanation(
            synergy_for_explanation,
            synergy_data.get('context_metadata')
        )
    except Exception as e:
        logger.warning(
            f"Failed to generate explanation for synergy "
            f"{synergy_data.get('synergy_id')}: {e}"
        )
        return None


def calculate_synergy_stats(synergies: list[Any]) -> dict[str, Any]:
    """
    Calculate statistics for a list of synergies.
    
    Args:
        synergies: List of synergy objects or dictionaries
        
    Returns:
        Statistics dictionary
    """
    total = len(synergies)
    by_type: dict[str, int] = {}
    by_complexity: dict[str, int] = {}
    total_confidence = 0.0
    total_impact = 0.0
    areas: set[str] = set()
    
    for s in synergies:
        if isinstance(s, dict):
            synergy_type = s.get("synergy_type", "unknown")
            complexity = s.get("complexity", "medium")
            confidence = s.get("confidence", 0.0)
            impact = s.get("impact_score", 0.0)
            area = s.get("area")
        else:
            synergy_type = s.synergy_type
            complexity = s.complexity or "medium"
            confidence = float(s.confidence) if s.confidence is not None else 0.0
            impact = float(s.impact_score) if s.impact_score is not None else 0.0
            area = s.area
        
        by_type[synergy_type] = by_type.get(synergy_type, 0) + 1
        by_complexity[complexity] = by_complexity.get(complexity, 0) + 1
        total_confidence += confidence
        total_impact += impact
        
        if area:
            areas.add(area)
    
    return {
        "total_synergies": total,
        "by_type": by_type,
        "by_complexity": by_complexity,
        "avg_impact_score": round(total_impact / total, 3) if total > 0 else 0.0,
        "avg_confidence": round(total_confidence / total, 3) if total > 0 else 0.0,
        "unique_areas": len(areas)
    }
