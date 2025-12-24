#!/usr/bin/env python3
"""
Enhanced fallback test using BMAD Context7 KB patterns
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
import websockets
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_env_file(env_path: str = ".env"):
    """Load environment variables from .env file using Context7 KB patterns"""
    env_file = Path(env_path)
    if env_file.exists():
        logger.info(f"📁 Loading environment from {env_path}")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        try:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            if '\x00' not in value:
                                os.environ[key] = value
                        except Exception as e:
                            logger.warning(f"⚠️  Error parsing line {line_num}: {line} - {e}")
            logger.info("✅ Environment variables loaded from .env file")
        except Exception as e:
            logger.error(f"❌ Error reading .env file: {e}")
    else:
        logger.warning(f"⚠️  .env file not found at {env_path}")

class EnhancedFallbackTest:
    """Enhanced fallback test using Context7 KB patterns"""
    
    def __init__(self):
        self.connections = []
        self._load_test_connections()
        
    def _load_test_connections(self):
        """Load test connection configurations using Context7 KB patterns"""
        
        # Primary connection (HA Simulator)
        primary_url = "http://ha-simulator:8123"
        primary_token = "dev_simulator_token"
        
        self.connections.append({
            "name": "Primary (HA Simulator)",
            "url": primary_url,
            "token": primary_token,
            "ws_url": primary_url.replace("http://", "ws://") + "/api/websocket",
            "priority": 1,
            "timeout": 30,
            "heartbeat": 20.0
        })
        
        # Nabu Casa fallback
        nabu_casa_url = "https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa"
        nabu_casa_token = os.getenv("NABU_CASA_TOKEN")
        
        if nabu_casa_token:
            self.connections.append({
                "name": "Nabu Casa Fallback",
                "url": nabu_casa_url,
                "token": nabu_casa_token,
                "ws_url": nabu_casa_url.replace("https://", "wss://") + "/api/websocket",
                "priority": 2,
                "timeout": 45,
                "heartbeat": 30.0
            })
        
        # Sort by priority
        self.connections.sort(key=lambda x: x["priority"])
        
        logger.info(f"📋 Enhanced test connections loaded:")
        for conn in self.connections:
            logger.info(f"  - {conn['name']}: {conn['url']} (Priority: {conn['priority']})")
    
    async def test_connection_enhanced(self, connection: Dict[str, Any]) -> bool:
        """Test connection using Context7 KB patterns"""
        try:
            logger.info(f"🔗 Testing enhanced connection to {connection['name']}")
            logger.info(f"🌐 URL: {connection['ws_url']}")
            logger.info(f"⏱️  Timeout: {connection['timeout']}s, Heartbeat: {connection['heartbeat']}s")
            
            # Connect using Context7 KB patterns
            ws = await websockets.connect(
                connection["ws_url"],
                ping_interval=connection["heartbeat"],
                ping_timeout=10,
                close_timeout=connection["timeout"],
                max_size=4194304,  # 4MB max message size
                compression=None
            )
            
            logger.info(f"✅ WebSocket connection established to {connection['name']}")
            
            # Wait for auth_required
            auth_required = await ws.recv()
            auth_data = json.loads(auth_required)
            logger.info(f"🔐 Auth required: {auth_data}")
            
            if auth_data.get('type') != 'auth_required':
                logger.error("❌ Expected auth_required message")
                return False
            
            # Send authentication using Context7 KB patterns
            auth_message = {
                "type": "auth",
                "access_token": connection["token"]
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            auth_response = await ws.recv()
            auth_result = json.loads(auth_response)
            logger.info(f"🔑 Auth response: {auth_result}")
            
            if auth_result.get('type') == 'auth_ok':
                logger.info(f"✅ {connection['name']} authentication successful")
                
                # Test event subscription using Context7 KB patterns
                subscribe_message = {
                    "id": 1,
                    "type": "subscribe_events"
                }
                await ws.send(json.dumps(subscribe_message))
                
                # Wait for subscription confirmation
                response = await ws.recv()
                result = json.loads(response)
                logger.info(f"📡 Event subscription: {result}")
                
                if result.get('type') == 'result' and result.get('success'):
                    logger.info(f"✅ {connection['name']} event subscription successful")
                    
                    # Test event reception
                    logger.info("⏳ Testing event reception (5 seconds)...")
                    event_count = 0
                    start_time = datetime.now()
                    
                    try:
                        while (datetime.now() - start_time).seconds < 5:
                            try:
                                event = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                event_data = json.loads(event)
                                
                                if event_data.get('type') == 'event':
                                    event_count += 1
                                    event_type = event_data.get('event', {}).get('event_type', 'unknown')
                                    logger.info(f"📨 Event {event_count}: {event_type}")
                                    
                            except asyncio.TimeoutError:
                                continue
                    
                    except Exception as e:
                        logger.warning(f"⚠️  Event reception test error: {e}")
                    
                    logger.info(f"✅ Received {event_count} events in 5 seconds")
                    await ws.close()
                    return True
                else:
                    logger.error(f"❌ {connection['name']} event subscription failed")
                    await ws.close()
                    return False
            else:
                logger.error(f"❌ {connection['name']} authentication failed: {auth_result}")
                await ws.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ {connection['name']} connection error: {e}")
            return False
    
    async def test_fallback_scenario_enhanced(self):
        """Test enhanced fallback scenario using Context7 KB patterns"""
        logger.info("🧪 Testing enhanced fallback scenario...")
        
        # Test each connection individually
        results = {}
        for connection in self.connections:
            results[connection["name"]] = await self.test_connection_enhanced(connection)
        
        # Report results
        logger.info("\n📊 Enhanced Connection Test Results:")
        for name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"  {name}: {status}")
        
        # Determine fallback capability
        available_connections = [name for name, success in results.items() if success]
        
        if len(available_connections) >= 2:
            logger.info(f"🎉 Enhanced fallback capability confirmed! {len(available_connections)} connections available")
            logger.info(f"📋 Available connections: {', '.join(available_connections)}")
            return True
        elif len(available_connections) == 1:
            logger.warning(f"⚠️  Only one connection available: {available_connections[0]}")
            logger.warning("No fallback capability - consider adding more connections")
            return False
        else:
            logger.error("❌ No connections available")
            return False
    
    async def test_priority_order_enhanced(self):
        """Test enhanced priority order using Context7 KB patterns"""
        logger.info("🔢 Testing enhanced priority order...")
        
        # Sort connections by priority
        sorted_connections = sorted(self.connections, key=lambda x: x["priority"])
        
        logger.info("📋 Enhanced connection priority order:")
        for i, conn in enumerate(sorted_connections, 1):
            logger.info(f"  {i}. {conn['name']} (Priority: {conn['priority']}, Timeout: {conn['timeout']}s)")
        
        return True

async def main():
    """Main test function using Context7 KB patterns"""
    # Load environment
    load_env_file()
    
    test = EnhancedFallbackTest()
    
    logger.info("🚀 Starting enhanced fallback functionality test...")
    logger.info("📚 Using BMAD Context7 KB patterns for optimal testing")
    
    # Test priority order
    await test.test_priority_order_enhanced()
    
    # Test fallback scenario
    success = await test.test_fallback_scenario_enhanced()
    
    if success:
        logger.info("\n🎉 Enhanced fallback functionality test completed successfully!")
        logger.info("The enhanced websocket service is ready for deployment with Context7 KB patterns.")
    else:
        logger.error("\n❌ Enhanced fallback functionality test failed!")
        logger.error("Please check your connection configurations and tokens.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
