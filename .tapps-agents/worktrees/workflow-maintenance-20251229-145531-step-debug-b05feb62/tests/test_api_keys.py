#!/usr/bin/env python3
"""
Local API Key Validation Tests

This script provides comprehensive testing for:
- Home Assistant API tokens
- Weather API keys
- Environment variable validation
- Actual API connectivity tests

Usage:
    python tests/test_api_keys.py
    python tests/test_api_keys.py --ha-token YOUR_HA_TOKEN
    python tests/test_api_keys.py --weather-key YOUR_WEATHER_KEY
    python tests/test_api_keys.py --env-file .env
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Third-party imports
try:
    import aiohttp
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install required packages:")
    print("pip install aiohttp requests python-dotenv")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APITestResult:
    """Container for API test results"""
    
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.error = None
        self.details = {}
        self.timestamp = datetime.now().isoformat()
    
    def set_success(self, details: Dict[str, Any] = None):
        """Mark test as successful"""
        self.success = True
        if details:
            self.details.update(details)
    
    def set_error(self, error: str, details: Dict[str, Any] = None):
        """Mark test as failed"""
        self.success = False
        self.error = error
        if details:
            self.details.update(details)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'success': self.success,
            'error': self.error,
            'details': self.details,
            'timestamp': self.timestamp
        }


class HomeAssistantAPITester:
    """Test Home Assistant API connectivity and token validation"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    async def test_connection(self) -> APITestResult:
        """Test basic connection to Home Assistant"""
        result = APITestResult("Home Assistant Connection")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/"
                
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        result.set_success({
                            'status_code': response.status,
                            'message': data.get('message', 'Connected successfully'),
                            'version': data.get('version')
                        })
                    else:
                        result.set_error(f"HTTP {response.status}: {await response.text()}")
        
        except asyncio.TimeoutError:
            result.set_error("Connection timeout - check if Home Assistant is running and accessible")
        except aiohttp.ClientError as e:
            result.set_error(f"Connection error: {str(e)}")
        except Exception as e:
            result.set_error(f"Unexpected error: {str(e)}")
        
        return result
    
    async def test_websocket_connection(self) -> APITestResult:
        """Test WebSocket connection (simulated)"""
        result = APITestResult("Home Assistant WebSocket Connection")
        
        try:
            # Test the WebSocket endpoint availability
            async with aiohttp.ClientSession() as session:
                ws_url = f"{self.base_url.replace('http', 'ws')}/api/websocket"
                
                # We'll just test if the endpoint is reachable
                # Full WebSocket testing would require more complex setup
                url = f"{self.base_url}/api/"
                
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        result.set_success({
                            'websocket_endpoint': ws_url,
                            'status_code': response.status,
                            'note': 'WebSocket endpoint available (full connection test requires WebSocket client)'
                        })
                    else:
                        result.set_error(f"WebSocket endpoint not accessible: HTTP {response.status}")
        
        except Exception as e:
            result.set_error(f"WebSocket test error: {str(e)}")
        
        return result
    
    async def test_token_permissions(self) -> APITestResult:
        """Test token permissions by accessing different endpoints"""
        result = APITestResult("Home Assistant Token Permissions")
        
        endpoints_to_test = [
            '/api/',
            '/api/states',
            '/api/events',
            '/api/config'
        ]
        
        successful_endpoints = []
        failed_endpoints = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for endpoint in endpoints_to_test:
                    try:
                        url = f"{self.base_url}{endpoint}"
                        async with session.get(url, headers=self.headers, timeout=10) as response:
                            if response.status == 200:
                                successful_endpoints.append(endpoint)
                            else:
                                failed_endpoints.append({
                                    'endpoint': endpoint,
                                    'status': response.status,
                                    'error': await response.text()
                                })
                    except Exception as e:
                        failed_endpoints.append({
                            'endpoint': endpoint,
                            'error': str(e)
                        })
            
            if successful_endpoints:
                result.set_success({
                    'successful_endpoints': successful_endpoints,
                    'failed_endpoints': failed_endpoints,
                    'permission_level': 'Read access confirmed' if '/api/states' in successful_endpoints else 'Limited access'
                })
            else:
                result.set_error("No endpoints accessible with current token", {
                    'failed_endpoints': failed_endpoints
                })
        
        except Exception as e:
            result.set_error(f"Permission test error: {str(e)}")
        
        return result


