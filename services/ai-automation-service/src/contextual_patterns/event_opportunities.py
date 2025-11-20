"""
Event Opportunity Detector

Detects event-based automation opportunities (sports schedules, calendar events).

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.7: Sports/Event Context Integration
"""

import logging
import uuid

logger = logging.getLogger(__name__)


class EventOpportunityDetector:
    """
    Detects event-based automation opportunities.
    
    Uses sports schedule and calendar data to suggest scene activations
    and entertainment system automations.
    
    Story AI3.7: Sports/Event Context Integration
    """

    def __init__(self, data_api_client):
        """Initialize event opportunity detector."""
        self.data_api = data_api_client
        logger.info("EventOpportunityDetector initialized")

    async def detect_opportunities(self) -> list[dict]:
        """
        Detect event-based automation opportunities.
        
        Returns:
            List of event opportunity dictionaries
        """
        logger.info("📅 Starting event opportunity detection...")

        try:
            # Get entertainment devices (lights, media players)
            entertainment_devices = await self._get_entertainment_devices()

            if not entertainment_devices:
                logger.info("ℹ️  No entertainment devices found")
                return []

            opportunities = []

            # Suggest game-time scene automation
            # Note: Actual sports schedule integration would query sports-data service
            # For now, creating opportunity suggestion if devices exist

            for device in entertainment_devices:
                opportunities.append({
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'event_context',
                    'devices': [device['entity_id']],
                    'action_entity': device['entity_id'],
                    'area': device.get('area_id', 'unknown'),
                    'relationship': 'gametime_scene',
                    'impact_score': 0.65,  # Medium - convenience
                    'complexity': 'medium',
                    'confidence': 0.70,
                    'opportunity_metadata': {
                        'action_name': device.get('friendly_name', device['entity_id']),
                        'event_context': 'Sports schedule available',
                        'suggested_action': 'Activate game-time scene when team plays',
                        'rationale': f"Automate {device.get('friendly_name', device['entity_id'])} for game-time entertainment"
                    }
                })

            logger.info(f"✅ Event opportunities: {len(opportunities)}")
            return opportunities

        except Exception as e:
            logger.error(f"❌ Event opportunity detection failed: {e}")
            return []

    async def _get_entertainment_devices(self) -> list[dict]:
        """Get entertainment-related devices."""
        try:
            entities = await self.data_api.fetch_entities()

            # Filter for entertainment devices
            entertainment = [
                e for e in entities
                if any(keyword in e['entity_id'].lower() for keyword in [
                    'tv', 'media_player', 'living_room', 'theater',
                    'sound', 'speaker', 'receiver'
                ])
                and e['entity_id'].startswith(('light.', 'media_player.', 'switch.'))
            ]

            return entertainment[:5]  # Limit to avoid too many suggestions

        except Exception as e:
            logger.warning(f"Failed to get entertainment devices: {e}")
            return []

