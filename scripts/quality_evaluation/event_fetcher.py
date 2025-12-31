"""
Event Fetcher for Quality Evaluation

Fetches events from Data API for validation.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Add services path for DataAPIClient
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "ai-pattern-service" / "src"))

try:
    from clients.data_api_client import DataAPIClient
except ImportError:
    # Fallback: Try alternative import path
    try:
        from services.ai_pattern_service.src.clients.data_api_client import DataAPIClient
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.error("Could not import DataAPIClient - event validation will be skipped")
        DataAPIClient = None

logger = logging.getLogger(__name__)


class EventFetcher:
    """Fetches events from Data API for validation."""
    
    def __init__(self, data_api_url: str = "http://localhost:8006"):
        """
        Initialize Data API client.
        
        Args:
            data_api_url: Base URL for Data API
        """
        if DataAPIClient is None:
            raise ImportError("DataAPIClient not available - cannot fetch events")
        
        self.data_api_url = data_api_url
        self.client: Optional[DataAPIClient] = None
        logger.info(f"Initialized event fetcher for {data_api_url}")
    
    async def fetch_events(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50000
    ) -> pd.DataFrame:
        """
        Fetch events and return as DataFrame.
        
        Args:
            start_time: Start time for events
            end_time: End time for events
            limit: Maximum number of events to fetch
            
        Returns:
            DataFrame containing events
        """
        if self.client is None:
            self.client = DataAPIClient(base_url=self.data_api_url)
        
        try:
            async with self.client:
                events_df = await self.client.fetch_events(
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit
                )
                
                if events_df.empty:
                    logger.warning("No events fetched from Data API")
                else:
                    logger.info(f"Fetched {len(events_df)} events from {start_time} to {end_time}")
                
                return events_df
                
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}", exc_info=True)
            return pd.DataFrame()
    
    async def close(self) -> None:
        """Close API client connection."""
        if self.client:
            # DataAPIClient uses async context manager, so we don't need explicit close
            self.client = None
            logger.debug("Event fetcher closed")