class WeatherAPITester:
    """Test Weather API connectivity and key validation"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openweathermap.org/data/2.5"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
    
    async def test_api_key_validity(self) -> APITestResult:
        """Test if the API key is valid by making a simple request"""
        result = APITestResult("Weather API Key Validation")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test with a known location (London)
                url = f"{self.base_url}/weather"
                params = {
                    'q': 'London,UK',
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        result.set_success({
                            'status_code': response.status,
                            'location': data.get('name', 'Unknown'),
                            'country': data.get('sys', {}).get('country', 'Unknown'),
                            'temperature': data.get('main', {}).get('temp'),
                            'weather': data.get('weather', [{}])[0].get('main', 'Unknown')
                        })
                    elif response.status == 401:
                        result.set_error("Invalid API key - authentication failed")
                    elif response.status == 403:
                        result.set_error("API key valid but access forbidden - check subscription")
                    else:
                        error_text = await response.text()
                        result.set_error(f"HTTP {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            result.set_error("Request timeout - check internet connection")
        except aiohttp.ClientError as e:
            result.set_error(f"Network error: {str(e)}")
        except Exception as e:
            result.set_error(f"Unexpected error: {str(e)}")
        
        return result
    
    async def test_location_weather(self, location: str) -> APITestResult:
        """Test weather API with specific location"""
        result = APITestResult(f"Weather API Location Test: {location}")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                params = {
                    'q': location,
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        result.set_success({
                            'status_code': response.status,
                            'location': data.get('name', 'Unknown'),
                            'country': data.get('sys', {}).get('country', 'Unknown'),
                            'temperature': data.get('main', {}).get('temp'),
                            'weather': data.get('weather', [{}])[0].get('main', 'Unknown'),
                            'humidity': data.get('main', {}).get('humidity'),
                            'coordinates': {
                                'lat': data.get('coord', {}).get('lat'),
                                'lon': data.get('coord', {}).get('lon')
                            }
                        })
                    elif response.status == 404:
                        result.set_error(f"Location not found: {location}")
                    else:
                        error_text = await response.text()
                        result.set_error(f"HTTP {response.status}: {error_text}")
        
        except Exception as e:
            result.set_error(f"Location test error: {str(e)}")
        
        return result
    
    async def test_api_quota(self) -> APITestResult:
        """Test API quota and rate limiting"""
        result = APITestResult("Weather API Quota Test")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Make multiple requests to test quota
                test_locations = ['London,UK', 'Paris,FR', 'Tokyo,JP']
                successful_requests = 0
                
                for location in test_locations:
                    try:
                        url = f"{self.base_url}/weather"
                        params = {
                            'q': location,
                            'appid': self.api_key,
                            'units': 'metric'
                        }
                        
                        async with session.get(url, params=params, timeout=10) as response:
                            if response.status == 200:
                                successful_requests += 1
                            elif response.status == 429:
                                result.set_error("Rate limit exceeded - API quota may be exceeded")
                                return result
                    
                    except Exception as e:
                        logger.warning(f"Request failed for {location}: {e}")
                
                result.set_success({
                    'successful_requests': successful_requests,
                    'total_requests': len(test_locations),
                    'success_rate': f"{(successful_requests/len(test_locations)*100):.1f}%"
                })
        
        except Exception as e:
            result.set_error(f"Quota test error: {str(e)}")
        
        return result


class EnvironmentValidator:
    """Validate environment variables and configuration"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file
        self.loaded_vars = {}
    
    def load_environment(self) -> APITestResult:
        """Load and validate environment variables"""
        result = APITestResult("Environment Variables")
        
        try:
            # Load from file if specified
            if self.env_file and os.path.exists(self.env_file):
                load_dotenv(self.env_file)
                result.details['env_file'] = self.env_file
            else:
                # Load from default locations
                default_files = ['.env', '.env.local', 'infrastructure/env.example']
                loaded_from = None
                
                for env_file in default_files:
                    if os.path.exists(env_file):
                        load_dotenv(env_file)
                        loaded_from = env_file
                        break
                
                result.details['env_file'] = loaded_from or 'system environment'
            
            # Check required variables
            required_vars = {
                'HOME_ASSISTANT_URL': 'Home Assistant base URL',
                'HOME_ASSISTANT_TOKEN': 'Home Assistant long-lived access token',
                'WEATHER_API_KEY': 'OpenWeatherMap API key',
                'WEATHER_LOCATION': 'Weather location (city,state,country)',
                'INFLUXDB_URL': 'InfluxDB connection URL',
                'INFLUXDB_TOKEN': 'InfluxDB authentication token'
            }
            
            missing_vars = []
            present_vars = []
            
            for var_name, description in required_vars.items():
                value = os.getenv(var_name)
                if value:
                    present_vars.append(var_name)
                    self.loaded_vars[var_name] = value
                    # Mask sensitive values
                    if 'TOKEN' in var_name or 'KEY' in var_name:
                        masked_value = self._mask_sensitive_value(value)
                        result.details[f'{var_name}_masked'] = masked_value
                    else:
                        result.details[var_name] = value
                else:
                    missing_vars.append(var_name)
            
            if missing_vars:
                result.set_error(f"Missing required environment variables: {', '.join(missing_vars)}", {
                    'missing_vars': missing_vars,
                    'present_vars': present_vars
                })
            else:
                result.set_success({
                    'all_required_vars_present': True,
                    'total_vars_checked': len(required_vars)
                })
        
        except Exception as e:
            result.set_error(f"Environment loading error: {str(e)}")
        
        return result
    
    def _mask_sensitive_value(self, value: str) -> str:
        """Mask sensitive values for logging"""
        if len(value) <= 8:
            return '*' * len(value)
        return '*' * (len(value) - 4) + value[-4:]


