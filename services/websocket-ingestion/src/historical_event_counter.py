"""
Historical Event Counter for Persistent Total Event Tracking
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from influxdb_wrapper import InfluxDBConnectionManager

logger = logging.getLogger(__name__)


class HistoricalEventCounter:
    """Manages persistent total event counts across service restarts"""
    
    def __init__(self, influxdb_manager: InfluxDBConnectionManager):
        """
        Initialize historical event counter
        
        Args:
            influxdb_manager: InfluxDB connection manager
        """
        self.influxdb_manager = influxdb_manager
        self.historical_totals = {
            'total_events_received': 0,
            'total_events_processed': 0,
            'events_by_type': {},
            'last_updated': None
        }
        self._initialized = False
    
    async def initialize_historical_totals(self) -> Dict[str, Any]:
        """
        Query InfluxDB for historical event totals and initialize counters
        
        Returns:
            Dictionary with historical totals
        """
        if self._initialized:
            logger.info("Historical totals already initialized")
            return self.historical_totals
        
        try:
            logger.info("🔍 Querying InfluxDB for historical event totals...")
            
            # Query total events from InfluxDB - count all records
            total_events_query = '''
                from(bucket: "home_assistant_events")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "home_assistant_events")
                |> count()
                |> group()
                |> sum(column: "_value")
            '''
            
            # Query events by type
            events_by_type_query = '''
                from(bucket: "home_assistant_events")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "home_assistant_events")
                |> group(columns: ["event_type"])
                |> count()
            '''
            
            # Execute queries
            total_result = await self._execute_influx_query(total_events_query)
            type_result = await self._execute_influx_query(events_by_type_query)
            
            # Parse results
            total_events = self._parse_count_result(total_result)
            events_by_type = self._parse_grouped_count_result(type_result)
            
            # Update historical totals
            self.historical_totals = {
                'total_events_received': total_events,
                'total_events_processed': total_events,  # Assuming all received events are processed
                'events_by_type': events_by_type,
                'last_updated': datetime.now()
            }
            
            self._initialized = True
            
            logger.info(f"✅ Historical totals initialized: {total_events:,} total events")
            logger.info(f"📊 Events by type: {events_by_type}")
            
            return self.historical_totals
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize historical totals: {e}")
            # Return zeros as fallback
            self.historical_totals = {
                'total_events_received': 0,
                'total_events_processed': 0,
                'events_by_type': {},
                'last_updated': datetime.now()
            }
            self._initialized = True
            return self.historical_totals
    
    async def _execute_influx_query(self, query: str) -> Optional[Any]:
        """Execute InfluxDB query safely"""
        try:
            if not self.influxdb_manager.is_connected:
                logger.warning("InfluxDB not connected, cannot query historical totals")
                return None
            
            # Use the org from the connection manager
            import asyncio
            result = await asyncio.to_thread(
                self.influxdb_manager.query_api.query,
                query,
                org=self.influxdb_manager.org
            )
            return result
            
        except Exception as e:
            # Handle 401 Unauthorized errors gracefully - InfluxDB might not be fully initialized yet
            error_str = str(e)
            if "401" in error_str or "unauthorized" in error_str.lower() or "Unauthorized" in error_str:
                logger.warning(f"InfluxDB authentication failed (likely during startup): {error_str}. Will retry on next initialization.")
                return None
            logger.error(f"Failed to execute InfluxDB query: {e}")
            return None
    
    def _parse_count_result(self, result) -> int:
        """Parse InfluxDB count query result"""
        try:
            if not result:
                return 0
            
            total_count = 0
            for table in result:
                logger.debug(f"Processing table with {len(table.records)} records")
                for record in table.records:
                    # InfluxDB count() returns a record with "_value" field
                    # Try to get the count value from the record
                    try:
                        # Check if record has the _value field
                        if hasattr(record, 'get_value'):
                            value = record.get_value()
                            if value is not None:
                                total_count += int(value)
                                logger.debug(f"Added {value} to total_count (now: {total_count})")
                    except AttributeError as attr_error:
                        # Record might not have expected methods
                        logger.debug(f"Record attribute error: {attr_error}")
                        continue
                    except Exception as rec_error:
                        # Silently skip if we can't parse this record
                        logger.debug(f"Error reading record: {rec_error}")
                        continue
            
            return total_count
            
        except Exception as e:
            logger.error(f"Error parsing count result: {e}", exc_info=True)
            return 0
    
    def _parse_grouped_count_result(self, result) -> Dict[str, int]:
        """Parse InfluxDB grouped count query result"""
        try:
            if not result:
                return {}
            
            events_by_type = {}
            for table in result:
                # Get event_type from table's group key
                event_type_key = None
                if hasattr(table, 'group_key') and isinstance(table.group_key, dict) and 'event_type' in table.group_key:
                    event_type_key = str(table.group_key['event_type'])
                
                # Get the count value from records
                for record in table.records:
                    try:
                        if hasattr(record, 'get_value'):
                            value = record.get_value()
                            if value is not None:
                                count = int(value)
                                if event_type_key:
                                    events_by_type[event_type_key] = events_by_type.get(event_type_key, 0) + count
                    except Exception as rec_error:
                        logger.warning(f"Error reading grouped record: {rec_error}")
                        continue
            
            return events_by_type
            
        except Exception as e:
            logger.error(f"Error parsing grouped count result: {e}")
            return {}
    
    def get_historical_totals(self) -> Dict[str, Any]:
        """Get current historical totals"""
        return self.historical_totals.copy()
    
    def add_to_totals(self, events_received: int, events_processed: int, events_by_type: Dict[str, int]):
        """Add new events to historical totals"""
        if not self._initialized:
            logger.warning("Historical totals not initialized, cannot add to totals")
            return
        
        self.historical_totals['total_events_received'] += events_received
        self.historical_totals['total_events_processed'] += events_processed
        self.historical_totals['last_updated'] = datetime.now()
        
        # Update events by type
        for event_type, count in events_by_type.items():
            current_count = self.historical_totals['events_by_type'].get(event_type, 0)
            self.historical_totals['events_by_type'][event_type] = current_count + count
    
    def get_total_events_received(self) -> int:
        """Get total events received (historical + current session)"""
        return self.historical_totals.get('total_events_received', 0)
    
    def get_total_events_processed(self) -> int:
        """Get total events processed (historical + current session)"""
        return self.historical_totals.get('total_events_processed', 0)
    
    def is_initialized(self) -> bool:
        """Check if historical totals are initialized"""
        return self._initialized
