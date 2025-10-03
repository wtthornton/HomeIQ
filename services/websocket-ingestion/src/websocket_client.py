"""
Home Assistant WebSocket Client with Authentication
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from aiohttp import ClientSession, WSMsgType, ClientWebSocketResponse
from aiohttp.web_exceptions import HTTPException
import json

from token_validator import TokenValidator

logger = logging.getLogger(__name__)


class HomeAssistantWebSocketClient:
    """WebSocket client for Home Assistant with authentication"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.token_validator = TokenValidator()
        self.session: Optional[ClientSession] = None
        self.websocket: Optional[ClientWebSocketResponse] = None
        self.is_connected = False
        self.is_authenticated = False
        self.connection_attempts = 0
        self.max_retries = 5
        self.retry_delay = 1  # seconds
        
        # Event handlers
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection with Home Assistant
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Validate token before attempting connection
            is_valid, error_msg = self.token_validator.validate_token(self.token)
            if not is_valid:
                logger.error(f"Token validation failed: {error_msg}")
                if self.on_error:
                    await self.on_error(f"Token validation failed: {error_msg}")
                return False
            
            logger.info(f"Connecting to Home Assistant at {self.base_url}")
            logger.info(f"Using token: {self.token_validator.mask_token(self.token)}")
            
            # Create session
            self.session = ClientSession()
            
            # Build WebSocket URL
            ws_url = f"{self.base_url.replace('http', 'ws')}/api/websocket"
            
            # Connect to WebSocket
            self.websocket = await self.session.ws_connect(
                ws_url,
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'User-Agent': 'HA-Ingestor/1.0'
                }
            )
            
            self.is_connected = True
            self.connection_attempts = 0
            
            logger.info("WebSocket connection established")
            
            # Handle authentication
            await self._handle_authentication()
            
            if self.is_authenticated:
                logger.info("Successfully authenticated with Home Assistant")
                if self.on_connect:
                    await self.on_connect()
                return True
            else:
                logger.error("Authentication failed")
                await self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            if self.on_error:
                await self.on_error(f"Connection failed: {e}")
            await self.disconnect()
            return False
    
    async def _handle_authentication(self):
        """Handle Home Assistant WebSocket authentication flow"""
        try:
            # Wait for auth_required message
            auth_required_msg = await self.websocket.receive()
            logger.debug(f"Received auth message: {auth_required_msg.data}")
            
            if auth_required_msg.type == WSMsgType.TEXT:
                auth_data = json.loads(auth_required_msg.data)
                
                if auth_data.get('type') == 'auth_required':
                    logger.info("Authentication required, sending token")
                    
                    # Send authentication message
                    auth_message = {
                        'type': 'auth',
                        'access_token': self.token
                    }
                    
                    await self.websocket.send_str(json.dumps(auth_message))
                    
                    # Wait for auth result
                    auth_result_msg = await self.websocket.receive()
                    logger.debug(f"Received auth result: {auth_result_msg.data}")
                    
                    if auth_result_msg.type == WSMsgType.TEXT:
                        auth_result = json.loads(auth_result_msg.data)
                        
                        if auth_result.get('type') == 'auth_ok':
                            self.is_authenticated = True
                            logger.info("Authentication successful")
                        else:
                            logger.error(f"Authentication failed: {auth_result}")
                            self.is_authenticated = False
                    else:
                        logger.error("Unexpected message type during authentication")
                        self.is_authenticated = False
                else:
                    logger.error(f"Unexpected message type: {auth_data.get('type')}")
                    self.is_authenticated = False
            else:
                logger.error("Unexpected message type during authentication")
                self.is_authenticated = False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.is_authenticated = False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            if self.session:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            self.is_authenticated = False
            
            logger.info("Disconnected from Home Assistant")
            
            if self.on_disconnect:
                await self.on_disconnect()
                
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to Home Assistant
        
        Args:
            message: Message to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected or not self.is_authenticated:
            logger.warning("Cannot send message: not connected or authenticated")
            return False
        
        try:
            await self.websocket.send_str(json.dumps(message))
            logger.debug(f"Sent message: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def listen(self):
        """Listen for messages from Home Assistant"""
        if not self.is_connected or not self.is_authenticated:
            logger.warning("Cannot listen: not connected or authenticated")
            return
        
        try:
            async for msg in self.websocket:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        logger.debug(f"Received message: {data}")
                        
                        if self.on_message:
                            await self.on_message(data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    if self.on_error:
                        await self.on_error(f"WebSocket error: {msg.data}")
                    break
                elif msg.type == WSMsgType.CLOSE:
                    logger.info("WebSocket connection closed")
                    break
                    
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            if self.on_error:
                await self.on_error(f"Listen error: {e}")
    
    async def reconnect(self) -> bool:
        """
        Reconnect to Home Assistant with exponential backoff
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self.connection_attempts >= self.max_retries:
            logger.error("Maximum reconnection attempts reached")
            return False
        
        self.connection_attempts += 1
        delay = self.retry_delay * (2 ** (self.connection_attempts - 1))
        
        logger.info(f"Reconnecting in {delay} seconds (attempt {self.connection_attempts}/{self.max_retries})")
        await asyncio.sleep(delay)
        
        await self.disconnect()
        return await self.connect()
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status
        
        Returns:
            Dictionary with connection status information
        """
        return {
            "is_connected": self.is_connected,
            "is_authenticated": self.is_authenticated,
            "connection_attempts": self.connection_attempts,
            "max_retries": self.max_retries,
            "base_url": self.base_url,
            "token_info": self.token_validator.get_token_info(self.token),
            "timestamp": datetime.now().isoformat()
        }
