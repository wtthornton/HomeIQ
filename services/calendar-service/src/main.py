"""
Calendar Service Main Entry Point
Integrates with Home Assistant Calendar for occupancy prediction
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from aiohttp import web
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging, log_with_context, log_error_with_context
from shared.enhanced_ha_connection_manager import ha_connection_manager

from health_check import HealthCheckHandler
from ha_client import HomeAssistantCalendarClient
from event_parser import CalendarEventParser

load_dotenv()

logger = setup_logging("calendar-service")


class CalendarService:
    """Home Assistant Calendar integration for occupancy prediction"""
    
    def __init__(self):
        # Calendar configuration
        self.calendar_entities = os.getenv('CALENDAR_ENTITIES', 'calendar.primary').split(',')
        
        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')
        
        # Service configuration
        self.fetch_interval = int(os.getenv('CALENDAR_FETCH_INTERVAL', '900'))  # 15 minutes default
        
        # Components
        self.ha_client: Optional[HomeAssistantCalendarClient] = None
        self.event_parser = CalendarEventParser()
        self.influxdb_client: Optional[InfluxDBClient3] = None
        self.health_handler = HealthCheckHandler()
        
        # Validate InfluxDB configuration
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")
        
        # Clean up calendar entity list
        self.calendar_entities = [cal.strip() for cal in self.calendar_entities]
        logger.info(f"Configured for {len(self.calendar_entities)} calendar(s): {self.calendar_entities}")
    
    async def startup(self):
        """Initialize service"""
        logger.info("Initializing Calendar Service (Home Assistant Integration)...")
        
        # Get HA connection using the enhanced connection manager with circuit breaker protection
        connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()
        
        if not connection_config:
            logger.error("No Home Assistant connections available")
            self.health_handler.ha_connected = False
            raise ConnectionError("No Home Assistant connections available. Configure HA_HTTP_URL/HA_WS_URL + HA_TOKEN or NABU_CASA_URL + NABU_CASA_TOKEN")
        
        logger.info(f"Using HA connection: {connection_config.name} ({connection_config.url})")
        
        # Convert WebSocket URL to HTTP URL for calendar client
        http_url = connection_config.url.replace('ws://', 'http://').replace('wss://', 'https://')
        if http_url.endswith('/api/websocket'):
            http_url = http_url.replace('/api/websocket', '')
        
        # Initialize Home Assistant client
        self.ha_client = HomeAssistantCalendarClient(
            base_url=http_url,
            token=connection_config.token
        )
        
        await self.ha_client.connect()
        
        # Test connection
        connection_ok = await self.ha_client.test_connection()
        if not connection_ok:
            logger.error("Failed to connect to Home Assistant")
            self.health_handler.ha_connected = False
            raise ConnectionError(f"Cannot connect to Home Assistant at {http_url}")
        
        self.health_handler.ha_connected = True
        
        # Discover available calendars
        available_calendars = await self.ha_client.get_calendars()
        logger.info(f"Found {len(available_calendars)} calendar(s) in Home Assistant: {available_calendars}")
        
        # Validate configured calendars exist
        for calendar_id in self.calendar_entities:
            if calendar_id not in available_calendars and f"calendar.{calendar_id}" not in available_calendars:
                logger.warning(f"Configured calendar '{calendar_id}' not found in Home Assistant")
        
        self.health_handler.calendar_count = len(self.calendar_entities)
        
        # Create InfluxDB client
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )
        
        logger.info(f"Calendar Service initialized successfully")
    
    async def shutdown(self):
        """Cleanup"""
        logger.info("Shutting down Calendar Service...")
        
        if self.ha_client:
            await self.ha_client.close()
        
        if self.influxdb_client:
            self.influxdb_client.close()
    
    async def get_today_events(self) -> List[Dict[str, Any]]:
        """Fetch today's calendar events from Home Assistant"""
        
        try:
            # Define time range (today)
            now = datetime.now(timezone.utc)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Fetch events from all configured calendars
            all_events_raw = await self.ha_client.get_events_from_multiple_calendars(
                calendar_ids=self.calendar_entities,
                start=now,
                end=end_of_day
            )
            
            # Combine events from all calendars
            combined_events = []
            for calendar_id, events in all_events_raw.items():
                for event in events:
                    # Add calendar source to event
                    event['calendar_source'] = calendar_id
                    combined_events.append(event)
            
            logger.info(f"Fetched {len(combined_events)} events from {len(self.calendar_entities)} calendar(s)")
            
            # Parse and enrich events
            parsed_events = self.event_parser.parse_multiple_events(combined_events)
            
            # Sort by start time
            parsed_events.sort(key=lambda e: e['start'] if e.get('start') else now)
            
            self.health_handler.last_successful_fetch = datetime.now()
            self.health_handler.total_fetches += 1
            
            return parsed_events
            
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching calendar events: {e}",
                service="calendar-service",
                error=str(e)
            )
            self.health_handler.ha_connected = False
            self.health_handler.failed_fetches += 1
            return []
    
    async def predict_home_status(self) -> Dict[str, Any]:
        """Predict home occupancy based on calendar"""
        
        try:
            events = await self.get_today_events()
            now = datetime.now(timezone.utc)
            
            if not events:
                logger.info("No calendar events found, assuming default status")
                return {
                    'currently_home': False,
                    'wfh_today': False,
                    'next_arrival': None,
                    'prepare_time': None,
                    'hours_until_arrival': None,
                    'confidence': 0.5,  # Low confidence with no data
                    'timestamp': datetime.now(timezone.utc),
                    'event_count': 0
                }
            
            # Check if working from home today
            wfh_today = any(e.get('is_wfh', False) for e in events)
            
            # Get current events using parser helper
            current_events = self.event_parser.get_current_events(events, now)
            
            # Check if currently home based on current events
            currently_home = wfh_today or any(e.get('is_home', False) for e in current_events)
            
            # Get upcoming events
            future_events = self.event_parser.get_upcoming_events(events, now)
            
            # Find next home event
            next_home_event = next((e for e in future_events if e.get('is_home', False)), None)
            
            # Calculate arrival time and confidence
            if next_home_event:
                arrival_time = next_home_event['start']
                travel_time = timedelta(minutes=30)  # Estimate
                prepare_time = arrival_time - travel_time
                hours_until_arrival = (arrival_time - now).total_seconds() / 3600
                
                # Use event's confidence if available
                confidence = next_home_event.get('confidence', 0.75)
            else:
                arrival_time = None
                prepare_time = None
                hours_until_arrival = None
                confidence = 0.85 if wfh_today else 0.70
            
            # Adjust confidence based on multiple factors
            if wfh_today and currently_home:
                confidence = max(confidence, 0.90)  # High confidence if WFH today
            elif currently_home and current_events:
                confidence = max(confidence, 0.85)  # High confidence with current home events
            
            prediction = {
                'currently_home': currently_home,
                'wfh_today': wfh_today,
                'next_arrival': arrival_time,
                'prepare_time': prepare_time,
                'hours_until_arrival': hours_until_arrival,
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc),
                'event_count': len(events),
                'current_event_count': len(current_events),
                'upcoming_event_count': len(future_events)
            }
            
            logger.info(
                f"Occupancy prediction: Home={currently_home}, WFH={wfh_today}, "
                f"Events={len(events)}, Confidence={confidence:.2f}"
            )
            
            return prediction
            
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error predicting occupancy: {e}",
                service="calendar-service",
                error=str(e)
            )
            self.health_handler.failed_fetches += 1
            return None
    
    async def store_in_influxdb(self, prediction: Dict[str, Any]):
        """Store occupancy prediction in InfluxDB"""
        
        if not prediction:
            return
        
        try:
            point = Point("occupancy_prediction") \
                .tag("source", "calendar") \
                .tag("user", "primary") \
                .field("currently_home", bool(prediction['currently_home'])) \
                .field("wfh_today", bool(prediction['wfh_today'])) \
                .field("confidence", float(prediction['confidence'])) \
                .field("hours_until_arrival", float(prediction['hours_until_arrival']) if prediction['hours_until_arrival'] is not None else 0) \
                .time(prediction['timestamp'])
            
            self.influxdb_client.write(point)
            
            logger.info("Occupancy prediction written to InfluxDB")
            
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="calendar-service",
                error=str(e)
            )
    
    async def run_continuous(self):
        """Run continuous prediction loop"""
        
        logger.info(f"Starting continuous occupancy prediction (every {self.fetch_interval}s)")
        
        while True:
            try:
                # Get prediction
                prediction = await self.predict_home_status()
                
                # Store in InfluxDB
                if prediction:
                    await self.store_in_influxdb(prediction)
                
                # Mark as healthy after successful fetch and store
                self.health_handler.ha_connected = True
                
                await asyncio.sleep(self.fetch_interval)
                
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="calendar-service",
                    error=str(e)
                )
                self.health_handler.ha_connected = False
                # Wait 5 minutes before retry on error
                await asyncio.sleep(300)


async def create_app(service: CalendarService):
    """Create web application"""
    app = web.Application()
    app.router.add_get('/health', service.health_handler.handle)
    return app


async def main():
    """Main entry point"""
    logger.info("Starting Calendar Service...")
    
    service = CalendarService()
    await service.startup()
    
    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('SERVICE_PORT', '8013'))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"API endpoints available on port {port}")
    
    try:
        await service.run_continuous()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await service.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

