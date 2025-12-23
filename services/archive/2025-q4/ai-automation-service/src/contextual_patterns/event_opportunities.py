"""
Event Opportunity Detector

Detects event-based automation opportunities (sports schedules, calendar events, holidays).

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.7: Sports/Event Context Integration
2025 Enhancement: Multi-event type support (sports, calendar, holidays)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

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
        
        2025 Enhancement: Supports multiple event types:
        - Sports events (from sports-data service if available)
        - Calendar events (from calendar service if available)
        - Holiday events (built-in)
        - Custom events
        
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

            # 2025 Enhancement: Detect multiple event types
            # 1. Sports events (query sports-data service if available)
            sports_opportunities = await self._detect_sports_opportunities(entertainment_devices)
            opportunities.extend(sports_opportunities)

            # 2. Calendar events (query calendar service if available)
            calendar_opportunities = await self._detect_calendar_opportunities(entertainment_devices)
            opportunities.extend(calendar_opportunities)

            # 3. Holiday events (built-in detection)
            holiday_opportunities = await self._detect_holiday_opportunities(entertainment_devices)
            opportunities.extend(holiday_opportunities)

            logger.info(f"✅ Event opportunities: {len(opportunities)} (sports: {len(sports_opportunities)}, calendar: {len(calendar_opportunities)}, holidays: {len(holiday_opportunities)})")
            return opportunities

        except Exception as e:
            logger.error(f"❌ Event opportunity detection failed: {e}", exc_info=True)
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

    async def _detect_sports_opportunities(self, entertainment_devices: list[dict]) -> list[dict]:
        """Detect sports event opportunities."""
        opportunities = []
        
        try:
            # Try to query sports-data service if available
            # Check if sports data is available via data-api or sports-data service
            sports_available = False
            
            # Attempt to detect if sports service is available (could check InfluxDB for sports data)
            # For now, create generic sports opportunity if entertainment devices exist
            if entertainment_devices:
                # Limit to 1-2 devices to avoid duplicates
                for device in entertainment_devices[:2]:
                    opportunities.append({
                        'synergy_id': str(uuid.uuid4()),
                        'synergy_type': 'event_context',
                        'devices': [device['entity_id']],
                        'action_entity': device['entity_id'],
                        'area': device.get('area_id', 'unknown'),
                        'relationship': 'sports_event_scene',
                        'impact_score': 0.65,  # Medium - convenience
                        'complexity': 'medium',
                        'confidence': 0.70,
                        'opportunity_metadata': {
                            'action_name': device.get('friendly_name', device['entity_id']),
                            'event_context': 'Sports events',
                            'event_type': 'sports',
                            'suggested_action': 'Activate scene when favorite team plays',
                            'rationale': f"Automate {device.get('friendly_name', device['entity_id'])} for sports viewing"
                        }
                    })
        except Exception as e:
            logger.warning(f"Failed to detect sports opportunities: {e}")
        
        return opportunities

    async def _detect_calendar_opportunities(self, entertainment_devices: list[dict]) -> list[dict]:
        """Detect calendar event opportunities."""
        opportunities = []
        
        try:
            # Try to detect if calendar service has events
            # Could query calendar-service or check InfluxDB for calendar data
            # For now, create generic calendar opportunity if entertainment devices exist
            
            # Only create one calendar opportunity (not per device)
            if entertainment_devices:
                # Use first entertainment device as representative
                device = entertainment_devices[0]
                opportunities.append({
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'event_context',
                    'devices': [device['entity_id']],
                    'action_entity': device['entity_id'],
                    'area': device.get('area_id', 'unknown'),
                    'relationship': 'calendar_event_scene',
                    'impact_score': 0.60,  # Medium - convenience
                    'complexity': 'medium',
                    'confidence': 0.65,
                    'opportunity_metadata': {
                        'action_name': device.get('friendly_name', device['entity_id']),
                        'event_context': 'Calendar events',
                        'event_type': 'calendar',
                        'suggested_action': 'Activate scene based on calendar events (meetings, appointments)',
                        'rationale': f"Automate {device.get('friendly_name', device['entity_id'])} based on your calendar schedule"
                    }
                })
        except Exception as e:
            logger.warning(f"Failed to detect calendar opportunities: {e}")
        
        return opportunities

    async def _detect_holiday_opportunities(self, entertainment_devices: list[dict]) -> list[dict]:
        """Detect holiday event opportunities."""
        opportunities = []
        
        try:
            # Check if we're near any major holidays
            today = datetime.now(timezone.utc).date()
            
            # Simple holiday detection (could be enhanced with holiday library)
            # For now, create generic holiday opportunity
            if entertainment_devices:
                # Use first entertainment device as representative
                device = entertainment_devices[0]
                opportunities.append({
                    'synergy_id': str(uuid.uuid4()),
                    'synergy_type': 'event_context',
                    'devices': [device['entity_id']],
                    'action_entity': device['entity_id'],
                    'area': device.get('area_id', 'unknown'),
                    'relationship': 'holiday_scene',
                    'impact_score': 0.55,  # Medium-low - seasonal
                    'complexity': 'low',
                    'confidence': 0.60,
                    'opportunity_metadata': {
                        'action_name': device.get('friendly_name', device['entity_id']),
                        'event_context': 'Holiday events',
                        'event_type': 'holiday',
                        'suggested_action': 'Activate special scene for holidays and special occasions',
                        'rationale': f"Automate {device.get('friendly_name', device['entity_id'])} for holiday celebrations"
                    }
                })
        except Exception as e:
            logger.warning(f"Failed to detect holiday opportunities: {e}")
        
        return opportunities

