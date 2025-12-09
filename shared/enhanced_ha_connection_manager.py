"""
Enhanced Home Assistant Connection Manager with Circuit Breaker Pattern

This module provides a unified way for all services to connect to Home Assistant
with automatic fallback and circuit breaker protection.

Features:
- Circuit breaker pattern for resilience
- Automatic fallback: Primary HA → Nabu Casa → Local HA
- Health monitoring and metrics
- Connection pooling and reuse
- Comprehensive error handling

Usage:
    from shared.ha_connection_manager import ha_connection_manager
    
    # Get connection with circuit breaker protection
    connection = await ha_connection_manager.get_connection_with_circuit_breaker()
    
    if connection:
        # Use the connection
        async with connection as client:
            # Make HA API calls
            pass
"""

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import websockets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of Home Assistant connections"""
    PRIMARY_HA = "primary_ha"
    NABU_CASA = "nabu_casa"
    LOCAL_HA = "local_ha"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


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
    circuit_breaker_config: Dict[str, Any] = field(default_factory=lambda: {
        'fail_max': 5,
        'reset_timeout': 60,
        'success_threshold': 3
    })


@dataclass
class ConnectionResult:
    """Result of a connection attempt"""
    success: bool
    connection_config: Optional[HAConnectionConfig] = None
    error: Optional[str] = None
    response_time: Optional[float] = None


class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, name: str, fail_max: int = 5, reset_timeout: int = 60, success_threshold: int = 3):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.state_changes = 0
        
    def can_execute(self) -> bool:
        """Check if requests can be executed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and (datetime.now() - self.last_failure_time).seconds >= self.reset_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.state_changes += 1
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record a successful operation"""
        self.successes += 1
        self.last_success_time = datetime.now()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.successes >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.state_changes += 1
                self.failures = 0
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED after {self.successes} successes")
    
    def record_failure(self, error: Exception):
        """Record a failed operation"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failures >= self.fail_max:
                self.state = CircuitBreakerState.OPEN
                self.state_changes += 1
                logger.warning(f"Circuit breaker {self.name} transitioning to OPEN after {self.failures} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.state_changes += 1
            logger.warning(f"Circuit breaker {self.name} transitioning to OPEN from HALF_OPEN")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failures': self.failures,
            'successes': self.successes,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'state_changes': self.state_changes
        }


