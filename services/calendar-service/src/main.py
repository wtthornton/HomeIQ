"""
Calendar Service Main Entry Point
Integrates with Google Calendar for occupancy prediction
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from aiohttp import web
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging, log_with_context, log_error_with_context

from health_check import HealthCheckHandler

load_dotenv()

logger = setup_logging("calendar-service")


class CalendarService:
    """Google Calendar integration for occupancy prediction"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')
        
        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')
        
        # Service configuration
        self.fetch_interval = 900  # 15 minutes
        
        # Components
        self.calendar_service = None
        self.credentials = None
        self.influxdb_client: Optional[InfluxDBClient3] = None
        self.health_handler = HealthCheckHandler()
        
        # Validate
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise ValueError("Google OAuth credentials required: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")
    
    async def startup(self):
        """Initialize service"""
        logger.info("Initializing Calendar Service...")
        
        # Setup OAuth credentials
        self.credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Refresh token
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        
        # Build calendar service
        self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
        
        self.health_handler.oauth_valid = True
        
        # Create InfluxDB client
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )
        
        logger.info("Calendar Service initialized")
    
    async def shutdown(self):
        """Cleanup"""
        logger.info("Shutting down Calendar Service...")
        
        if self.influxdb_client:
            self.influxdb_client.close()
    
    async def get_today_events(self) -> List[Dict[str, Any]]:
        """Fetch today's calendar events"""
        
        try:
            now = datetime.now().isoformat() + 'Z'
            end_of_day = (datetime.now().replace(hour=23, minute=59)).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = []
            for event in events_result.get('items', []):
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                events.append({
                    'summary': event.get('summary', 'Untitled'),
                    'location': event.get('location', ''),
                    'start': datetime.fromisoformat(start_str.replace('Z', '+00:00')),
                    'end': datetime.fromisoformat(end_str.replace('Z', '+00:00')),
                    'is_wfh': 'WFH' in event.get('summary', '').upper() or 
                             'HOME' in event.get('location', '').upper()
                })
            
            return events
            
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching calendar events: {e}",
                service="calendar-service",
                error=str(e)
            )
            self.health_handler.oauth_valid = False
            return []
    
    async def predict_home_status(self) -> Dict[str, Any]:
        """Predict home occupancy based on calendar"""
        
        try:
            events = await self.get_today_events()
            now = datetime.now()
            
            # Check if working from home today
            wfh_today = any(e['is_wfh'] for e in events)
            
            # Check current events
            current_events = [e for e in events if e['start'] <= now <= e['end']]
            currently_home = wfh_today or any('HOME' in e.get('location', '').upper() for e in current_events)
            
            # Find next home event
            future_events = [e for e in events if e['start'] > now]
            next_home_event = next((e for e in future_events if 'HOME' in e.get('location', '').upper()), None)
            
            # Calculate arrival time
            if next_home_event:
                arrival_time = next_home_event['start']
                travel_time = timedelta(minutes=30)  # Estimate
                prepare_time = arrival_time - travel_time
                hours_until_arrival = (arrival_time - now).total_seconds() / 3600
            else:
                arrival_time = None
                prepare_time = None
                hours_until_arrival = None
            
            prediction = {
                'currently_home': currently_home,
                'wfh_today': wfh_today,
                'next_arrival': arrival_time,
                'prepare_time': prepare_time,
                'hours_until_arrival': hours_until_arrival,
                'confidence': 0.85 if wfh_today else 0.70,
                'timestamp': datetime.now()
            }
            
            self.health_handler.last_successful_fetch = datetime.now()
            self.health_handler.total_fetches += 1
            
            logger.info(f"Occupancy prediction: Home={currently_home}, WFH={wfh_today}")
            
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
                # Refresh OAuth token if needed
                if not self.credentials.valid:
                    self.credentials.refresh(Request())
                    self.health_handler.oauth_valid = True
                
                # Get prediction
                prediction = await self.predict_home_status()
                
                # Store in InfluxDB
                if prediction:
                    await self.store_in_influxdb(prediction)
                
                await asyncio.sleep(self.fetch_interval)
                
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="calendar-service",
                    error=str(e)
                )
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

