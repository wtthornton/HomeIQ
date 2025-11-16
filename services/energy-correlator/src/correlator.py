"""
Energy-Event Correlation Engine
Analyzes relationships between HA events and power consumption changes
"""

import logging
from bisect import bisect_left
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from influxdb_client import Point

from .influxdb_wrapper import InfluxDBWrapper

logger = logging.getLogger(__name__)


class EnergyEventCorrelator:
    """
    Correlates Home Assistant events with power consumption changes
    Creates derived metrics in InfluxDB for analysis
    """
    
    def __init__(
        self,
        influxdb_url: str,
        influxdb_token: str,
        influxdb_org: str,
        influxdb_bucket: str,
        *,
        correlation_window_seconds: int = 10,
        min_power_delta: float = 10.0,
        max_events_per_interval: int = 500,
        power_lookup_padding_seconds: int = 30,
        max_retry_queue_size: int = 250,
        retry_window_minutes: int = 5
    ):
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        self.client: Optional[InfluxDBWrapper] = None
        
        # Configuration
        self.correlation_window_seconds = max(1, int(correlation_window_seconds))  # Look +/- window
        self.min_power_delta = float(min_power_delta)  # Minimum change to correlate
        self.max_events_per_interval = max(1, int(max_events_per_interval))
        self.power_lookup_padding_seconds = max(
            self.correlation_window_seconds,
            int(power_lookup_padding_seconds)
        )
        self.max_retry_queue_size = max(0, int(max_retry_queue_size))
        self.retry_window_minutes = max(1, int(retry_window_minutes))
        
        # Runtime caches
        self._pending_events: List[Dict[str, Any]] = []
        self._power_cache: Optional[Dict[str, List[float]]] = None
        
        # Statistics
        self.total_events_processed = 0
        self.correlations_found = 0
        self.correlations_written = 0
        self.errors = 0
    
    async def startup(self):
        """Initialize InfluxDB connection"""
        try:
            self.client = InfluxDBWrapper(
                self.influxdb_url,
                self.influxdb_token,
                self.influxdb_org,
                self.influxdb_bucket
            )
            
            self.client.connect()
            logger.info(f"Energy correlator connected to InfluxDB at {self.influxdb_url}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup"""
        if self.client:
            try:
                self.client.close()
                logger.info("Energy correlator shut down")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
    
    async def process_recent_events(self, lookback_minutes: int = 5):
        """
        Process recent events and create correlations
        
        Args:
            lookback_minutes: How far back to process events (default: 5 minutes)
        """
        logger.info(f"Processing events from last {lookback_minutes} minutes")
        
        power_cache_built = False
        
        try:
            # Query recent events
            events = await self._query_recent_events(lookback_minutes)
            original_event_count = len(events)
            
            # Merge with pending retries
            events = self._merge_pending_events(events, lookback_minutes)
            
            if not events:
                logger.debug("No events to process")
                self._pending_events = []
                return
            
            logger.info(
                f"Processing {len(events)} events "
                f"(queried={original_event_count}, pending={len(self._pending_events)})"
            )
            
            # Build power cache covering entire window
            self._power_cache = await self._build_power_cache(events)
            power_cache_built = True
            
            batch_points: List[Point] = []
            deferred_events: List[Dict[str, Any]] = []
            
            # Process each event
            for event in events:
                point = await self._correlate_event_with_power(
                    event,
                    retry_queue=deferred_events,
                    write_result=False
                )
                
                if point:
                    batch_points.append(point)
            
            if batch_points:
                await self._write_correlation_points(batch_points)
            
            # Track deferred events for retry (if any)
            self._pending_events = self._trim_pending_events(
                deferred_events,
                lookback_minutes
            )
            
            if self._pending_events:
                logger.debug(f"Deferred {len(self._pending_events)} events for retry")
            
            logger.info(
                f"Processed {self.total_events_processed} events, "
                f"found {self.correlations_found} correlations, "
                f"wrote {self.correlations_written} to InfluxDB"
            )
            
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            self.errors += 1
            raise
        finally:
            if power_cache_built:
                self._power_cache = None
    
    async def _query_recent_events(self, minutes: int) -> List[Dict]:
        """
        Query recent HA events that could affect power consumption
        
        Focuses on:
        - Switches (lights, plugs)
        - Climate devices (HVAC, thermostats)
        - Fans
        - Covers (blinds - affect heating/cooling)
        """
        
        # Calculate time range
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=minutes)
        
        # Flux query for InfluxDB 2.x with batching limits
        flux_query = f'''
        from(bucket: "{self.influxdb_bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {now.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
          |> filter(fn: (r) => 
              r["domain"] == "switch" or 
              r["domain"] == "light" or 
              r["domain"] == "climate" or 
              r["domain"] == "fan" or 
              r["domain"] == "cover"
          )
          |> filter(fn: (r) => r["_field"] == "state_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {self.max_events_per_interval})
          |> sort(columns: ["_time"])
        '''
        
        try:
            logger.debug(f"Querying events since {start_time.isoformat()}")
            results = await self.client.query(flux_query)
            
            # Convert to event format
            events = []
            for record in results:
                event_time = record.get('time')
                if not isinstance(event_time, datetime):
                    continue
                
                events.append({
                    'time': event_time,
                    'entity_id': record.get('entity_id', ''),
                    'domain': record.get('domain', ''),
                    'state': record.get('_value', ''),
                    'previous_state': record.get('previous_state', '')
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error querying events: {e}")
            raise
    
    async def _correlate_event_with_power(
        self,
        event: Dict,
        *,
        retry_queue: Optional[List[Dict[str, Any]]] = None,
        write_result: bool = True
    ):
        """
        Correlate a single event with power changes
        
        Looks for power changes within ±10 seconds of the event
        
        Args:
            event: Event data with time, entity_id, state, previous_state
        """
        self.total_events_processed += 1
        
        event_time = event.get('time')
        entity_id = event.get('entity_id')
        domain = event.get('domain')
        state = event.get('state')
        previous_state = event.get('previous_state')
        
        # Get power before event (within correlation window)
        time_before = event_time - timedelta(seconds=self.correlation_window_seconds / 2)
        power_before = await self._get_power_at_time(time_before)
        
        # Get power after event
        time_after = event_time + timedelta(seconds=self.correlation_window_seconds / 2)
        power_after = await self._get_power_at_time(time_after)
        
        if power_before is None or power_after is None:
            logger.debug(f"No power data found for event {entity_id} at {event_time}")
            if retry_queue is not None:
                retry_queue.append(event)
            return
        
        # Calculate delta
        power_delta = power_after - power_before
        
        # Check if significant change
        if abs(power_delta) < self.min_power_delta:
            logger.debug(
                f"Power change too small for {entity_id}: {power_delta:.1f}W "
                f"(threshold: {self.min_power_delta}W)"
            )
            return
        
        self.correlations_found += 1
        
        point = self._build_correlation_point(
            event_time=event_time,
            entity_id=entity_id,
            domain=domain,
            state=state,
            previous_state=previous_state,
            power_before=power_before,
            power_after=power_after,
            power_delta=power_delta
        )
        
        if point and write_result:
            await self._write_correlation_points([point])
        
        return point
    
    async def _get_power_at_time(self, target_time: datetime) -> Optional[float]:
        """
        Get power reading closest to target time
        
        Looks within ±30 seconds of target time
        
        Args:
            target_time: Target timestamp
            
        Returns:
            Power reading in watts, or None if not found
        """
        
        if self._power_cache:
            cached_value = self._lookup_power_in_cache(target_time, self._power_cache)
            if cached_value is not None:
                return cached_value
        
        start_time = target_time - timedelta(seconds=self.power_lookup_padding_seconds)
        end_time = target_time + timedelta(seconds=self.power_lookup_padding_seconds)
        
        # Flux query for smart_meter measurement
        flux_query = f'''
        from(bucket: "{self.influxdb_bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w")
          |> sort(columns: ["_time"])
          |> limit(n: 1)
        '''
        
        try:
            results = await self.client.query(flux_query)
            
            if results:
                power = results[0].get('_value')
                if power is not None:
                    return float(power)
            
            return None
            
        except Exception as e:
            logger.error(f"Error querying power: {e}")
            raise
    
    def _build_correlation_point(
        self,
        event_time: datetime,
        entity_id: str,
        domain: str,
        state: str,
        previous_state: str,
        power_before: float,
        power_after: float,
        power_delta: float
    ) -> Optional[Point]:
        """Build correlation data point"""
        if power_before is None or power_after is None:
            return None
        
        power_delta_pct = (
            (power_delta / power_before * 100)
            if power_before and power_before > 0 else 0.0
        )
        
        point = Point("event_energy_correlation") \
            .tag("entity_id", entity_id) \
            .tag("domain", domain) \
            .tag("state", state) \
            .tag("previous_state", previous_state) \
            .field("power_before_w", float(power_before)) \
            .field("power_after_w", float(power_after)) \
            .field("power_delta_w", float(power_delta)) \
            .field("power_delta_pct", float(power_delta_pct)) \
            .time(event_time)
        
        logger.info(
            f"Correlation: {entity_id} [{previous_state}→{state}] "
            f"caused {power_delta:+.0f}W change "
            f"({power_delta_pct:+.1f}%)"
        )
        
        return point
    
    async def _write_correlation_points(self, points: List[Point]):
        """Write correlation batch to InfluxDB"""
        if not points or not self.client:
            return
        
        try:
            await self.client.write_points(points)
            self.correlations_written += len(points)
        except Exception as e:
            logger.error(f"Error writing correlation batch: {e}")
            self.errors += 1
            raise
    
    def _merge_pending_events(
        self,
        new_events: List[Dict[str, Any]],
        lookback_minutes: int
    ) -> List[Dict[str, Any]]:
        """Combine new events with pending retries, enforcing limits"""
        if not new_events and not self._pending_events:
            return []
        
        cutoff = datetime.utcnow() - timedelta(
            minutes=max(lookback_minutes, self.retry_window_minutes)
        )
        
        filtered_pending = [
            evt for evt in self._pending_events
            if isinstance(evt.get('time'), datetime) and evt['time'] >= cutoff
        ]
        
        combined = filtered_pending + new_events
        if not combined:
            return []
        
        dedup: Dict[tuple, Dict[str, Any]] = {}
        for event in combined:
            event_time = event.get('time')
            if not isinstance(event_time, datetime):
                continue
            key = (event.get('entity_id'), event_time)
            dedup[key] = event
        
        merged_events = list(dedup.values())
        if not merged_events:
            return []
        
        merged_events.sort(key=lambda e: e.get('time'), reverse=True)
        dropped = 0
        if len(merged_events) > self.max_events_per_interval:
            dropped = len(merged_events) - self.max_events_per_interval
            merged_events = merged_events[:self.max_events_per_interval]
        
        merged_events.sort(key=lambda e: e.get('time'))
        
        if dropped:
            logger.warning(
                "Dropped %s events due to max_events_per_interval=%s",
                dropped,
                self.max_events_per_interval
            )
        
        return merged_events
    
    def _trim_pending_events(
        self,
        events: List[Dict[str, Any]],
        lookback_minutes: int
    ) -> List[Dict[str, Any]]:
        """Enforce retry queue retention and size"""
        if not events or self.max_retry_queue_size == 0:
            return []
        
        cutoff = datetime.utcnow() - timedelta(
            minutes=max(lookback_minutes, self.retry_window_minutes)
        )
        
        filtered = [
            event for event in events
            if isinstance(event.get('time'), datetime) and event['time'] >= cutoff
        ]
        
        if not filtered:
            return []
        
        filtered.sort(key=lambda e: e['time'])
        
        if len(filtered) > self.max_retry_queue_size:
            filtered = filtered[-self.max_retry_queue_size:]
        
        return filtered
    
    async def _build_power_cache(self, events: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Fetch power samples covering the entire batch window"""
        timestamps = [event.get('time') for event in events if isinstance(event.get('time'), datetime)]
        if not timestamps:
            return {"timestamps": [], "values": []}
        
        start_time = min(timestamps) - timedelta(seconds=self.power_lookup_padding_seconds)
        end_time = max(timestamps) + timedelta(seconds=self.power_lookup_padding_seconds)
        
        flux_query = f'''
        from(bucket: "{self.influxdb_bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r["_measurement"] == "smart_meter")
          |> filter(fn: (r) => r["_field"] == "total_power_w")
          |> sort(columns: ["_time"])
        '''
        
        results = await self.client.query(flux_query)
        
        cache = {
            "timestamps": [],
            "values": []
        }
        
        for record in results:
            record_time = record.get('time')
            value = record.get('_value')
            if not isinstance(record_time, datetime) or value is None:
                continue
            
            cache["timestamps"].append(record_time.timestamp())
            cache["values"].append(float(value))
        
        logger.debug(
            "Loaded %s smart_meter points for power cache window %s - %s",
            len(cache["timestamps"]),
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        return cache
    
    def _lookup_power_in_cache(
        self,
        target_time: datetime,
        cache: Dict[str, List[float]]
    ) -> Optional[float]:
        """Find the nearest cached power reading to the requested time"""
        timestamps = cache.get("timestamps") or []
        values = cache.get("values") or []
        
        if not timestamps or not values:
            return None
        
        target_ts = target_time.timestamp()
        idx = bisect_left(timestamps, target_ts)
        candidate_indices = []
        
        for candidate in (idx, idx - 1):
            if 0 <= candidate < len(timestamps):
                candidate_indices.append(candidate)
        
        if not candidate_indices:
            return None
        
        best_idx = min(
            candidate_indices,
            key=lambda i: abs(timestamps[i] - target_ts)
        )
        
        if abs(timestamps[best_idx] - target_ts) > self.power_lookup_padding_seconds:
            return None
        
        return values[best_idx]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get correlator statistics"""
        
        correlation_rate = (
            (self.correlations_found / self.total_events_processed * 100)
            if self.total_events_processed > 0 else 0
        )
        
        write_success_rate = (
            (self.correlations_written / self.correlations_found * 100)
            if self.correlations_found > 0 else 100
        )
        
        return {
            "total_events_processed": self.total_events_processed,
            "correlations_found": self.correlations_found,
            "correlations_written": self.correlations_written,
            "correlation_rate_pct": round(correlation_rate, 2),
            "write_success_rate_pct": round(write_success_rate, 2),
            "errors": self.errors,
            "config": {
                "correlation_window_seconds": self.correlation_window_seconds,
                "min_power_delta_w": self.min_power_delta,
                "max_events_per_interval": self.max_events_per_interval,
                "power_lookup_padding_seconds": self.power_lookup_padding_seconds
            }
        }
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.total_events_processed = 0
        self.correlations_found = 0
        self.correlations_written = 0
        self.errors = 0
        logger.info("Statistics reset")