class EnhancedHAConnectionManager:
    """
    Enhanced Home Assistant Connection Manager with Circuit Breaker Pattern
    
    Connection Priority:
    1. HOME_ASSISTANT_URL + HOME_ASSISTANT_TOKEN (Primary HA - local instance)
    2. NABU_CASA_URL + NABU_CASA_TOKEN (Nabu Casa cloud fallback)
    
    Legacy support: HA_HTTP_URL/HA_WS_URL + HA_TOKEN also supported for backwards compatibility
    """
    
    def __init__(self):
        self.connections: List[HAConnectionConfig] = []
        self.current_connection: Optional[HAConnectionConfig] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        self._load_connection_configs()
    
    def _normalize_websocket_url(self, url: str, connection_type: ConnectionType) -> str:
        """
        Normalize URL to WebSocket format
        
        Args:
            url: Input URL (can be HTTP, HTTPS, or already WebSocket format)
            connection_type: Type of connection for special handling
            
        Returns:
            Normalized WebSocket URL
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Handle already WebSocket URLs
        if url.startswith('wss://') or url.startswith('ws://'):
            # Already WebSocket format, just ensure /api/websocket is present
            if not url.endswith('/api/websocket'):
                if url.endswith('/api'):
                    url += '/websocket'
                else:
                    url += '/api/websocket'
            return url
        
        # Convert HTTP/HTTPS to WebSocket
        if url.startswith('https://'):
            ws_url = url.replace('https://', 'wss://')
        elif url.startswith('http://'):
            ws_url = url.replace('http://', 'ws://')
        else:
            # No protocol specified - assume HTTPS for Nabu Casa, HTTP for local
            if connection_type == ConnectionType.NABU_CASA:
                ws_url = f'wss://{url}'
            else:
                ws_url = f'ws://{url}'
        
        # Ensure /api/websocket path is present
        if not ws_url.endswith('/api/websocket'):
            if ws_url.endswith('/api'):
                ws_url += '/websocket'
            else:
                ws_url += '/api/websocket'
        
        return ws_url
    
    def _normalize_http_url(self, ws_url: str) -> str:
        """
        Convert WebSocket URL to HTTP URL for API testing
        
        Args:
            ws_url: WebSocket URL
            
        Returns:
            HTTP URL without /api/websocket path
        """
        # Convert WebSocket protocol to HTTP
        http_url = ws_url.replace('wss://', 'https://').replace('ws://', 'http://')
        
        # Remove /api/websocket suffix if present
        if http_url.endswith('/api/websocket'):
            http_url = http_url[:-14]  # Remove '/api/websocket'
        elif http_url.endswith('/api'):
            http_url = http_url[:-4]  # Remove '/api'
        
        return http_url.rstrip('/')
        
    def _load_connection_configs(self):
        """Load connection configurations from environment variables"""
        
        # Primary HA Connection (HA_* variables)
        ha_http_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL')
        ha_ws_url = os.getenv('HA_WS_URL') or os.getenv('HA_URL')
        ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
        
        if ha_http_url and ha_token:
            # Use WebSocket URL if provided, otherwise derive from HTTP URL
            if ha_ws_url:
                try:
                    url = self._normalize_websocket_url(ha_ws_url, ConnectionType.PRIMARY_HA)
                except Exception as e:
                    logger.error(f"❌ Failed to normalize WebSocket URL: {e}. Using HTTP URL instead.")
                    url = self._normalize_websocket_url(ha_http_url, ConnectionType.PRIMARY_HA)
            else:
                url = self._normalize_websocket_url(ha_http_url, ConnectionType.PRIMARY_HA)
            
            config = HAConnectionConfig(
                name="Primary HA",
                url=url,
                token=ha_token,
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1,
                timeout=30,
                max_retries=3,
                retry_delay=5.0
            )
            self.connections.append(config)
            self._create_circuit_breaker(config)
            logger.info(f"✅ Primary HA connection configured: {url}")
        
        # Nabu Casa Fallback Connection
        nabu_casa_url = os.getenv('NABU_CASA_URL')
        nabu_casa_token = os.getenv('NABU_CASA_TOKEN')
        
        if nabu_casa_url and nabu_casa_token:
            try:
                # Normalize URL to WebSocket format
                ws_url = self._normalize_websocket_url(nabu_casa_url, ConnectionType.NABU_CASA)
                
                config = HAConnectionConfig(
                    name="Nabu Casa Fallback",
                    url=ws_url,
                    token=nabu_casa_token,
                    connection_type=ConnectionType.NABU_CASA,
                    priority=2,
                    timeout=45,  # Longer timeout for cloud connection
                    max_retries=5,
                    retry_delay=10.0
                )
                self.connections.append(config)
                self._create_circuit_breaker(config)
                logger.info(f"✅ Nabu Casa fallback configured: {ws_url}")
            except Exception as e:
                logger.error(f"❌ Failed to configure Nabu Casa fallback: {e}. URL: {nabu_casa_url}")
        
        # Sort by priority
        self.connections.sort(key=lambda x: x.priority)
        
        if not self.connections:
            logger.warning("⚠️ No Home Assistant connections configured")
        else:
            logger.info(f"📋 Loaded {len(self.connections)} Home Assistant connection(s)")
    
    def _create_circuit_breaker(self, config: HAConnectionConfig):
        """Create circuit breaker for a connection"""
        breaker_config = config.circuit_breaker_config
        breaker = CircuitBreaker(
            name=config.name,
            fail_max=breaker_config.get('fail_max', 5),
            reset_timeout=breaker_config.get('reset_timeout', 60),
            success_threshold=breaker_config.get('success_threshold', 3)
        )
        self.circuit_breakers[config.name] = breaker
        self.connection_stats[config.name] = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_connection_time': None,
            'last_error': None
        }
    
    async def get_connection_with_circuit_breaker(self) -> Optional[HAConnectionConfig]:
        """
        Get the best available connection with circuit breaker protection
        
        Returns:
            HAConnectionConfig if a working connection is found, None otherwise
        """
        for connection in self.connections:
            breaker = self.circuit_breakers.get(connection.name)
            
            # Check if circuit breaker allows execution
            if breaker and not breaker.can_execute():
                logger.debug(f"Circuit breaker {connection.name} is OPEN, skipping")
                continue
            
            try:
                # Test connection
                start_time = time.time()
                success = await self._test_connection(connection)
                response_time = time.time() - start_time
                
                if success:
                    # Record success in circuit breaker
                    if breaker:
                        breaker.record_success()
                    
                    # Update connection stats
                    self.connection_stats[connection.name]['successful_connections'] += 1
                    self.connection_stats[connection.name]['last_connection_time'] = datetime.now()
                    self.connection_stats[connection.name]['last_error'] = None
                    
                    self.current_connection = connection
                    logger.info(f"✅ Connected to {connection.name} ({connection.url}) in {response_time:.2f}s")
                    return connection
                else:
                    raise ConnectionError(f"Connection test failed for {connection.name}")
                    
            except Exception as e:
                # Record failure in circuit breaker
                if breaker:
                    breaker.record_failure(e)
                
                # Update connection stats
                self.connection_stats[connection.name]['failed_connections'] += 1
                self.connection_stats[connection.name]['last_error'] = str(e)
                
                logger.warning(f"❌ Connection failed for {connection.name}: {e}")
                continue
        
        logger.error("❌ All Home Assistant connections failed!")
        return None
    
    async def _test_connection(self, config: HAConnectionConfig) -> bool:
        """
        Test if a connection is working by making an HTTP API call
        
        Args:
            config: Connection configuration to test
            
        Returns:
            True if connection is working, False otherwise
        """
        http_url = None
        try:
            # Convert WebSocket URL to HTTP URL for testing
            http_url = self._normalize_http_url(config.url)
            test_url = f"{http_url}/api/"
            
            # Test HTTP API endpoint
            headers = {
                'Authorization': f'Bearer {config.token}',
                'Content-Type': 'application/json'
            }
            
            # SSL verification - disable for Nabu Casa if needed (some cert issues)
            ssl_verify = os.getenv('NABU_CASA_SSL_VERIFY', 'true').lower() == 'true' if config.connection_type == ConnectionType.NABU_CASA else True
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.timeout),
                connector=aiohttp.TCPConnector(ssl=ssl_verify)
            ) as session:
                async with session.get(test_url, headers=headers) as response:
                    if response.status == 200:
                        logger.debug(f"✅ Connection test passed for {config.name} ({http_url})")
                        return True
                    else:
                        error_text = await response.text()
                        logger.warning(
                            f"❌ Connection test failed for {config.name}: "
                            f"HTTP {response.status} - {error_text[:200]}"
                        )
                        return False
                    
        except aiohttp.ClientConnectorError as e:
            logger.warning(
                f"❌ Connection test failed for {config.name} ({http_url or config.url}): "
                f"Connection error - {str(e)}"
            )
            return False
        except aiohttp.ClientError as e:
            logger.warning(
                f"❌ Connection test failed for {config.name} ({http_url or config.url}): "
                f"Client error - {str(e)}"
            )
            return False
        except asyncio.TimeoutError:
            logger.warning(
                f"❌ Connection test timed out for {config.name} ({http_url or config.url}) "
                f"after {config.timeout}s"
            )
            return False
        except Exception as e:
            logger.warning(
                f"❌ Connection test failed for {config.name} ({http_url or config.url}): "
                f"Unexpected error - {type(e).__name__}: {str(e)}"
            )
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get comprehensive connection status"""
        status = {
            'total_connections': len(self.connections),
            'current_connection': self.current_connection.name if self.current_connection else None,
            'connections': [],
            'circuit_breakers': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for connection in self.connections:
            conn_status = {
                'name': connection.name,
                'url': connection.url,
                'type': connection.connection_type.value,
                'priority': connection.priority,
                'stats': self.connection_stats.get(connection.name, {}),
                'circuit_breaker': self.circuit_breakers.get(connection.name).get_stats() if connection.name in self.circuit_breakers else None
            }
            status['connections'].append(conn_status)
        
        for name, breaker in self.circuit_breakers.items():
            status['circuit_breakers'][name] = breaker.get_stats()
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connections"""
        health_status = {
            'overall_health': 'healthy',
            'connections': [],
            'timestamp': datetime.now().isoformat()
        }
        
        healthy_connections = 0
        
        for connection in self.connections:
            try:
                is_healthy = await self._test_connection(connection)
                conn_health = {
                    'name': connection.name,
                    'healthy': is_healthy,
                    'url': connection.url,
                    'circuit_breaker_state': self.circuit_breakers.get(connection.name).state.value if connection.name in self.circuit_breakers else 'unknown'
                }
                
                if is_healthy:
                    healthy_connections += 1
                
                health_status['connections'].append(conn_health)
                
            except Exception as e:
                conn_health = {
                    'name': connection.name,
                    'healthy': False,
                    'url': connection.url,
                    'error': str(e),
                    'circuit_breaker_state': self.circuit_breakers.get(connection.name).state.value if connection.name in self.circuit_breakers else 'unknown'
                }
                health_status['connections'].append(conn_health)
        
        # Determine overall health
        if healthy_connections == 0:
            health_status['overall_health'] = 'unhealthy'
        elif healthy_connections < len(self.connections):
            health_status['overall_health'] = 'degraded'
        
        return health_status


# Global instance
ha_connection_manager = EnhancedHAConnectionManager()


# Backward compatibility
async def get_connection() -> Optional[HAConnectionConfig]:
    """Get connection (backward compatibility)"""
    return await ha_connection_manager.get_connection_with_circuit_breaker()
