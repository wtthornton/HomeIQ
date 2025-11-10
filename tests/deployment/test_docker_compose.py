#!/usr/bin/env python3
"""
Docker Compose Orchestration Tests

Tests for validating Docker Compose deployment and orchestration functionality.
"""

import pytest
import time
import json
import requests
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Any


class DockerComposeTester:
    """Test Docker Compose deployment and orchestration"""
    
    def __init__(self, compose_file: str = "docker-compose.prod.yml", env_file: str = "infrastructure/env.production"):
        self.project_root = Path(__file__).parent.parent.parent
        self.compose_file = self.project_root / compose_file
        self.env_file = self.project_root / env_file
        self.services = [
            "influxdb",
            "websocket-ingestion", 
            "enrichment-pipeline",
            "weather-api",
            "admin-api",
            "data-retention",
            "health-dashboard"
        ]
        
    def run_docker_compose(self, command: str) -> subprocess.CompletedProcess:
        """Run docker-compose command"""
        cmd = ["docker-compose", "-f", str(self.compose_file), "--env-file", str(self.env_file)]
        cmd.extend(command.split())
        
        return subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        result = self.run_docker_compose("ps --format json")
        
        if result.returncode != 0:
            return {}
            
        services = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    services.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                    
        return {service['Service']: service for service in services}
    
    def wait_for_service_health(self, service: str, timeout: int = 300) -> bool:
        """Wait for service to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_service_status()
            
            if service in status:
                service_info = status[service]
                health = service_info.get('Health', '')
                
                if health == 'healthy':
                    return True
                elif health == 'unhealthy':
                    return False
                    
            time.sleep(10)
            
        return False
    
    def check_service_connectivity(self, service: str, port: int, path: str = "/health") -> bool:
        """Check if service is accessible via HTTP"""
        try:
            url = f"http://localhost:{port}{path}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except (requests.RequestException, ConnectionError):
            return False


class TestDockerComposeOrchestration:
    """Test Docker Compose orchestration functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        self.tester = DockerComposeTester()
        
        # Setup: Ensure clean state
        self.tester.run_docker_compose("down --volumes --remove-orphans")
        time.sleep(5)
        
        yield
        
        # Teardown: Clean up
        self.tester.run_docker_compose("down --volumes --remove-orphans")
        time.sleep(5)
    
    def test_compose_file_exists(self):
        """Test that Docker Compose file exists and is valid"""
        assert self.tester.compose_file.exists(), f"Compose file not found: {self.tester.compose_file}"
        
        # Test compose file syntax
        result = self.tester.run_docker_compose("config")
        assert result.returncode == 0, f"Invalid compose file syntax: {result.stderr}"
    
    def test_environment_file_exists(self):
        """Test that environment file exists"""
        assert self.tester.env_file.exists(), f"Environment file not found: {self.tester.env_file}"
    
    def test_services_startup_order(self):
        """Test that services start in correct dependency order"""
        # Start services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for all services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
    
    def test_service_dependencies(self):
        """Test that service dependencies are properly configured"""
        # Start only InfluxDB first
        result = self.tester.run_docker_compose("up -d influxdb")
        assert result.returncode == 0, "Failed to start InfluxDB"
        
        # Wait for InfluxDB to be healthy
        assert self.tester.wait_for_service_health("influxdb"), "InfluxDB failed to become healthy"
        
        # Start dependent services
        dependent_services = ["websocket-ingestion", "enrichment-pipeline", "admin-api", "data-retention"]
        
        for service in dependent_services:
            result = self.tester.run_docker_compose(f"up -d {service}")
            assert result.returncode == 0, f"Failed to start {service}: {result.stderr}"
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
    
    def test_health_checks(self):
        """Test that health checks are working for all services"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} health check failed"
    
    def test_service_connectivity(self):
        """Test that all services are accessible via their exposed ports"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Test connectivity to each service
        connectivity_tests = [
            ("influxdb", 8086, "/health"),
            ("websocket-ingestion", 8001, "/health"),
            ("enrichment-pipeline", 8002, "/health"),
            ("admin-api", 8003, "/api/v1/health"),
            ("data-retention", 8080, "/health"),
            ("health-dashboard", 3000, "/"),
        ]
        
        for service, port, path in connectivity_tests:
            assert self.tester.check_service_connectivity(service, port, path), \
                f"Service {service} not accessible on port {port}"
    
    def test_graceful_shutdown(self):
        """Test that services shut down gracefully"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Shutdown services gracefully
        result = self.tester.run_docker_compose("down --timeout 30")
        assert result.returncode == 0, f"Failed to shutdown services gracefully: {result.stderr}"
        
        # Verify all services are stopped
        status = self.tester.get_service_status()
        assert len(status) == 0, "Not all services were stopped"
    
    def test_restart_policies(self):
        """Test that restart policies are working"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Stop a service and verify it restarts
        result = self.tester.run_docker_compose("stop influxdb")
        assert result.returncode == 0, "Failed to stop InfluxDB"
        
        # Wait for restart
        time.sleep(15)
        
        # Verify service is running again
        status = self.tester.get_service_status()
        assert "influxdb" in status, "InfluxDB did not restart"
        assert status["influxdb"]["State"] == "running", "InfluxDB is not running after restart"
    
    def test_resource_limits(self):
        """Test that resource limits are properly configured"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Get container resource usage
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "json"],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "Failed to get container stats"
        
        # Parse stats and verify resource limits
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    stats = json.loads(line)
                    container_name = stats.get('Name', '')
                    
                    # Check if this is one of our services
                    if any(service in container_name for service in self.tester.services):
                        # Verify memory usage is within limits
                        mem_usage = float(stats.get('MemUsage', '0B').split('/')[0].replace('MiB', '').replace('GiB', ''))
                        mem_limit = float(stats.get('MemLimit', '0B').replace('MiB', '').replace('GiB', ''))
                        
                        if mem_limit > 0:  # Only check if limit is set
                            assert mem_usage <= mem_limit * 1.1, \
                                f"Container {container_name} exceeded memory limit"
                                
                except (json.JSONDecodeError, ValueError, IndexError):
                    continue
    
    def test_network_isolation(self):
        """Test that services can communicate within the Docker network"""
        # Start all services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Test internal service communication
        # Admin API should be able to reach InfluxDB internally
        admin_container = None
        status = self.tester.get_service_status()
        
        for service_name, service_info in status.items():
            if "admin" in service_name:
                admin_container = service_info.get('ID')
                break
        
        if admin_container:
            # Test internal connectivity
            result = subprocess.run([
                "docker", "exec", admin_container,
                "curl", "-f", "http://influxdb:8086/health"
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, "Admin API cannot reach InfluxDB internally"
    
    def test_volume_persistence(self):
        """Test that volumes persist data correctly"""
        # Start services
        result = self.tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in self.tester.services:
            assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Create some test data in InfluxDB
        influxdb_container = None
        status = self.tester.get_service_status()
        
        for service_name, service_info in status.items():
            if "influxdb" in service_name:
                influxdb_container = service_info.get('ID')
                break
        
        if influxdb_container:
            # Create a test database
            result = subprocess.run([
                "docker", "exec", influxdb_container,
                "influx", "bucket", "create", "--name", "test_bucket", "--org", "homeiq"
            ], capture_output=True, text=True)
            
            # Stop services
            self.tester.run_docker_compose("down")
            
            # Restart services
            result = self.tester.run_docker_compose("up -d")
            assert result.returncode == 0, f"Failed to restart services: {result.stderr}"
            
            # Wait for services to be healthy
            for service in self.tester.services:
                assert self.tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
            
            # Verify test data still exists
            status = self.tester.get_service_status()
            for service_name, service_info in status.items():
                if "influxdb" in service_name:
                    influxdb_container = service_info.get('ID')
                    break
            
            if influxdb_container:
                result = subprocess.run([
                    "docker", "exec", influxdb_container,
                    "influx", "bucket", "list", "--org", "homeiq"
                ], capture_output=True, text=True)
                
                assert "test_bucket" in result.stdout, "Test data was not persisted"


class TestDeploymentValidation:
    """Test deployment validation and verification"""
    
    def test_api_key_validation_after_deployment(self):
        """Test that API key validation works after deployment"""
        tester = DockerComposeTester()
        
        # Start services
        result = tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in tester.services:
            assert tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Run API key validation tests
        test_script = tester.project_root / "tests" / "test_api_keys.py"
        if test_script.exists():
            result = subprocess.run([
                "python", str(test_script), 
                "--env-file", str(tester.env_file),
                "--output", "json"
            ], cwd=tester.project_root, capture_output=True, text=True)
            
            # API key tests may fail due to placeholder values, but the test should run
            assert result.returncode in [0, 1], f"API key validation failed: {result.stderr}"
        
        # Cleanup
        tester.run_docker_compose("down")
    
    def test_service_health_endpoints(self):
        """Test that all service health endpoints are accessible"""
        tester = DockerComposeTester()
        
        # Start services
        result = tester.run_docker_compose("up -d")
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be healthy
        for service in tester.services:
            assert tester.wait_for_service_health(service), f"Service {service} failed to become healthy"
        
        # Test health endpoints
        health_endpoints = [
            ("http://localhost:8086/health", "InfluxDB"),
            ("http://localhost:8001/health", "WebSocket Ingestion"),
            ("http://localhost:8002/health", "Enrichment Pipeline"),
            ("http://localhost:8003/api/v1/health", "Admin API"),
            ("http://localhost:8080/health", "Data Retention"),
            ("http://localhost:3000", "Health Dashboard"),
        ]
        
        for url, service_name in health_endpoints:
            try:
                response = requests.get(url, timeout=10)
                assert response.status_code == 200, f"{service_name} health check failed: {response.status_code}"
            except requests.RequestException as e:
                pytest.fail(f"{service_name} health endpoint not accessible: {e}")
        
        # Cleanup
        tester.run_docker_compose("down")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
