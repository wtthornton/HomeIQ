"""
Automated Correlation Insights and Explanations

Epic 38, Story 38.6: Automated Insights and Explanations
Generates automated correlation insights, natural language explanations,
and integrates with automation suggestions.

Single-home NUC optimized:
- Memory: <20MB (lightweight insight generation)
- Performance: <100ms per insight generation
- Natural language generation without heavy LLM calls
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime

from .augmented_analytics import AugmentedCorrelationAnalytics
from .correlation_service import CorrelationService
from .presence_aware_correlations import PresenceAwareCorrelationAnalyzer

from shared.logging_config import get_logger

logger = get_logger(__name__)


class AutomatedCorrelationInsights:
    """
    Generates automated insights and explanations for correlations.
    
    Provides:
    - Automated correlation insights
    - Natural language explanations
    - Integration with automation suggestions
    - Context-aware explanations
    
    Single-home optimization:
    - Lightweight insight generation
    - Rule-based natural language generation
    - Efficient explanation templates
    """
    
    def __init__(
        self,
        correlation_service: CorrelationService,
        augmented_analytics: Optional[AugmentedCorrelationAnalytics] = None,
        presence_analyzer: Optional[PresenceAwareCorrelationAnalyzer] = None
    ):
        """
        Initialize automated insights generator.
        
        Args:
            correlation_service: Correlation service instance
            augmented_analytics: Optional augmented analytics instance
            presence_analyzer: Optional presence-aware analyzer instance
        """
        self.correlation_service = correlation_service
        self.augmented_analytics = augmented_analytics or AugmentedCorrelationAnalytics(
            correlation_service
        )
        self.presence_analyzer = presence_analyzer
        
        logger.info("AutomatedCorrelationInsights initialized")
    
    def generate_correlation_insights(
        self,
        entity1_id: str,
        entity2_id: str,
        entity1_metadata: Optional[Dict] = None,
        entity2_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive correlation insights.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
        
        Returns:
            Dict with comprehensive insights:
            {
                'correlation_explanation': Dict,  # From augmented analytics
                'pattern_detection': Dict,  # Pattern analysis
                'presence_insights': Optional[Dict],  # Presence-aware insights
                'automation_opportunity': Dict,  # Automation suggestion
                'summary': str,  # Brief summary
                'recommendations': List[str]  # Actionable recommendations
            }
        """
        try:
            # Get correlation score
            correlation_score = self.correlation_service.get_correlation(
                entity1_id, entity2_id, entity1_metadata, entity2_metadata
            ) or 0.0
            
            # Generate correlation explanation
            explanation = self.augmented_analytics.explain_correlation(
                entity1_id, entity2_id, correlation_score,
                entity1_metadata, entity2_metadata
            )
            
            # Detect patterns
            pattern = self.augmented_analytics.detect_patterns(
                entity1_id, entity2_id, entity1_metadata, entity2_metadata, correlation_score
            )
            
            # Generate presence insights (if available)
            presence_insights = None
            if self.presence_analyzer:
                try:
                    # This would be async in production
                    # For now, return None (would need async context)
                    pass
                except Exception as e:
                    logger.debug("Failed to get presence insights: %s", e)
            
            # Generate automation opportunity
            automation_opportunity = self._generate_automation_opportunity(
                entity1_id, entity2_id, correlation_score, pattern, explanation
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                entity1_id, entity2_id, correlation_score, pattern, explanation
            )
            
            # Generate summary
            summary = self._generate_insights_summary(
                entity1_id, entity2_id, correlation_score, pattern, explanation
            )
            
            return {
                'correlation_explanation': explanation,
                'pattern_detection': pattern,
                'presence_insights': presence_insights,
                'automation_opportunity': automation_opportunity,
                'summary': summary,
                'recommendations': recommendations,
                'timestamp': datetime.now()
            }
        
        except Exception as e:
            logger.error("Failed to generate correlation insights: %s", e)
            return {
                'correlation_explanation': {'error': str(e)},
                'pattern_detection': {'error': str(e)},
                'presence_insights': None,
                'automation_opportunity': {},
                'summary': f'Failed to generate insights for {entity1_id} and {entity2_id}',
                'recommendations': [],
                'error': str(e)
            }
    
    def enhance_automation_suggestion(
        self,
        suggestion: Dict,
        entity_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Enhance automation suggestion with correlation insights.
        
        Args:
            suggestion: Automation suggestion dict
            entity_metadata: Optional entity metadata mapping
        
        Returns:
            Enhanced suggestion with correlation insights:
            {
                ...original suggestion fields...,
                'correlation_insights': Dict,
                'explanation': str,
                'confidence_boost': float
            }
        """
        try:
            enhanced = suggestion.copy()
            
            # Extract entity IDs from suggestion
            entity_ids = self._extract_entity_ids_from_suggestion(suggestion)
            
            if len(entity_ids) < 2:
                # Single entity, no correlation to analyze
                enhanced['correlation_insights'] = None
                enhanced['correlation_explanation'] = 'Single entity suggestion - no correlation analysis'
                return enhanced
            
            # Generate insights for first pair (or all pairs if multiple)
            entity1_id = entity_ids[0]
            entity2_id = entity_ids[1] if len(entity_ids) > 1 else entity_ids[0]
            
            entity1_meta = entity_metadata.get(entity1_id, {}) if entity_metadata else {}
            entity2_meta = entity_metadata.get(entity2_id, {}) if entity_metadata else {}
            
            # Generate insights
            insights = self.generate_correlation_insights(
                entity1_id, entity2_id, entity1_meta, entity2_meta
            )
            
            # Add to suggestion
            enhanced['correlation_insights'] = insights
            enhanced['correlation_explanation'] = insights.get('summary', '')
            
            # Boost confidence if correlation is strong
            correlation_score = insights.get('correlation_explanation', {}).get('correlation_score', 0.0)
            if abs(correlation_score) > 0.7:
                current_confidence = enhanced.get('confidence', 0.7)
                enhanced['confidence'] = min(1.0, current_confidence * 1.1)
                enhanced['confidence_boost'] = 'correlation_strong'
            elif abs(correlation_score) > 0.5:
                current_confidence = enhanced.get('confidence', 0.7)
                enhanced['confidence'] = min(1.0, current_confidence * 1.05)
                enhanced['confidence_boost'] = 'correlation_moderate'
            
            return enhanced
        
        except Exception as e:
            logger.error("Failed to enhance automation suggestion: %s", e)
            # Return original suggestion on error
            return suggestion
    
    def _generate_automation_opportunity(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        pattern: Dict,
        explanation: Dict
    ) -> Dict:
        """Generate automation opportunity from correlation"""
        strength = explanation.get('strength', 'unknown')
        pattern_type = pattern.get('pattern_type', 'none')
        
        # Determine opportunity type based on pattern
        opportunity_types = {
            'complementary': 'device_synergy',
            'spatial': 'area_automation',
            'temporal': 'time_based_automation',
            'sequential': 'trigger_automation',
            'general': 'correlation_automation'
        }
        
        opportunity_type = opportunity_types.get(pattern_type, 'general')
        
        # Generate opportunity description
        if abs(correlation_score) > 0.7:
            opportunity_desc = (
                f"Strong {strength} correlation detected between {entity1_id} and {entity2_id}. "
                f"This suggests an automation opportunity where {entity1_id} could trigger {entity2_id}."
            )
        elif abs(correlation_score) > 0.5:
            opportunity_desc = (
                f"Moderate correlation detected between {entity1_id} and {entity2_id}. "
                f"Consider creating an automation to link these devices."
            )
        else:
            opportunity_desc = (
                f"Weak correlation between {entity1_id} and {entity2_id}. "
                f"Automation may not be beneficial."
            )
        
        return {
            'type': opportunity_type,
            'description': opportunity_desc,
            'entity1_id': entity1_id,
            'entity2_id': entity2_id,
            'correlation_score': correlation_score,
            'pattern_type': pattern_type,
            'recommended': abs(correlation_score) > 0.5
        }
    
    def _generate_recommendations(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        pattern: Dict,
        explanation: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        strength = explanation.get('strength', 'unknown')
        pattern_type = pattern.get('pattern_type', 'none')
        
        if abs(correlation_score) > 0.7:
            recommendations.append(
                f"Create automation: When {entity1_id} changes, trigger {entity2_id}"
            )
            
            if pattern_type == 'complementary':
                recommendations.append(
                    f"These devices are complementary - consider a bidirectional automation"
                )
            elif pattern_type == 'spatial':
                recommendations.append(
                    f"Both devices are in the same area - create an area-based automation"
                )
            elif pattern_type == 'temporal':
                recommendations.append(
                    f"Devices are used at similar times - create a time-based automation"
                )
        
        elif abs(correlation_score) > 0.5:
            recommendations.append(
                f"Consider monitoring {entity1_id} and {entity2_id} for automation opportunities"
            )
        
        # Add pattern-specific recommendations
        factors = explanation.get('factors', [])
        if 'Same area/room' in factors:
            recommendations.append("Devices are in the same area - ideal for area-based automation")
        
        if 'High time overlap' in factors:
            recommendations.append("High time overlap suggests time-based automation would be effective")
        
        return recommendations
    
    def _generate_insights_summary(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        pattern: Dict,
        explanation: Dict
    ) -> str:
        """Generate brief insights summary"""
        summary = explanation.get('summary', '')
        
        # Add pattern information
        pattern_type = pattern.get('pattern_type', 'none')
        if pattern_type != 'none':
            pattern_desc = pattern.get('description', '')
            summary += f" Pattern: {pattern_desc}"
        
        return summary
    
    def _extract_entity_ids_from_suggestion(self, suggestion: Dict) -> List[str]:
        """Extract entity IDs from automation suggestion"""
        entity_ids = []
        
        # Try different suggestion formats
        if 'entity_ids' in suggestion:
            entity_ids.extend(suggestion['entity_ids'])
        
        if 'devices_involved' in suggestion:
            # These might be friendly names, not entity IDs
            devices = suggestion['devices_involved']
            if isinstance(devices, list):
                entity_ids.extend([d for d in devices if isinstance(d, str) and '.' in d])
        
        if 'validated_entities' in suggestion:
            # Extract entity IDs from validated_entities dict
            validated = suggestion['validated_entities']
            if isinstance(validated, dict):
                entity_ids.extend(validated.values())
        
        if 'trigger' in suggestion and 'entities' in suggestion['trigger']:
            trigger_entities = suggestion['trigger']['entities']
            if isinstance(trigger_entities, list):
                entity_ids.extend([e if isinstance(e, str) else e.get('entity_id', '') for e in trigger_entities])
        
        if 'action' in suggestion and 'entities' in suggestion['action']:
            action_entities = suggestion['action']['entities']
            if isinstance(action_entities, list):
                entity_ids.extend([e if isinstance(e, str) else e.get('entity_id', '') for e in action_entities])
        
        # Remove duplicates and empty strings
        return list(set([eid for eid in entity_ids if eid and '.' in eid]))

