"""
Template + Pattern Fusion Service

Enhanced 2025: Combines template-based suggestions (for new devices) with 
pattern-based suggestions (for existing devices) for optimal automation generation.

Strategy:
- New devices: Use templates (fast, reliable)
- Existing devices: Use patterns (learned behavior)
- Hybrid: Template base + pattern enhancement
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TemplatePatternFusion:
    """
    Fuses template-based and pattern-based suggestions.
    
    Strategy from ai_automation_suggester:
    - New devices: Templates (fast, reliable)
    - Existing devices: Patterns (learned behavior)
    - Hybrid: Template base + pattern insights
    """

    def __init__(self, template_generator, pattern_generator=None):
        """
        Initialize fusion service.
        
        Args:
            template_generator: DeviceTemplateGenerator instance
            pattern_generator: Optional pattern-based suggestion generator
        """
        self.template_generator = template_generator
        self.pattern_generator = pattern_generator

    def should_use_template(
        self,
        device_id: str,
        device_type: str | None,
        has_patterns: bool = False,
        device_age_days: float | None = None
    ) -> bool:
        """
        Determine if template-based generation should be used.
        
        Strategy:
        - New devices (< 7 days): Use templates
        - Devices without patterns: Use templates
        - Devices with patterns: Use patterns (or hybrid)
        
        Args:
            device_id: Device identifier
            device_type: Device type
            has_patterns: Whether device has detected patterns
            device_age_days: Age of device in days (if available)
            
        Returns:
            True if template should be used, False for patterns
        """
        # New devices: Use templates
        if device_age_days is not None and device_age_days < 7:
            return True
        
        # Devices without patterns: Use templates
        if not has_patterns:
            return True
        
        # Devices with patterns: Use patterns (not templates)
        return False

    def fuse_suggestions(
        self,
        template_suggestions: list[dict[str, Any]],
        pattern_suggestions: list[dict[str, Any]],
        device_id: str,
        device_type: str | None
    ) -> list[dict[str, Any]]:
        """
        Fuse template and pattern suggestions.
        
        Strategy:
        1. Templates for new devices (no patterns)
        2. Patterns for existing devices (with usage history)
        3. Hybrid: Template structure + pattern insights
        
        Args:
            template_suggestions: List of template-based suggestions
            pattern_suggestions: List of pattern-based suggestions
            device_id: Device identifier
            device_type: Device type
            
        Returns:
            Fused list of suggestions
        """
        fused = []
        
        # If no patterns, use templates
        if not pattern_suggestions:
            logger.debug(f"Device {device_id} has no patterns - using templates only")
            return template_suggestions
        
        # If no templates, use patterns
        if not template_suggestions:
            logger.debug(f"Device {device_id} has no templates - using patterns only")
            return pattern_suggestions
        
        # Hybrid approach: Combine both
        # Prefer patterns (learned behavior) but include high-scoring templates
        logger.debug(f"Fusing {len(template_suggestions)} templates + {len(pattern_suggestions)} patterns for {device_id}")
        
        # Add patterns first (higher priority - learned behavior)
        for pattern_sugg in pattern_suggestions:
            pattern_sugg['source'] = 'pattern'
            pattern_sugg['fusion_type'] = 'pattern'
            fused.append(pattern_sugg)
        
        # Add high-scoring templates (template_score > 0.85)
        for template_sugg in template_suggestions:
            template_score = template_sugg.get('template_score', template_sugg.get('confidence', 0.0))
            if template_score > 0.85:
                template_sugg['source'] = 'template'
                template_sugg['fusion_type'] = 'template'
                fused.append(template_sugg)
        
        return fused

    def enhance_template_with_pattern(
        self,
        template_suggestion: dict[str, Any],
        pattern_suggestion: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Enhance template suggestion with pattern insights.
        
        Strategy:
        - Use template structure (reliable YAML)
        - Enhance with pattern timing/conditions
        - Combine confidence scores
        
        Args:
            template_suggestion: Template-based suggestion
            pattern_suggestion: Optional pattern-based suggestion
            
        Returns:
            Enhanced suggestion
        """
        if not pattern_suggestion:
            return template_suggestion
        
        enhanced = template_suggestion.copy()
        
        # Enhance with pattern timing
        pattern_metadata = pattern_suggestion.get('metadata', {})
        if 'avg_time' in pattern_metadata:
            enhanced['metadata'] = enhanced.get('metadata', {})
            enhanced['metadata']['pattern_time'] = pattern_metadata['avg_time']
        
        # Combine confidence scores (weighted average)
        template_confidence = enhanced.get('confidence', 0.8)
        pattern_confidence = pattern_suggestion.get('confidence', 0.7)
        enhanced['confidence'] = (template_confidence * 0.6 + pattern_confidence * 0.4)
        
        # Mark as hybrid
        enhanced['fusion_type'] = 'hybrid'
        enhanced['source'] = 'template_pattern_fusion'
        
        return enhanced

