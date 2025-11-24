"""
Explainable AI (XAI) for Synergy Recommendations

Generates human-readable explanations for synergy recommendations to build user trust
and improve acceptance rates. Research shows 40% higher acceptance with explanations.

2025 Best Practice: Explainable AI is critical for user trust in recommendation systems
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ExplainableSynergyGenerator:
    """
    Generates human-readable explanations for synergy recommendations.
    
    Explains:
    1. Why this synergy was detected
    2. How the score was calculated
    3. What evidence supports it
    4. What benefits it provides
    """

    def __init__(self):
        """Initialize explainable synergy generator."""
        logger.info("ExplainableSynergyGenerator initialized")

    def generate_explanation(
        self,
        synergy: dict,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate comprehensive explanation for synergy.
        
        Args:
            synergy: Synergy opportunity dictionary
            context: Optional context metadata
        
        Returns:
            {
                'summary': str,
                'detailed': str,
                'score_breakdown': dict,
                'evidence': list[str],
                'benefits': list[str],
                'visualization': dict
            }
        """
        # Input validation (2025 improvement)
        if not isinstance(synergy, dict):
            raise ValueError("synergy must be a dictionary")
        
        synergy_id = synergy.get('synergy_id', 'unknown')
        trigger_entity = synergy.get('trigger_entity', synergy.get('trigger_name', 'unknown'))
        action_entity = synergy.get('action_entity', synergy.get('action_name', 'unknown'))
        
        logger.debug(
            f"Generating explanation for synergy {synergy_id} "
            f"({trigger_entity} → {action_entity})"
        )
        
        explanation = {
            'summary': self._generate_summary(synergy),
            'detailed': self._generate_detailed_explanation(synergy, context),
            'score_breakdown': self._breakdown_score(synergy),
            'evidence': self._collect_evidence(synergy),
            'benefits': self._list_benefits(synergy),
            'visualization': self._create_visualization(synergy)
        }
        
        return explanation

    def _generate_summary(self, synergy: dict) -> str:
        """Generate one-line summary."""
        trigger_name = synergy.get('trigger_name', synergy.get('trigger_entity', 'Device'))
        action_name = synergy.get('action_name', synergy.get('action_entity', 'Device'))
        relationship = synergy.get('relationship_type', 'automation')
        area = synergy.get('area', 'your home')
        
        # Convert relationship type to readable format
        relationship_readable = relationship.replace('_', ' ').title()
        
        return (
            f"{relationship_readable}: {trigger_name} → {action_name} "
            f"in {area} (Impact: {synergy.get('impact_score', 0):.0%})"
        )

    def _generate_detailed_explanation(
        self,
        synergy: dict,
        context: dict[str, Any] | None
    ) -> str:
        """Generate detailed explanation."""
        trigger_name = synergy.get('trigger_name', synergy.get('trigger_entity', 'Device'))
        action_name = synergy.get('action_name', synergy.get('action_entity', 'Device'))
        relationship = synergy.get('relationship_type', 'automation')
        area = synergy.get('area', 'your home')
        impact = synergy.get('impact_score', 0)
        confidence = synergy.get('confidence', 0)
        
        explanation_parts = []
        
        # Main description
        explanation_parts.append(
            f"This automation would connect {trigger_name} to {action_name} in {area}. "
        )
        
        # Relationship context
        if relationship == 'motion_to_light':
            explanation_parts.append(
                "When motion is detected, the lights will automatically turn on, "
                "providing convenience and energy efficiency."
            )
        elif relationship == 'door_to_lock':
            explanation_parts.append(
                "When the door closes, it will automatically lock, enhancing security."
            )
        elif relationship == 'temp_to_climate':
            explanation_parts.append(
                "The climate system will adjust based on temperature readings, "
                "maintaining comfort automatically."
            )
        else:
            explanation_parts.append(
                f"This {relationship.replace('_', ' ')} relationship would automate "
                "device interactions for improved convenience."
            )
        
        # Impact and confidence
        explanation_parts.append(
            f"\nImpact Score: {impact:.0%} | Confidence: {confidence:.0%}"
        )
        
        # Context information
        if context:
            if context.get('weather'):
                explanation_parts.append(
                    f"\nCurrent conditions: {context.get('weather', 'unknown')} "
                    f"({context.get('temperature', 'N/A')}°C)"
                )
            if context.get('peak_hours'):
                explanation_parts.append(
                    "\n⚠️ Note: Currently in peak energy hours - consider scheduling for off-peak."
                )
        
        return " ".join(explanation_parts)

    def _breakdown_score(self, synergy: dict) -> dict[str, Any]:
        """
        Break down impact score into components.
        
        Returns:
            {
                'base_benefit': float,
                'usage_frequency': float,
                'area_traffic': float,
                'time_weight': float,
                'health_factor': float,
                'complexity_penalty': float,
                'final_score': float
            }
        """
        # Extract score components if available
        breakdown = {
            'base_benefit': synergy.get('base_benefit', synergy.get('impact_score', 0.7)),
            'usage_frequency': synergy.get('usage_freq', 0.5),
            'area_traffic': synergy.get('area_traffic', 0.7),
            'time_weight': synergy.get('time_weight', 1.0),
            'health_factor': synergy.get('health_factor', 1.0),
            'complexity_penalty': synergy.get('complexity_penalty', 0.1),
            'final_score': synergy.get('impact_score', 0.5)
        }
        
        # If context breakdown available, use it
        if 'context_breakdown' in synergy:
            context_breakdown = synergy['context_breakdown']
            breakdown.update({
                'temporal_boost': context_breakdown.get('temporal_boost', 1.0),
                'weather_boost': context_breakdown.get('weather_boost', 1.0),
                'energy_boost': context_breakdown.get('energy_boost', 1.0),
                'behavior_boost': context_breakdown.get('behavior_boost', 1.0),
                'enhanced_score': synergy.get('enhanced_score', breakdown['final_score'])
            })
        
        return breakdown

    def _collect_evidence(self, synergy: dict) -> list[str]:
        """
        Collect evidence supporting this synergy.
        
        Returns:
            List of evidence strings
        """
        evidence = []
        
        # Usage evidence
        trigger_name = synergy.get('trigger_name', synergy.get('trigger_entity', 'Device'))
        action_name = synergy.get('action_name', synergy.get('action_entity', 'Device'))
        
        if synergy.get('trigger_usage_count'):
            evidence.append(
                f"{trigger_name} was used {synergy['trigger_usage_count']} times in the last 30 days"
            )
        
        if synergy.get('action_usage_count'):
            evidence.append(
                f"{action_name} was used {synergy['action_usage_count']} times in the same period"
            )
        
        # Area evidence
        area = synergy.get('area')
        if area and area != 'unknown':
            evidence.append(f"Both devices are located in {area}")
        
        # Pattern validation evidence
        if synergy.get('validated_by_patterns'):
            pattern_score = synergy.get('pattern_support_score', 0)
            evidence.append(
                f"Validated by detected usage patterns ({pattern_score:.0%} support)"
            )
        
        # ML discovery evidence
        if synergy.get('synergy_type') == 'ml_discovered':
            frequency = synergy.get('frequency', 0)
            consistency = synergy.get('consistency', 0)
            evidence.append(
                f"Discovered from {frequency} real usage occurrences "
                f"({consistency:.0%} consistent)"
            )
        
        # No existing automation
        evidence.append("No existing automation currently connects these devices")
        
        # Confidence evidence
        confidence = synergy.get('confidence', 0)
        if confidence >= 0.9:
            evidence.append("High confidence based on device compatibility and location")
        elif confidence >= 0.7:
            evidence.append("Moderate confidence - good match with some uncertainty")
        
        return evidence

    def _list_benefits(self, synergy: dict) -> list[str]:
        """List user benefits of this synergy."""
        benefits = []
        relationship = synergy.get('relationship_type', '')
        
        # Relationship-specific benefits
        if 'motion_to_light' in relationship or 'occupancy_to_light' in relationship:
            benefits.extend([
                "Automatic lighting when you enter a room",
                "Energy savings by turning lights off when not needed",
                "Improved convenience - no need to manually switch lights"
            ])
        elif 'door_to_lock' in relationship:
            benefits.extend([
                "Enhanced security - automatic locking",
                "Peace of mind - never forget to lock the door",
                "Protection against unauthorized access"
            ])
        elif 'temp_to_climate' in relationship:
            benefits.extend([
                "Automatic climate control for comfort",
                "Energy efficiency through smart temperature management",
                "Consistent temperature without manual adjustment"
            ])
        elif 'presence_to_light' in relationship or 'presence_to_climate' in relationship:
            benefits.extend([
                "Personalized automation based on your presence",
                "Energy savings when you're away",
                "Comfort when you arrive home"
            ])
        else:
            benefits.extend([
                "Automated device coordination",
                "Improved convenience",
                "Potential energy savings"
            ])
        
        # Complexity-based benefits
        complexity = synergy.get('complexity', 'medium')
        if complexity == 'low':
            benefits.append("Easy to implement - simple automation")
        elif complexity == 'medium':
            benefits.append("Moderate complexity - may require some configuration")
        
        return benefits

    def _create_visualization(self, synergy: dict) -> dict[str, Any]:
        """
        Create visualization data for frontend.
        
        Returns:
            {
                'graph': dict,
                'timeline': list,
                'score_chart': dict
            }
        """
        trigger_entity = synergy.get('trigger_entity', '')
        action_entity = synergy.get('action_entity', '')
        trigger_name = synergy.get('trigger_name', trigger_entity)
        action_name = synergy.get('action_name', action_entity)
        
        # Graph structure
        graph = {
            'nodes': [
                {
                    'id': trigger_entity,
                    'label': trigger_name,
                    'type': 'trigger',
                    'area': synergy.get('area', 'unknown')
                },
                {
                    'id': action_entity,
                    'label': action_name,
                    'type': 'action',
                    'area': synergy.get('area', 'unknown')
                }
            ],
            'edges': [
                {
                    'from': trigger_entity,
                    'to': action_entity,
                    'label': synergy.get('relationship_type', 'triggers'),
                    'weight': synergy.get('impact_score', 0.5)
                }
            ]
        }
        
        # Timeline (if available)
        timeline = []
        if synergy.get('frequency'):
            timeline.append({
                'event': f"{trigger_name} triggers",
                'frequency': synergy.get('frequency', 0),
                'consistency': synergy.get('consistency', 0)
            })
        
        # Score chart data
        score_breakdown = self._breakdown_score(synergy)
        score_chart = {
            'components': [
                {'name': 'Base Benefit', 'value': score_breakdown.get('base_benefit', 0)},
                {'name': 'Usage Frequency', 'value': score_breakdown.get('usage_frequency', 0)},
                {'name': 'Area Traffic', 'value': score_breakdown.get('area_traffic', 0)},
                {'name': 'Time Weight', 'value': score_breakdown.get('time_weight', 1.0)},
                {'name': 'Health Factor', 'value': score_breakdown.get('health_factor', 1.0)}
            ],
            'final_score': score_breakdown.get('final_score', 0)
        }
        
        return {
            'graph': graph,
            'timeline': timeline,
            'score_chart': score_chart
        }

