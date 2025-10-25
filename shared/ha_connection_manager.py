"""
Home Assistant Connection Manager with HA/Nabu Casa Fallback

This module provides a unified way for all services to connect to Home Assistant
with automatic fallback from primary HA URLs/tokens to Nabu Casa URLs/tokens.

Usage:
    from shared.ha_connection_manager import HAConnectionManager
    
    # Initialize with environment variables
    ha_manager = HAConnectionManager()
    
    # Get the best available connection
    connection = await ha_manager.get_connection()
    
    # Use the connection
    async with connection as client:
        # Make HA API calls
        pass
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
import websockets
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of Home Assistant connections"""
    PRIMARY_HA = "primary_ha"
    NABU_CASA = "nabu_casa"
    LOCAL_HA = "local_ha"


@dataclass
class HAConnectionConfig:
    """Configuration for a Home Assistant connection"""
    name: str
    url: str
    token: str
    connection_type: ConnectionType
    priority: int
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 5.0


@dataclass
class ConnectionResult:
    """Result of a connection attempt"""
    success: bool
    config: Optional[HAConnectionConfig]
    error: Optional[str] = None
    response_time: Optional[float] = None


class HAConnectionManager:
    """
    Manages Home Assistant connections with automatic fallback.
    
    Connection Priority:
    1. HA_HTTP_URL/HA_WS_URL + HA_TOKEN (Primary HA)
    2. NABU_CASA_URL + NABU_CASA_TOKEN (Nabu Casa fallback)
    3. LOCAL_HA_URL + LOCAL_HA_TOKEN (Local HA fallback)
    """
    
    def __init__(self):
        self.connections: List[HAConnectionConfig] = []
        self.current_connection: Optional[HAConnectionConfig] = None
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        self._load_connection_configs()
        
    def _load_connection_configs(self):
        """Load connection configurations from environment variables"""
        
        # Primary HA Connection (HA_* variables)
        ha_http_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL')
        ha_ws_url = os.getenv('HA_WS_URL') or os.getenv('HA_URL')
        ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
        
        if ha_http_url and ha_token:
            # Use WebSocket URL if provided, otherwise derive from HTTP URL
            if ha_ws_url:
                url = ha_ws_url
            else:
                url = ha_http_url.replace('http://', 'ws://').replace('https://', 'wss://')
                if not url.endswith('/api/websocket'):
                    url += '/api/websocket'
            
            self.connections.append(HAConnectionConfig(
                name="Primary HA",
                url=url,
                token=ha_token,
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1,
                timeout=30,
                max_retries=3,
                retry_delay=5.0
            ))
            logger.info(f"✅ Primary HA connection configured: {url}")
        
        # Nabu Casa Fallback Connection
        nabu_casa_url = os.getenv('NABU_CASA_URL')
        nabu_casa_token = os.getenv('NABU_CASA_TOKEN')
        
        if nabu_casa_url and nabu_casa_token:
            # Ensure Nabu Casa URL is WebSocket format
            if nabu_casa_url.startswith('https://'):
                ws_url = nabu_casa_url.replace('https://', 'wss://')
            elif nabu_casa_url.startswith('http://'):
                ws_url = nabu_casa_url.replace('http://', 'ws://')
            else:
                ws_url = nabu_casa_url
            
            if not ws_url.endswith('/api/websocket'):
                ws_url += '/api/websocket'
            
            self.connections.append(HAConnectionConfig(
                name="Nabu Casa Fallback",
                url=ws_url,
                token=nabu_casa_token,
                connection_type=ConnectionType.NABU_CASA,
                priority=2,
                timeout=45,  # Longer timeout for cloud connection
                max_retries=5,
                retry_delay=10.0
            ))
            logger.info(f"✅ Nabu Casa fallback configured: {ws_url}")
        
        # Local HA Fallback Connection (Optional)
        local_ha_url = os.getenv('LOCAL_HA_URL')
        local_ha_token = os.getenv('LOCAL_HA_TOKEN')
        
        if local_ha_url and local_ha_token:
            # Convert to WebSocket URL
            ws_url = local_ha_url.replace('http://', 'ws://').replace('https://', 'wss://')
            if not ws_url.endswith('/api/websocket'):
                ws_url += '/api/websocket'
            
            self.connections.append(HAConnectionConfig(
                name="Local HA Fallback",
                url=ws_url,
                token=local_ha_token,
                connection_type=ConnectionType.LOCAL_HA,
                priority=3,
                timeout=30,
                max_retries=3,
                retry_delay=5.0
            ))
            logger.info(f"✅ Local HA fallback configured: {ws_url}")
        
        # Sort by priority
        self.connections.sort(key=lambda x: x.priority)
        
        if not self.connections:
            logger.warning("⚠️ No Home Assistant connections configured!")
            logger.warning("   Set HA_HTTP_URL/HA_WS_URL + HA_TOKEN or NABU_CASA_URL + NABU_CASA_TOKEN")
        else:
            logger.info(f"📋 Loaded {len(self.connections)} Home Assistant connection(s)")
            for conn in self.connections:
                logger.info(f"   - {conn.name}: {conn.url} (Priority: {conn.priority})")
    
    async def test_connection(self, config: HAConnectionConfig) -> ConnectionResult:
        """Test a specific connection configuration"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Test WebSocket connection
            headers = {"Authorization": f"Bearer {config.token}"}
            
            async with websockets.connect(
                config.url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
                open_timeout=config.timeout
            ) as websocket:
                # Wait for authentication response
                auth_response = await asyncio.wait_for(websocket.recv(), timeout=10)
                auth_data = await self._parse_auth_response(auth_response)
                
                if auth_data.get("type") == "auth_ok":
                    response_time = asyncio.get_event_loop().time() - start_time
                    logger.info(f"✅ Connection test successful: {config.name} ({response_time:.2f}s)")
                    return ConnectionResult(
                        success=True,
                        config=config,
                        response_time=response_time
                    )
                else:
                    error_msg = f"Authentication failed: {auth_data.get('message', 'Unknown error')}"
                    logger.warning(f"❌ Authentication failed for {config.name}: {error_msg}")
                    return ConnectionResult(
                        success=False,
                        config=config,
                        error=error_msg
                    )
        
        except asyncio.TimeoutError:
            error_msg = f"Connection timeout after {config.timeout}s"
            logger.warning(f"❌ Connection timeout for {config.name}: {error_msg}")
            return ConnectionResult(
                success=False,
                config=config,
                error=error_msg
            )
        
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.warning(f"❌ Connection failed for {config.name}: {error_msg}")
            return ConnectionResult(
                success=False,
                config=config,
                error=error_msg
            )
    
    async def _parse_auth_response(self, response: str) -> Dict[str, Any]:
        """Parse authentication response from Home Assistant"""
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            return {"type": "error", "message": "Invalid JSON response"}
    
    async def get_best_connection(self) -> Optional[HAConnectionConfig]:
        """
        Get the best available connection by testing each one in priority order.
        Returns the first successful connection.
        """
        for config in self.connections:
            result = await self.test_connection(config)
            if result.success:
                self.current_connection = config
                self._update_connection_stats(config.name, True, result.response_time)
                logger.info(f"🎯 Selected connection: {config.name}")
                return config
            else:
                self._update_connection_stats(config.name, False, None)
                logger.warning(f"⚠️ Connection failed: {config.name} - {result.error}")
        
        logger.error("❌ All Home Assistant connections failed!")
        return None
    
    async def get_connection(self) -> Optional[HAConnectionConfig]:
        """
        Get a connection, using cached successful connection if available,
        otherwise testing all connections.
        """
        if self.current_connection:
            # Test current connection first
            result = await self.test_connection(self.current_connection)
            if result.success:
                return self.current_connection
            else:
                logger.warning(f"⚠️ Current connection failed, testing alternatives: {result.error}")
                self.current_connection = None
        
        # Find best available connection
        return await self.get_best_connection()
    
    def _update_connection_stats(self, name: str, success: bool, response_time: Optional[float]):
        """Update connection statistics"""
        if name not in self.connection_stats:
            self.connection_stats[name] = {
                'total_attempts': 0,
                'successful_attempts': 0,
                'failed_attempts': 0,
                'avg_response_time': 0.0,
                'last_success': None,
                'last_failure': None
            }
        
        stats = self.connection_stats[name]
        stats['total_attempts'] += 1
        
        if success:
            stats['successful_attempts'] += 1
            stats['last_success'] = asyncio.get_event_loop().time()
            if response_time:
                # Update average response time
                if stats['avg_response_time'] == 0:
                    stats['avg_response_time'] = response_time
                else:
                    stats['avg_response_time'] = (stats['avg_response_time'] + response_time) / 2
        else:
            stats['failed_attempts'] += 1
            stats['last_failure'] = asyncio.get_event_loop().time()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'current_connection': self.current_connection.name if self.current_connection else None,
            'total_connections': len(self.connections),
            'connection_stats': self.connection_stats,
            'health_status': 'healthy' if self.current_connection else 'unhealthy'
        }
    
    @asynccontextmanager
    async def get_websocket_client(self):
        """Get a WebSocket client for the best available connection"""
        config = await self.get_connection()
        if not config:
            raise ConnectionError("No Home Assistant connections available")
        
        headers = {"Authorization": f"Bearer {config.token}"}
        
        try:
            websocket = await websockets.connect(
                config.url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
                open_timeout=config.timeout
            )
            
            # Handle authentication
            auth_response = await websocket.recv()
            auth_data = await self._parse_auth_response(auth_response)
            
            if auth_data.get("type") != "auth_ok":
                await websocket.close()
                raise ConnectionError(f"Authentication failed: {auth_data.get('message', 'Unknown error')}")
            
            logger.info(f"🔌 WebSocket connected to {config.name}")
            yield websocket
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {str(e)}")
            raise
        finally:
            if 'websocket' in locals():
                await websocket.close()
                logger.info(f"🔌 WebSocket disconnected from {config.name}")
    
    async def get_http_client(self) -> Optional[aiohttp.ClientSession]:
        """Get an HTTP client for the best available connection"""
        config = await self.get_connection()
        if not config:
            return None
        
        # Convert WebSocket URL to HTTP URL
        http_url = config.url.replace('ws://', 'http://').replace('wss://', 'https://')
        if http_url.endswith('/api/websocket'):
            http_url = http_url.replace('/api/websocket', '')
        
        headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=config.timeout)
        return aiohttp.ClientSession(
            base_url=http_url,
            headers=headers,
            timeout=timeout
        )


# Global instance for easy access
ha_connection_manager = HAConnectionManager()


# Convenience functions
async def get_ha_connection() -> Optional[HAConnectionConfig]:
    """Get the best available HA connection"""
    return await ha_connection_manager.get_connection()


async def get_ha_websocket():
    """Get a WebSocket client for HA"""
    return ha_connection_manager.get_websocket_client()


async def get_ha_http_client() -> Optional[aiohttp.ClientSession]:
    """Get an HTTP client for HA"""
    return await ha_connection_manager.get_http_client()


def get_ha_stats() -> Dict[str, Any]:
    """Get HA connection statistics"""
    return ha_connection_manager.get_connection_stats()
