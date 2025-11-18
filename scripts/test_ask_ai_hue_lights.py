#!/usr/bin/env python3
"""
E2E Test for Ask AI - Hue Lights Flash Automation
Tests the specific prompt about flashing Hue lights at the top of every hour.
"""

import sys
import os
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration
AI_AUTOMATION_URL = os.getenv('AI_AUTOMATION_URL', 'http://localhost:8024')
DATA_API_URL = os.getenv('DATA_API_URL', 'http://localhost:8006')
API_KEY = os.getenv('API_KEY', os.getenv('HOMEIQ_API_KEY', os.getenv('AI_AUTOMATION_API_KEY', 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR')))

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

class AskAIHueLightsTest:
    """E2E test for Ask AI Hue lights automation"""
    
    def __init__(self):
        self.test_prompt = (
            "In the office, flash all the Hue lights for 45 secs using the Hue Flash action. "
            "Do this at the top of every hour. Kick up the brightness to 100% when flashing. "
            "When 45 secs is over, return all lights back to their original state."
        )
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def run_all_tests(self):
        """Run all tests"""
        print_header("ASK AI - HUE LIGHTS FLASH AUTOMATION E2E TEST")
        print_info(f"Test started at: {datetime.now().isoformat()}")
        print_info(f"Test prompt: {self.test_prompt}\n")
        
        # Test 1: Check services are running
        self.test_services_running()
        
        # Test 2: Check if Hue entities exist in database
        self.test_hue_entities_in_database()
        
        # Test 3: Check if AI service can query entities
        self.test_ai_service_entity_query()
        
        # Test 4: Submit Ask AI request
        self.test_ask_ai_request()
        
        # Test 5: Verify response doesn't say "no Hue lights"
        self.test_response_has_hue_devices()
        
        # Print summary
        self.print_summary()
        
    def test_services_running(self):
        """Test 1: Verify services are running"""
        print_header("TEST 1: Service Health Check")
        
        services = {
            'ai-automation-service': AI_AUTOMATION_URL,
            'data-api': DATA_API_URL,
        }
        
        for service_name, url in services.items():
            try:
                health_url = f"{url}/health"
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print_success(f"{service_name} is healthy")
                    self.successes.append(f"{service_name} health check")
                else:
                    print_error(f"{service_name} returned status {response.status_code}")
                    self.errors.append(f"{service_name} health check failed")
            except Exception as e:
                print_error(f"{service_name} is not reachable: {e}")
                self.errors.append(f"{service_name} not reachable")
    
    def test_hue_entities_in_database(self):
        """Test 2: Check if Hue entities exist in database"""
        print_header("TEST 2: Hue Entities in Database")
        
        try:
            # Query data-api for Hue entities
            # Try different endpoint patterns
            endpoints = [
                '/api/v1/entities?domain=light&entity_id_like=hue',
                '/internal/entities?entity_id_like=hue',
            ]
            
            found_entities = False
            entity_count = 0
            
            for endpoint in endpoints:
                try:
                    url = f"{DATA_API_URL}{endpoint}"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        entities = []
                        
                        if isinstance(data, list):
                            entities = data
                        elif isinstance(data, dict):
                            entities = data.get('entities', data.get('data', []))
                        
                        hue_entities = [e for e in entities if 'hue' in str(e.get('entity_id', '')).lower()]
                        entity_count = len(hue_entities)
                        
                        if hue_entities:
                            found_entities = True
                            print_success(f"Found {entity_count} Hue entities via {endpoint}")
                            print_info(f"Sample entities: {[e.get('entity_id') for e in hue_entities[:5]]}")
                            break
                            
                except Exception as e:
                    print_warning(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            if not found_entities:
                # Try direct database query
                try:
                    import sqlite3
                    db_path = 'services/data-api/data/metadata.db'
                    if os.path.exists(db_path):
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        # First check total entity count
                        cursor.execute("SELECT COUNT(*) FROM entities")
                        total_count = cursor.fetchone()[0]
                        
                        if total_count == 0:
                            print_error("CRITICAL: Database has 0 entities - discovery is not working!")
                            print_warning("Expected: Many entities from Home Assistant (including Hue devices)")
                            print_warning("Actual: 0 entities discovered - this is NOT a correct answer")
                            self.errors.append("Database has 0 entities - discovery failed")
                            conn.close()
                            return False
                        
                        # Then check for Hue entities
                        cursor.execute("SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%hue%'")
                        count = cursor.fetchone()[0]
                        conn.close()
                        
                        if count > 0:
                            print_success(f"Found {count} Hue entities in database (out of {total_count} total)")
                            found_entities = True
                            entity_count = count
                        else:
                            print_error(f"No Hue entities found in database (but {total_count} total entities exist)")
                            print_warning("No Hue entities found - this may cause AI to say 'no Hue lights'")
                            self.errors.append("No Hue entities in database")
                    else:
                        print_error(f"Database not found at {db_path}")
                        self.errors.append("Database not found")
                except Exception as e:
                    print_error(f"Database query failed: {e}")
                    self.errors.append(f"Database query error: {e}")
            
            if found_entities:
                self.successes.append(f"Found {entity_count} Hue entities")
            else:
                self.warnings.append("No Hue entities found - this may cause AI to say 'no Hue lights'")
                
        except Exception as e:
            print_error(f"Error checking Hue entities: {e}")
            self.errors.append(f"Hue entity check error: {e}")
    
    def test_ai_service_entity_query(self):
        """Test 3: Check if AI service can query entities"""
        print_header("TEST 3: AI Service Entity Query")
        
        try:
            # Check if AI service has an endpoint to get entities
            endpoints = [
                '/api/v1/entities',
                '/api/v1/devices',
                '/health',  # At least verify service is accessible
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{AI_AUTOMATION_URL}{endpoint}"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        print_success(f"AI service endpoint {endpoint} is accessible")
                        self.successes.append(f"AI service {endpoint} accessible")
                    else:
                        print_warning(f"AI service endpoint {endpoint} returned {response.status_code}")
                        
                except Exception as e:
                    print_warning(f"AI service endpoint {endpoint} failed: {e}")
                    
        except Exception as e:
            print_error(f"Error checking AI service: {e}")
            self.errors.append(f"AI service check error: {e}")
    
    def test_ask_ai_request(self):
        """Test 4: Submit Ask AI request"""
        print_header("TEST 4: Submit Ask AI Request")
        
        try:
            # Find the correct endpoint for Ask AI
            ask_ai_endpoints = [
                '/api/v1/ask-ai/query',
                '/api/v1/ask-ai',
                '/api/v1/ask_ai',
                '/ask-ai',
                '/ask_ai',
            ]
            
            endpoint_found = False
            response_data = None
            
            for endpoint in ask_ai_endpoints:
                try:
                    url = f"{AI_AUTOMATION_URL}{endpoint}"
                    
                    payload = {
                        "query": self.test_prompt,
                        "user_id": "test_user",
                    }
                    
                    headers = {
                        "X-HomeIQ-API-Key": API_KEY,
                        "Content-Type": "application/json"
                    }
                    
                    print_info(f"Trying endpoint: {url}")
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    
                    if response.status_code in [200, 201]:
                        response_data = response.json()
                        print_success(f"Ask AI request successful via {endpoint}")
                        endpoint_found = True
                        self.successes.append(f"Ask AI request successful")
                        break
                    else:
                        print_warning(f"Endpoint {endpoint} returned {response.status_code}: {response.text[:200]}")
                        
                except Exception as e:
                    print_warning(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            if not endpoint_found:
                print_error("Could not find working Ask AI endpoint")
                self.errors.append("Ask AI endpoint not found")
                return None
            
            # Store response for next test
            self.last_response = response_data
            return response_data
            
        except Exception as e:
            print_error(f"Error submitting Ask AI request: {e}")
            self.errors.append(f"Ask AI request error: {e}")
            return None
    
    def test_response_has_hue_devices(self):
        """Test 5: Verify response doesn't say 'no Hue lights'"""
        print_header("TEST 5: Verify Response Has Hue Devices")
        
        if not hasattr(self, 'last_response'):
            print_warning("No response to check - skipping test")
            self.warnings.append("No response to check")
            return
        
        try:
            response = self.last_response
            
            # Check response structure
            print_info(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            # Look for indication of "no Hue lights" or similar
            response_text = json.dumps(response).lower()
            
            negative_indicators = [
                'no hue',
                'no hue lights',
                'no hue devices',
                'hue lights listed',
                'no devices',
                'no lights',
            ]
            
            found_negative = False
            for indicator in negative_indicators:
                if indicator in response_text:
                    print_error(f"Response contains negative indicator: '{indicator}'")
                    found_negative = True
                    self.errors.append(f"Response says '{indicator}'")
            
            # Look for positive indicators
            positive_indicators = [
                'hue',
                'light.hue',
                'entity_id',
                'devices',
            ]
            
            found_positive = False
            for indicator in positive_indicators:
                if indicator in response_text:
                    print_success(f"Response contains positive indicator: '{indicator}'")
                    found_positive = True
                    self.successes.append(f"Response mentions '{indicator}'")
            
            # Check for clarification questions
            if 'clarification' in response_text or 'questions' in response_text:
                print_warning("Response contains clarification questions")
                print_info("This may indicate the AI couldn't find devices")
                self.warnings.append("Clarification questions in response")
            
            # Print relevant parts of response
            if isinstance(response, dict):
                print_info("\nResponse summary:")
                for key in ['message', 'response', 'answer', 'suggestions', 'clarification']:
                    if key in response:
                        value = response[key]
                        if isinstance(value, str):
                            print_info(f"  {key}: {value[:200]}...")
                        elif isinstance(value, list):
                            print_info(f"  {key}: {len(value)} items")
                        else:
                            print_info(f"  {key}: {type(value).__name__}")
            
            if not found_negative and found_positive:
                print_success("Response appears to have found Hue devices")
            elif found_negative:
                print_error("Response indicates no Hue devices found")
            
        except Exception as e:
            print_error(f"Error checking response: {e}")
            self.errors.append(f"Response check error: {e}")
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
        print(f"  {Colors.GREEN}[OK] Successes: {len(self.successes)}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[WARN] Warnings: {len(self.warnings)}{Colors.RESET}")
        print(f"  {Colors.RED}[ERROR] Errors: {len(self.errors)}{Colors.RESET}")
        
        if self.successes:
            print(f"\n{Colors.BOLD}{Colors.GREEN}SUCCESSES:{Colors.RESET}")
            for success in self.successes:
                print(f"  • {success}")
        
        if self.errors:
            print(f"\n{Colors.BOLD}{Colors.RED}ERRORS:{Colors.RESET}")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}WARNINGS:{Colors.RESET}")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print(f"\n{Colors.BOLD}Completed at: {datetime.now().isoformat()}{Colors.RESET}\n")
        
        # Exit with appropriate code
        if self.errors:
            sys.exit(1)
        elif self.warnings:
            sys.exit(0)
        else:
            sys.exit(0)

if __name__ == "__main__":
    test = AskAIHueLightsTest()
    test.run_all_tests()

