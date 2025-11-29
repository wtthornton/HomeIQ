#!/usr/bin/env python3
"""
Phase 1 Deployment and Testing Script
Deploys containerized AI services and runs comprehensive tests
"""

import subprocess
import sys
import time
import httpx
import asyncio
import json
from pathlib import Path

# Import progress indicator from same directory
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from progress_indicator import Spinner, ProgressBar, StatusUpdater, print_step_header

# Service URLs
SERVICES = {
    "influxdb": "http://localhost:8086",
    "data-api": "http://localhost:8006",
    "openvino": "http://localhost:8019",
    "ml": "http://localhost:8021", 
    "ai_core": "http://localhost:8018",
    "ner": "http://localhost:8031",
    "openai": "http://localhost:8020",
    "ai_automation": "http://localhost:8017"
}

class Phase1Deployment:
    """Phase 1 deployment and testing manager"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.services_healthy = {}
        
    async def check_service_health(self, service_name: str, url: str) -> bool:
        """Check if a service is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") == "healthy"
        except Exception as e:
            print(f"❌ {service_name} service check failed: {e}")
        return False
    
    async def wait_for_services(self, max_wait: int = 300):
        """Wait for all services to be healthy"""
        status = StatusUpdater("Waiting for services to be healthy")
        
        start_time = time.time()
        check_count = 0
        while time.time() - start_time < max_wait:
            all_healthy = True
            healthy_count = 0
            for service_name, url in SERVICES.items():
                if await self.check_service_health(service_name, url):
                    healthy_count += 1
                else:
                    all_healthy = False
            
            elapsed = time.time() - start_time
            status.update(f"Checking services... ({healthy_count}/{len(SERVICES)} healthy, {elapsed:.0f}s)")
            
            if all_healthy:
                status.finish(success=True, message="All services are healthy")
                return True
            
            check_count += 1
            await asyncio.sleep(10)
        
        status.finish(success=False, message="Timeout waiting for services to be healthy")
        return False
    
    def run_docker_compose(self, command: str, show_output: bool = False):
        """Run docker-compose command"""
        try:
            if show_output:
                # Show output in real-time for long-running commands
                result = subprocess.run(
                    ["docker-compose"] + command.split(),
                    cwd=self.project_root,
                    text=True,
                    timeout=300
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ["docker-compose"] + command.split(),
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    return True
                else:
                    print(f"❌ Docker-compose {command} failed")
                    print(f"STDOUT: {result.stdout}")
                    print(f"STDERR: {result.stderr}")
                    return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Docker-compose {command} timed out")
            return False
        except Exception as e:
            print(f"❌ Error running docker-compose {command}: {e}")
            return False
    
    def build_services(self):
        """Build all Phase 1 services"""
        print_step_header(1, 3, "Building Phase 1 Services")
        
        services_to_build = [
            "openvino-service",
            "ml-service", 
            "ai-core-service",
            "ner-service",
            "openai-service",
            "ai-automation-service"
        ]
        
        progress = ProgressBar(len(services_to_build), "Building services")
        
        for idx, service in enumerate(services_to_build, 1):
            progress.update(idx - 1)
            with Spinner(f"Building {service}") as spinner:
                if not self.run_docker_compose(f"build {service}", show_output=True):
                    spinner.stop(success=False, message=f"{service} build failed")
                    return False
                spinner.stop(success=True, message=f"{service} built")
        
        progress.finish(message="All services built successfully")
        return True
    
    def start_services(self):
        """Start all services in dependency order"""
        print_step_header(2, 3, "Starting Phase 1 Services")
        
        # Start base services first
        status = StatusUpdater("Starting base services")
        status.update("Starting influxdb and data-api...")
        if not self.run_docker_compose("up -d influxdb data-api", show_output=True):
            status.finish(success=False, message="Failed to start base services")
            return False
        status.finish(success=True, message="Base services started")
        
        # Wait for base services
        status = StatusUpdater("Waiting for base services")
        for i in range(6):  # 30 seconds / 5 second intervals
            status.update(f"Waiting... ({i*5}/30 seconds)")
            time.sleep(5)
        status.finish(success=True, message="Base services ready")
        
        # Start model services
        status = StatusUpdater("Starting model services")
        status.update("Starting ner-service, openai-service, openvino-service, ml-service...")
        if not self.run_docker_compose("up -d ner-service openai-service openvino-service ml-service", show_output=True):
            status.finish(success=False, message="Failed to start model services")
            return False
        status.finish(success=True, message="Model services started")
        
        # Wait for model services
        status = StatusUpdater("Waiting for model services")
        for i in range(12):  # 60 seconds / 5 second intervals
            status.update(f"Waiting... ({i*5}/60 seconds)")
            time.sleep(5)
        status.finish(success=True, message="Model services ready")
        
        # Start orchestrator services
        status = StatusUpdater("Starting orchestrator services")
        status.update("Starting ai-core-service and ai-automation-service...")
        if not self.run_docker_compose("up -d ai-core-service ai-automation-service", show_output=True):
            status.finish(success=False, message="Failed to start orchestrator services")
            return False
        status.finish(success=True, message="Orchestrator services started")
        
        # Wait for orchestrator services
        status = StatusUpdater("Waiting for orchestrator services")
        for i in range(6):  # 30 seconds / 5 second intervals
            status.update(f"Waiting... ({i*5}/30 seconds)")
            time.sleep(5)
        status.finish(success=True, message="All services started")
        
        return True
    
    async def test_services(self):
        """Test all services"""
        print_step_header(3, 3, "Testing Phase 1 Services")
        
        # Wait for services to be healthy
        if not await self.wait_for_services():
            return False
        
        # Test individual services
        test_results = {}
        services_to_test = [
            ('openvino', 'OpenVINO Service', lambda client: client.post(
                f"{SERVICES['openvino']}/embeddings",
                json={"texts": ["test pattern"], "normalize": True}
            )),
            ('ml', 'ML Service', lambda client: client.post(
                f"{SERVICES['ml']}/cluster",
                json={"data": [[1, 2], [3, 4]], "algorithm": "kmeans", "n_clusters": 2}
            )),
            ('ai_core', 'AI Core Service', lambda client: client.post(
                f"{SERVICES['ai_core']}/analyze",
                json={
                    "data": [{"description": "test pattern"}],
                    "analysis_type": "pattern_detection"
                }
            ))
        ]
        
        progress = ProgressBar(len(services_to_test), "Testing services")
        
        async with httpx.AsyncClient() as client:
            for idx, (key, name, test_func) in enumerate(services_to_test, 1):
                progress.update(idx - 1)
                with Spinner(f"Testing {name}") as spinner:
                    try:
                        response = await test_func(client)
                        test_results[key] = response.status_code == 200
                        if test_results[key]:
                            spinner.stop(success=True, message=f"{name} test passed")
                        else:
                            spinner.stop(success=False, message=f"{name} test failed (status {response.status_code})")
                    except Exception as e:
                        test_results[key] = False
                        spinner.stop(success=False, message=f"{name} test failed: {str(e)[:50]}")
        
        progress.finish(message="Service testing completed")
        
        # Print test results
        print("\n📊 Test Results:")
        for service, passed in test_results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{service:15} {status}")
        
        return all(test_results.values())
    
    def show_service_status(self):
        """Show current service status"""
        print("\n📊 Service Status:")
        result = subprocess.run(
            ["docker-compose", "ps"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        print(result.stdout)
    
    def show_service_urls(self):
        """Show service URLs"""
        print("\n🔗 Service URLs:")
        for service, url in SERVICES.items():
            print(f"{service:15} {url}")
    
    async def run_full_deployment(self):
        """Run complete deployment and testing"""
        print("\n" + "="*80)
        print("Phase 1 Containerized AI Services Deployment")
        print("="*80 + "\n")
        
        # Step 1: Build services
        if not self.build_services():
            print("❌ Build failed")
            return False
        
        # Step 2: Start services
        if not self.start_services():
            print("❌ Start failed")
            return False
        
        # Step 3: Test services
        if not await self.test_services():
            print("❌ Tests failed")
            return False
        
        # Step 4: Show status
        self.show_service_status()
        self.show_service_urls()
        
        print("\n🎉 Phase 1 deployment successful!")
        print("All containerized AI services are running and healthy.")
        
        return True

async def main():
    """Main function"""
    deployment = Phase1Deployment()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "build":
            deployment.build_services()
        elif command == "start":
            deployment.start_services()
        elif command == "test":
            await deployment.test_services()
        elif command == "status":
            deployment.show_service_status()
        elif command == "urls":
            deployment.show_service_urls()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    else:
        # Run full deployment
        success = await deployment.run_full_deployment()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