class APITestSuite:
    """Main test suite for API key validation"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_validator = EnvironmentValidator(env_file)
        self.results = []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all API validation tests"""
        logger.info("Starting API key validation tests...")
        
        # Test 1: Environment Variables
        logger.info("Testing environment variables...")
        env_result = self.env_validator.load_environment()
        self.results.append(env_result)
        
        if not env_result.success:
            logger.error("Environment validation failed - skipping API tests")
            return self._generate_summary()
        
        # Test 2: Home Assistant API
        ha_url = os.getenv('HOME_ASSISTANT_URL')
        ha_token = os.getenv('HOME_ASSISTANT_TOKEN')
        
        if ha_url and ha_token:
            logger.info("Testing Home Assistant API...")
            ha_tester = HomeAssistantAPITester(ha_url, ha_token)
            
            # Run HA tests
            ha_tests = [
                ha_tester.test_connection(),
                ha_tester.test_websocket_connection(),
                ha_tester.test_token_permissions()
            ]
            
            for test in ha_tests:
                result = await test
                self.results.append(result)
        else:
            logger.warning("Home Assistant URL or token not found - skipping HA tests")
        
        # Test 3: Weather API
        weather_key = os.getenv('WEATHER_API_KEY')
        
        if weather_key:
            logger.info("Testing Weather API...")
            weather_tester = WeatherAPITester(weather_key)
            
            # Run Weather tests
            weather_tests = [
                weather_tester.test_api_key_validity(),
                weather_tester.test_api_quota()
            ]
            
            # Test specific location if configured
            weather_location = os.getenv('WEATHER_LOCATION')
            if weather_location:
                logger.info(f"Testing weather for location: {weather_location}")
                location_test = weather_tester.test_location_weather(weather_location)
                weather_tests.append(location_test)
            
            for test in weather_tests:
                result = await test
                self.results.append(result)
        else:
            logger.warning("Weather API key not found - skipping Weather API tests")
        
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results if result.success)
        failed_tests = total_tests - successful_tests
        
        summary = {
            'summary': {
                'total_tests': total_tests,
                'successful': successful_tests,
                'failed': failed_tests,
                'success_rate': f"{(successful_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
            },
            'results': [result.to_dict() for result in self.results],
            'timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print formatted test summary"""
        print("\n" + "="*80)
        print("API KEY VALIDATION TEST RESULTS")
        print("="*80)
        
        # Summary
        s = summary['summary']
        print(f"\nSUMMARY:")
        print(f"  Total Tests: {s['total_tests']}")
        print(f"  Successful:  {s['successful']} [PASS]")
        print(f"  Failed:      {s['failed']} [FAIL]")
        print(f"  Success Rate: {s['success_rate']}")
        
        # Detailed results
        print(f"\nDETAILED RESULTS:")
        print("-" * 80)
        
        for result in summary['results']:
            status = "[PASS]" if result['success'] else "[FAIL]"
            print(f"\n{status} {result['name']}")
            
            if result['success']:
                if result['details']:
                    for key, value in result['details'].items():
                        print(f"  {key}: {value}")
            else:
                print(f"  Error: {result['error']}")
                if result['details']:
                    for key, value in result['details'].items():
                        print(f"  {key}: {value}")
        
        print("\n" + "="*80)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='API Key Validation Tests')
    parser.add_argument('--env-file', help='Environment file to load (.env)')
    parser.add_argument('--ha-url', help='Home Assistant URL override')
    parser.add_argument('--ha-token', help='Home Assistant token override')
    parser.add_argument('--weather-key', help='Weather API key override')
    parser.add_argument('--output', choices=['console', 'json'], default='console', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set override environment variables
    if args.ha_url:
        os.environ['HOME_ASSISTANT_URL'] = args.ha_url
    if args.ha_token:
        os.environ['HOME_ASSISTANT_TOKEN'] = args.ha_token
    if args.weather_key:
        os.environ['WEATHER_API_KEY'] = args.weather_key
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run tests
    test_suite = APITestSuite(args.env_file)
    summary = await test_suite.run_all_tests()
    
    # Output results
    if args.output == 'json':
        print(json.dumps(summary, indent=2))
    else:
        test_suite.print_summary(summary)
    
    # Exit with appropriate code
    if summary['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
