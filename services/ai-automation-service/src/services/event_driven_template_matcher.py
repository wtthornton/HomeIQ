"""
Event-Driven Template Matching Service

Enhanced 2025: Immediate template matching when devices are added to Home Assistant.

Strategy from ai_automation_suggester:
- Subscribe to device registry create events
- Match device type to templates within 1-2 seconds
- Queue suggestion generation (non-blocking)
- Smart grouping for batch device additions
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventDrivenTemplateMatcher:
    """
    Event-driven template matching for immediate suggestions on device addition.
    
    Strategy:
    - Real-time device detection
    - Immediate template matching (< 2 seconds)
    - Non-blocking suggestion queue
    - Batch processing for multiple devices
    """

    def __init__(
        self,
        template_generator,
        data_api_client,
        db_session_factory=None
    ):
        """
        Initialize event-driven template matcher.
        
        Args:
            template_generator: DeviceTemplateGenerator instance
            data_api_client: DataAPIClient for fetching device data
            db_session_factory: Optional async function that returns DB session
        """
        self.template_generator = template_generator
        self.data_api_client = data_api_client
        self.db_session_factory = db_session_factory
        self.suggestion_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: asyncio.Task | None = None

    async def start(self):
        """Start the suggestion processing queue."""
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_suggestion_queue())
            logger.info("✅ Event-driven template matcher started")

    async def stop(self):
        """Stop the suggestion processing queue."""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 Event-driven template matcher stopped")

    async def on_device_added(
        self,
        device_id: str,
        device_type: str | None = None,
        device_data: dict[str, Any] | None = None
    ):
        """
        Handle device addition event.
        
        Strategy:
        - Immediate template matching (< 2 seconds)
        - Queue suggestion generation (non-blocking)
        - Smart grouping for batch additions
        
        Args:
            device_id: Device identifier
            device_type: Device type (if available)
            device_data: Optional device data dictionary
        """
        logger.info(f"📱 Device added: {device_id} (type: {device_type})")
        
        # Queue for processing
        await self.suggestion_queue.put({
            'device_id': device_id,
            'device_type': device_type,
            'device_data': device_data,
            'timestamp': datetime.now(timezone.utc)
        })
        
        logger.debug(f"Queued device {device_id} for template matching")

    async def on_devices_added_batch(
        self,
        devices: list[dict[str, Any]]
    ):
        """
        Handle batch device addition.
        
        Strategy:
        - Group similar devices
        - Batch template matching
        - Efficient processing
        
        Args:
            devices: List of device dictionaries with device_id, device_type, etc.
        """
        logger.info(f"📱 Batch device addition: {len(devices)} devices")
        
        # Group by device type for efficient processing
        devices_by_type: dict[str, list[dict[str, Any]]] = {}
        for device in devices:
            device_type = device.get('device_type', 'unknown')
            if device_type not in devices_by_type:
                devices_by_type[device_type] = []
            devices_by_type[device_type].append(device)
        
        # Queue each device
        for device in devices:
            await self.on_device_added(
                device_id=device.get('device_id'),
                device_type=device.get('device_type'),
                device_data=device
            )

    async def _process_suggestion_queue(self):
        """Process suggestion queue (background task)."""
        logger.info("🔄 Starting suggestion queue processor")
        
        while True:
            try:
                # Wait for device addition event
                device_event = await self.suggestion_queue.get()
                
                # Process immediately (non-blocking)
                asyncio.create_task(
                    self._generate_suggestions_for_device(device_event)
                )
                
                # Mark task as done
                self.suggestion_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Suggestion queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing suggestion queue: {e}", exc_info=True)

    async def _generate_suggestions_for_device(
        self,
        device_event: dict[str, Any]
    ):
        """
        Generate suggestions for a device (non-blocking).
        
        Strategy:
        - Fetch device entities
        - Match templates (< 2 seconds)
        - Generate top 3-5 suggestions
        - Store in database
        
        Args:
            device_event: Device event dictionary
        """
        device_id = device_event.get('device_id')
        device_type = device_event.get('device_type')
        
        if not device_id:
            return
        
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"🔍 Generating template suggestions for device {device_id}")
            
            # Fetch device entities
            try:
                entities = await self.data_api_client.fetch_entities(device_id=device_id)
            except Exception as e:
                logger.warning(f"Failed to fetch entities for {device_id}: {e}")
                entities = []
            
            # If no device_type, try to infer from entities
            if not device_type and entities:
                # Try to infer from entity domains
                domains = {e.get('entity_id', '').split('.')[0] for e in entities if e.get('entity_id')}
                # Simple mapping (can be enhanced)
                domain_to_type = {
                    'binary_sensor': 'motion_sensor',
                    'light': 'light',
                    'switch': 'switch',
                    'climate': 'thermostat',
                    'camera': 'camera',
                    'lock': 'lock'
                }
                for domain in domains:
                    if domain in domain_to_type:
                        device_type = domain_to_type[domain]
                        break
            
            if not device_type:
                logger.debug(f"Could not determine device type for {device_id}")
                return
            
            # Get all entities for template-based resolution
            all_entities = []
            try:
                all_entities = await self.data_api_client.fetch_entities(limit=1000)
            except Exception as e:
                logger.debug(f"Failed to fetch all entities: {e}")
            
            # Generate template suggestions
            template_suggestions = self.template_generator.suggest_device_automations(
                device_id=device_id,
                device_type=device_type,
                device_entities=entities,
                all_entities=all_entities,
                max_suggestions=5  # Top 5 templates
            )
            
            if not template_suggestions:
                logger.debug(f"No template suggestions for {device_id}")
                return
            
            # Store suggestions in database
            if self.db_session_factory:
                from ..database import store_suggestion
                from ..database.models import Suggestion
                
                db = await self.db_session_factory()
                try:
                    for template_sugg in template_suggestions:
                        suggestion_data = {
                            'pattern_id': None,
                            'title': template_sugg.get('title'),
                            'description': template_sugg.get('description'),
                            'automation_yaml': template_sugg.get('automation_yaml'),
                            'confidence': template_sugg.get('template_score', template_sugg.get('confidence', 0.8)),
                            'category': template_sugg.get('category', 'device_specific'),
                            'priority': 'medium',
                            'status': 'draft',
                            'device_id': device_id,
                            'devices_involved': [device_id],
                            'metadata': {
                                'source_type': 'event_driven_template',
                                'device_type': device_type,
                                'template_score': template_sugg.get('template_score', 0.8),
                                'template_match_quality': template_sugg.get('template_match_quality', 1.0),
                                'complexity': template_sugg.get('complexity', 'simple'),
                                'variants': template_sugg.get('variants', ['simple']),
                                'entity_mapping': template_sugg.get('entity_mapping', {}),
                                'generated_at': datetime.now(timezone.utc).isoformat()
                            }
                        }
                        
                        await store_suggestion(db, suggestion_data)
                    
                    await db.commit()
                    logger.info(f"✅ Stored {len(template_suggestions)} template suggestions for {device_id}")
                except Exception as e:
                    logger.error(f"Failed to store suggestions for {device_id}: {e}")
                    await db.rollback()
                finally:
                    await db.close()
            
            # Log performance
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"⚡ Template matching completed in {duration:.2f}s for {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions for {device_id}: {e}", exc_info=True)

