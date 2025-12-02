"""
Sports Data InfluxDB Writer
Epic 12 Story 12.1: InfluxDB Persistence Layer

Writes sports game data to InfluxDB for historical queries and webhook event detection.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None

logger = logging.getLogger(__name__)


class SportsInfluxDBWriter:
    """InfluxDB writer for sports game data"""
    
    def __init__(self):
        """Initialize InfluxDB writer"""
        self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.token = os.getenv("INFLUXDB_TOKEN")
        self.org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.bucket = os.getenv("INFLUXDB_SPORTS_BUCKET", "sports_data")
        
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.is_connected = False
        
        # Statistics
        self.total_points_written = 0
        self.total_points_failed = 0
    
    async def connect(self) -> bool:
        """Connect to InfluxDB"""
        if InfluxDBClient is None:
            logger.warning("influxdb_client package not installed - InfluxDB writes disabled")
            return False
        
        if not self.token:
            logger.warning("INFLUXDB_TOKEN not set - InfluxDB writes disabled")
            return False
        
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30000
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.is_connected = True
            
            logger.info(f"Connected to InfluxDB for sports data at {self.url}, bucket: {self.bucket}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.is_connected = False
            return False
    
    async def write_nfl_game(self, game_data: Dict[str, Any]) -> bool:
        """Write NFL game data to InfluxDB"""
        if not self.is_connected or not self.write_api:
            return False
        
        try:
            point = Point("nfl_scores")
            
            # Tags (indexed for filtering)
            if game_id := game_data.get("game_id"):
                point.tag("game_id", str(game_id))
            if season := game_data.get("season"):
                point.tag("season", str(season))
            if week := game_data.get("week"):
                point.tag("week", str(week))
            if home_team := game_data.get("home_team") or game_data.get("homeTeam"):
                point.tag("home_team", str(home_team))
            if away_team := game_data.get("away_team") or game_data.get("awayTeam"):
                point.tag("away_team", str(away_team))
            if status := game_data.get("status"):
                point.tag("status", str(status))
            
            # Fields (measurements)
            if home_score := game_data.get("home_score") or game_data.get("homeScore"):
                point.field("home_score", int(home_score))
            if away_score := game_data.get("away_score") or game_data.get("awayScore"):
                point.field("away_score", int(away_score))
            if quarter := game_data.get("quarter") or game_data.get("period"):
                point.field("quarter", str(quarter))
            if time_remaining := game_data.get("time_remaining") or game_data.get("clock"):
                point.field("time_remaining", str(time_remaining))
            
            # Timestamp
            if start_time := game_data.get("start_time") or game_data.get("startTime"):
                if isinstance(start_time, str):
                    try:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        point.time(dt, WritePrecision.S)
                    except:
                        point.time(datetime.now(), WritePrecision.S)
                else:
                    point.time(start_time, WritePrecision.S)
            else:
                point.time(datetime.now(), WritePrecision.S)
            
            # Write to InfluxDB
            await asyncio.to_thread(
                self.write_api.write,
                bucket=self.bucket,
                org=self.org,
                record=point
            )
            
            self.total_points_written += 1
            return True
            
        except Exception as e:
            logger.error(f"Error writing NFL game to InfluxDB: {e}")
            self.total_points_failed += 1
            return False
    
    async def write_nhl_game(self, game_data: Dict[str, Any]) -> bool:
        """Write NHL game data to InfluxDB"""
        if not self.is_connected or not self.write_api:
            return False
        
        try:
            point = Point("nhl_scores")
            
            # Tags
            if game_id := game_data.get("game_id"):
                point.tag("game_id", str(game_id))
            if season := game_data.get("season"):
                point.tag("season", str(season))
            if home_team := game_data.get("home_team") or game_data.get("homeTeam"):
                point.tag("home_team", str(home_team))
            if away_team := game_data.get("away_team") or game_data.get("awayTeam"):
                point.tag("away_team", str(away_team))
            if status := game_data.get("status"):
                point.tag("status", str(status))
            
            # Fields
            if home_score := game_data.get("home_score") or game_data.get("homeScore"):
                point.field("home_score", int(home_score))
            if away_score := game_data.get("away_score") or game_data.get("awayScore"):
                point.field("away_score", int(away_score))
            if period := game_data.get("period"):
                point.field("period", str(period))
            if time_remaining := game_data.get("time_remaining") or game_data.get("clock"):
                point.field("time_remaining", str(time_remaining))
            
            # Timestamp
            if start_time := game_data.get("start_time") or game_data.get("startTime"):
                if isinstance(start_time, str):
                    try:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        point.time(dt, WritePrecision.S)
                    except:
                        point.time(datetime.now(), WritePrecision.S)
                else:
                    point.time(start_time, WritePrecision.S)
            else:
                point.time(datetime.now(), WritePrecision.S)
            
            # Write to InfluxDB
            await asyncio.to_thread(
                self.write_api.write,
                bucket=self.bucket,
                org=self.org,
                record=point
            )
            
            self.total_points_written += 1
            return True
            
        except Exception as e:
            logger.error(f"Error writing NHL game to InfluxDB: {e}")
            self.total_points_failed += 1
            return False
    
    async def write_game(self, game_data: Dict[str, Any]) -> bool:
        """Write game data to InfluxDB (auto-detects league)"""
        league = game_data.get("league", "").upper()
        
        if league == "NFL":
            return await self.write_nfl_game(game_data)
        elif league == "NHL":
            return await self.write_nhl_game(game_data)
        else:
            logger.warning(f"Unknown league: {league}, skipping write")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get writer statistics"""
        return {
            "connected": self.is_connected,
            "total_points_written": self.total_points_written,
            "total_points_failed": self.total_points_failed,
            "bucket": self.bucket
        }
    
    async def close(self):
        """Close InfluxDB connection"""
        if self.write_api:
            try:
                self.write_api.close()
            except:
                pass
        
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.is_connected = False
        logger.info("InfluxDB writer closed")


# Global instance
_sports_writer: Optional[SportsInfluxDBWriter] = None


def get_sports_writer() -> SportsInfluxDBWriter:
    """Get global sports InfluxDB writer instance"""
    global _sports_writer
    if _sports_writer is None:
        _sports_writer = SportsInfluxDBWriter()
    return _sports_writer

