#!/usr/bin/env python3
"""
End-to-End Device Verification Test
Verifies that devices are correctly discovered, stored, and used throughout the system.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8006")
WEBSOCKET_INGESTION_URL = os.getenv("WEBSOCKET_INGESTION_URL", "http://localhost:8001")
DB_PATH = "services/data-api/data/metadata.db"
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

class DeviceVerificationTest:
    """End-to-end device verification test suite"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []

    def run_all_tests(self):
        """Run all verification tests"""
        print_header("E2E DEVICE VERIFICATION TEST SUITE")
        print_info(f"Started at: {datetime.now().isoformat()}")

        # Test 1: Check service health
        self.test_service_health()

        # Test 2: Check database exists
        self.test_database_exists()

        # Test 3: Check entities in database
        self.test_entities_in_database()

        # Test 4: Check device name fields
        self.test_device_name_fields()

        # Test 5: Check discovery service
        self.test_discovery_service()

        # Test 6: Check data-api endpoints
        self.test_data_api_endpoints()

        # Test 7: Check event enrichment (if applicable)
        self.test_event_enrichment()

        # Print summary
        self.print_summary()

    def test_service_health(self):
        """Test 1: Verify all required services are healthy"""
        print_header("TEST 1: Service Health Check")

        services = {
            "data-api": DATA_API_URL,
            "websocket-ingestion": WEBSOCKET_INGESTION_URL,
        }

        for service_name, url in services.items():
            try:
                health_url = f"{url}/health"
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print_success(f"{service_name} is healthy")
                else:
                    print_error(f"{service_name} returned status {response.status_code}")
                    self.errors.append(f"{service_name} health check failed")
            except Exception as e:
                print_error(f"{service_name} is not reachable: {e}")
                self.errors.append(f"{service_name} is not reachable")

    def test_database_exists(self):
        """Test 2: Verify SQLite database exists"""
        print_header("TEST 2: Database Existence Check")

        if os.path.exists(DB_PATH):
            print_success(f"Database exists at {DB_PATH}")

            # Check database is readable
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print_success(f"Database is readable. Found {len(tables)} tables")
                conn.close()
            except Exception as e:
                print_error(f"Database is not readable: {e}")
                self.errors.append(f"Database read error: {e}")
        else:
            print_error(f"Database not found at {DB_PATH}")
            self.errors.append(f"Database not found at {DB_PATH}")

    def test_entities_in_database(self):
        """Test 3: Verify entities exist in database"""
        print_header("TEST 3: Entities in Database Check")

        if not os.path.exists(DB_PATH):
            print_error("Database not found, skipping test")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Check entities table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities';")
            if cursor.fetchone():
                print_success("Entities table exists")
            else:
                print_error("Entities table does not exist")
                self.errors.append("Entities table missing")
                conn.close()
                return

            # Count entities
            cursor.execute("SELECT COUNT(*) FROM entities;")
            count = cursor.fetchone()[0]
            print_info(f"Total entities in database: {count}")

            if count == 0:
                print_warning("No entities found in database. Discovery may not have run.")
                self.warnings.append("No entities in database")
            else:
                print_success(f"Found {count} entities in database")

            # Check for Hue entities specifically
            cursor.execute("SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%hue%';")
            hue_count = cursor.fetchone()[0]
            print_info(f"Hue entities found: {hue_count}")

            if hue_count == 0:
                print_warning("No Hue entities found. This may be expected if no Hue devices are configured.")
                self.warnings.append("No Hue entities found")

            conn.close()

        except Exception as e:
            print_error(f"Error checking entities: {e}")
            self.errors.append(f"Entity check error: {e}")

    def test_device_name_fields(self):
        """Test 4: Verify device name fields are populated correctly"""
        print_header("TEST 4: Device Name Fields Check")

        if not os.path.exists(DB_PATH):
            print_error("Database not found, skipping test")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Check for entities with missing name fields
            cursor.execute("""
                SELECT entity_id, name, name_by_user, original_name, friendly_name
                FROM entities
                WHERE entity_id LIKE '%hue%'
                LIMIT 10
            """)

            rows = cursor.fetchall()

            if not rows:
                print_warning("No Hue entities found to check")
                return

            print_info(f"Checking {len(rows)} Hue entities for name fields...")
            print(f"\n{'Entity ID':<40} {'name':<20} {'name_by_user':<20} {'original_name':<20} {'friendly_name':<20}")
            print("-" * 120)

            issues_found = False
            for row in rows:
                entity_id, name, name_by_user, original_name, friendly_name = row
                print(f"{entity_id:<40} {name or ''!s:<20} {name_by_user or ''!s:<20} {original_name or ''!s:<20} {friendly_name or ''!s:<20}")

                # Check for common issues
                if not friendly_name and not name_by_user and not name:
                    print_warning(f"  → Entity {entity_id} has no name fields populated")
                    issues_found = True
                    self.warnings.append(f"Entity {entity_id} missing all name fields")

            if not issues_found:
                print_success("All checked entities have at least one name field populated")

            conn.close()

        except Exception as e:
            print_error(f"Error checking device name fields: {e}")
            self.errors.append(f"Device name check error: {e}")

    def test_discovery_service(self):
        """Test 5: Verify discovery service can be triggered"""
        print_header("TEST 5: Discovery Service Check")

        try:
            discovery_url = f"{WEBSOCKET_INGESTION_URL}/api/v1/discovery/trigger"
            response = requests.post(discovery_url, timeout=30)

            if response.status_code == 200:
                result = response.json()
                print_success("Discovery service is accessible")
                print_info(f"Discovery result: {json.dumps(result, indent=2)}")
            else:
                print_error(f"Discovery service returned status {response.status_code}")
                print_info(f"Response: {response.text}")
                self.errors.append(f"Discovery service failed: {response.status_code}")

        except Exception as e:
            print_error(f"Error triggering discovery: {e}")
            self.errors.append(f"Discovery service error: {e}")

    def test_data_api_endpoints(self):
        """Test 6: Verify data-api endpoints for entities"""
        print_header("TEST 6: Data API Endpoints Check")

        endpoints = [
            "/api/v1/entities",
            "/api/v1/entities?limit=10",
        ]

        for endpoint in endpoints:
            try:
                url = f"{DATA_API_URL}{endpoint}"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        print_success(f"{endpoint} returned {len(data)} entities")
                    elif isinstance(data, dict) and "entities" in data:
                        print_success(f"{endpoint} returned {len(data['entities'])} entities")
                    else:
                        print_info(f"{endpoint} returned: {type(data)}")
                else:
                    print_error(f"{endpoint} returned status {response.status_code}")
                    self.errors.append(f"Data API endpoint {endpoint} failed")

            except Exception as e:
                print_error(f"Error checking {endpoint}: {e}")
                self.errors.append(f"Data API endpoint {endpoint} error: {e}")

    def test_event_enrichment(self):
        """Test 7: Check if events are being enriched with device names"""
        print_header("TEST 7: Event Enrichment Check")

        print_info("Checking if event enrichment code exists...")

        # This would require checking the codebase or logs
        # For now, we'll check if there's any evidence of enrichment
        print_warning("Event enrichment check requires code inspection")
        print_info("Manual check needed: Verify if websocket-ingestion enriches events with device names")
        self.warnings.append("Event enrichment check needs manual verification")

    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")

        len(self.successes) + len(self.warnings) + len(self.errors)

        print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
        print(f"  {Colors.GREEN}[OK] Successes: {len(self.successes)}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[WARN] Warnings: {len(self.warnings)}{Colors.RESET}")
        print(f"  {Colors.RED}[ERROR] Errors: {len(self.errors)}{Colors.RESET}")

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
            sys.exit(0)  # Warnings don't fail the test
        else:
            sys.exit(0)

if __name__ == "__main__":
    test = DeviceVerificationTest()
    test.run_all_tests()

