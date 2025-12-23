"""
Calendar Correlation Integration

Epic 38, Story 38.1: Calendar Integration Foundation
Integrates calendar service (Epic 34) with correlation analysis for presence-aware correlations.

Single-home NUC optimized:
- Memory: <10MB (lightweight, cached queries)
- Performance: <10ms per query (with caching)
- Graceful fallback when calendar service unavailable
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from collections import OrderedDict

import aiohttp
from aiohttp import ClientError, ClientTimeout

from shared.logging_config import get_logger

logger = get_logger(__name__)


class CalendarCorrelationIntegration:
    """
    Integrates calendar service with correlation analysis.
    
    Provides presence-aware correlation features:
    - Current presence state (home/away)
    - Predicted presence (next N hours)
    - Presence patterns over time
    
    Single-home optimization:
    - Lightweight presence tracking
    - Cached calendar queries (1 hour TTL)
    - Graceful fallback when calendar unavailable
    """
    
    def __init__(
        self,
        calendar_service_url: Optional[str] = None,
        cache_ttl: timedelta = timedelta(hours=1),
        max_cache_size: int = 100
    ):
        """
        Initialize calendar correlation integration.
        
        Args:
            calendar_service_url: Calendar service URL (default: http://calendar-service:8013)
            cache_ttl: Cache TTL for calendar queries
            max_cache_size: Maximum cache size for presence queries
        """
        self.calendar_service_url = calendar_service_url or "http://calendar-service:8013"
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        
        # HTTP session for calendar service
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = ClientTimeout(total=5)  # 5 second timeout
        
        # Presence state cache (timestamp -> presence state)
        self.presence_cache: OrderedDict[datetime, Dict] = OrderedDict()
        
        # Calendar service availability
        self.calendar_available = True
        
        logger.info(
            "CalendarCorrelationIntegration initialized (url=%s, cache_ttl=%s)",
            self.calendar_service_url,
            cache_ttl
        )
    
    async def connect(self) -> None:
        """Initialize HTTP session for calendar service"""
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            logger.info("Calendar service HTTP session created")
    
    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Calendar service HTTP session closed")
    
    async def get_current_presence(self, timestamp: Optional[datetime] = None) -> Optional[Dict]:
        """
        Get current presence state.
        
        Args:
            timestamp: Optional timestamp (default: now)
        
        Returns:
            Dict with presence state or None if unavailable:
            {
                'currently_home': bool,
                'wfh_today': bool,
                'confidence': float,
                'timestamp': datetime
            }
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Check cache
        cache_key = timestamp.replace(minute=0, second=0, microsecond=0)  # Hourly cache
        if cache_key in self.presence_cache:
            cached = self.presence_cache[cache_key]
            age = timestamp - cached['timestamp']
            if age < self.cache_ttl:
                logger.debug("Presence cache hit for %s", cache_key)
                return cached['data']
        
        # Query calendar service (via InfluxDB or direct query)
        # For now, we'll query InfluxDB for occupancy predictions
        # stored by calendar service
        try:
            await self.connect()
            
            # Query InfluxDB for latest occupancy prediction
            # This is a simplified approach - in production, we'd use data-api
            presence = await self._query_presence_from_influxdb(timestamp)
            
            if presence:
                # Cache result
                self._cache_presence(cache_key, presence, timestamp)
                return presence
            else:
                # Fallback: assume home if no data
                logger.warning("No presence data available, using fallback")
                return {
                    'currently_home': True,  # Conservative default
                    'wfh_today': False,
                    'confidence': 0.5,
                    'timestamp': timestamp
                }
        
        except Exception as e:
            logger.warning("Failed to get presence from calendar service: %s", e)
            self.calendar_available = False
            
            # Graceful fallback
            return {
                'currently_home': True,  # Conservative default
                'wfh_today': False,
                'confidence': 0.3,  # Low confidence for fallback
                'timestamp': timestamp
            }
    
    async def get_predicted_presence(
        self,
        hours_ahead: int = 24,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Get predicted presence for next N hours.
        
        Args:
            hours_ahead: Number of hours to predict ahead
            timestamp: Optional timestamp (default: now)
        
        Returns:
            Dict with predicted presence or None if unavailable:
            {
                'next_arrival': datetime,
                'next_departure': datetime,
                'will_be_home': bool,
                'confidence': float,
                'timestamp': datetime
            }
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        try:
            await self.connect()
            
            # Query InfluxDB for future occupancy predictions
            prediction = await self._query_future_presence_from_influxdb(
                timestamp,
                hours_ahead
            )
            
            if prediction:
                return prediction
            else:
                # Fallback: assume will be home
                return {
                    'next_arrival': None,
                    'next_departure': None,
                    'will_be_home': True,
                    'confidence': 0.5,
                    'timestamp': timestamp
                }
        
        except Exception as e:
            logger.warning("Failed to get predicted presence: %s", e)
            return None
    
    def extract_presence_features(
        self,
        presence: Optional[Dict] = None,
        predicted_presence: Optional[Dict] = None
    ) -> Dict:
        """
        Extract presence features for correlation analysis.
        
        Args:
            presence: Current presence state (from get_current_presence)
            predicted_presence: Predicted presence (from get_predicted_presence)
        
        Returns:
            Dict with presence features:
            {
                'currently_home': float (0.0 or 1.0),
                'wfh_today': float (0.0 or 1.0),
                'presence_confidence': float,
                'hours_until_arrival': float (or None),
                'will_be_home_next_24h': float (0.0 or 1.0)
            }
        """
        features = {}
        
        if presence:
            features['currently_home'] = 1.0 if presence.get('currently_home', False) else 0.0
            features['wfh_today'] = 1.0 if presence.get('wfh_today', False) else 0.0
            features['presence_confidence'] = presence.get('confidence', 0.5)
            
            hours_until = presence.get('hours_until_arrival')
            if hours_until is not None:
                features['hours_until_arrival'] = float(hours_until)
            else:
                features['hours_until_arrival'] = None
        else:
            # Default values if no presence data
            features['currently_home'] = 0.5  # Unknown
            features['wfh_today'] = 0.0
            features['presence_confidence'] = 0.0
            features['hours_until_arrival'] = None
        
        if predicted_presence:
            features['will_be_home_next_24h'] = 1.0 if predicted_presence.get('will_be_home', False) else 0.0
        else:
            features['will_be_home_next_24h'] = 0.5  # Unknown
        
        return features
    
    async def _query_presence_from_influxdb(
        self,
        timestamp: datetime
    ) -> Optional[Dict]:
        """
        Query InfluxDB for latest occupancy prediction.
        
        Calendar service stores occupancy predictions in InfluxDB with:
        - Measurement: "occupancy_prediction"
        - Fields: currently_home, wfh_today, confidence, hours_until_arrival
        - Tags: source="calendar", user="primary"
        
        Args:
            timestamp: Timestamp for query
        
        Returns:
            Presence state dict or None
        """
        try:
            from influxdb_client import InfluxDBClient
            
            # Get InfluxDB configuration from environment
            import os
            influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
            influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
            influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
            influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
            
            # Create InfluxDB client
            client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
            query_api = client.query_api()
            
            # Query for latest occupancy prediction (last 24 hours)
            start_time = timestamp - timedelta(hours=24)
            flux_query = f'''
                from(bucket: "{influxdb_bucket}")
                  |> range(start: {start_time.isoformat()}Z, stop: {timestamp.isoformat()}Z)
                  |> filter(fn: (r) => r["_measurement"] == "occupancy_prediction")
                  |> filter(fn: (r) => r["source"] == "calendar")
                  |> sort(columns: ["_time"], desc: true)
                  |> limit(n: 1)
            '''
            
            tables = query_api.query(flux_query, org=influxdb_org)
            
            # Parse result
            for table in tables:
                for record in table.records:
                    # Extract fields from record
                    currently_home = None
                    wfh_today = None
                    confidence = None
                    hours_until_arrival = None
                    
                    # Get field values
                    field = record.get_field()
                    value = record.get_value()
                    
                    if field == "currently_home":
                        currently_home = bool(value)
                    elif field == "wfh_today":
                        wfh_today = bool(value)
                    elif field == "confidence":
                        confidence = float(value)
                    elif field == "hours_until_arrival":
                        hours_until_arrival = float(value) if value is not None else None
                    
                    # If we have at least one field, return presence state
                    if currently_home is not None or wfh_today is not None:
                        return {
                            'currently_home': currently_home if currently_home is not None else True,
                            'wfh_today': wfh_today if wfh_today is not None else False,
                            'confidence': confidence if confidence is not None else 0.5,
                            'hours_until_arrival': hours_until_arrival,
                            'timestamp': record.get_time()
                        }
            
            client.close()
            return None
            
        except ImportError:
            logger.warning("influxdb_client not available, cannot query InfluxDB")
            return None
        except Exception as e:
            logger.warning("Failed to query InfluxDB for presence: %s", e)
            return None
    
    async def _query_future_presence_from_influxdb(
        self,
        timestamp: datetime,
        hours_ahead: int
    ) -> Optional[Dict]:
        """
        Query InfluxDB for future occupancy predictions.
        
        Calendar service stores predictions with next_arrival times.
        We query for predictions within the next N hours.
        
        Args:
            timestamp: Current timestamp
            hours_ahead: Hours to look ahead
        
        Returns:
            Predicted presence dict or None
        """
        try:
            from influxdb_client import InfluxDBClient
            
            # Get InfluxDB configuration
            import os
            influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
            influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
            influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
            influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
            
            # Create InfluxDB client
            client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
            query_api = client.query_api()
            
            # Query for predictions with next_arrival in the future
            end_time = timestamp + timedelta(hours=hours_ahead)
            flux_query = f'''
                from(bucket: "{influxdb_bucket}")
                  |> range(start: {timestamp.isoformat()}Z, stop: {end_time.isoformat()}Z)
                  |> filter(fn: (r) => r["_measurement"] == "occupancy_prediction")
                  |> filter(fn: (r) => r["source"] == "calendar")
                  |> filter(fn: (r) => exists r["hours_until_arrival"] and r["hours_until_arrival"] > 0)
                  |> sort(columns: ["_time"], desc: false)
                  |> limit(n: 1)
            '''
            
            tables = query_api.query(flux_query, org=influxdb_org)
            
            # Parse result
            for table in tables:
                for record in table.records:
                    hours_until = record.get_value() if record.get_field() == "hours_until_arrival" else None
                    
                    if hours_until is not None and hours_until > 0:
                        next_arrival = timestamp + timedelta(hours=float(hours_until))
                        return {
                            'next_arrival': next_arrival,
                            'next_departure': None,  # Not stored in current schema
                            'will_be_home': True,  # If arrival predicted, will be home
                            'confidence': 0.75,  # Default confidence
                            'timestamp': timestamp
                        }
            
            client.close()
            return None
            
        except ImportError:
            logger.warning("influxdb_client not available, cannot query InfluxDB")
            return None
        except Exception as e:
            logger.warning("Failed to query InfluxDB for future presence: %s", e)
            return None
    
    def _cache_presence(
        self,
        cache_key: datetime,
        data: Dict,
        timestamp: datetime
    ) -> None:
        """Cache presence data"""
        # Add to cache
        self.presence_cache[cache_key] = {
            'data': data,
            'timestamp': timestamp
        }
        
        # Enforce max cache size
        while len(self.presence_cache) > self.max_cache_size:
            self.presence_cache.popitem(last=False)  # Remove oldest
        
        logger.debug("Cached presence data for %s", cache_key)
    
    def is_available(self) -> bool:
        """Check if calendar service is available"""
        return self.calendar_available

