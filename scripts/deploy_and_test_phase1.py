#!/usr/bin/env python3
"""
Phase 1 Deployment and Testing Script
Deploys containerized AI services and runs comprehensive tests
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import httpx

# Service URLs
SERVICES = {
    "influxdb": "http://localhost:8086",
    "data-api": "http://localhost:8006",
    "openvino": "http://localhost:8019",
    "ml": "http://localhost:8021",
    "ai_core": "http://localhost:8018",
    "ner": "http://localhost:8031",
    "openai": "http://localhost:8020",
    "ai_automation": "http://localhost:8017",
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
        print("🔄 Waiting for services to be healthy...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            all_healthy = True
            for service_name, url in SERVICES.items():
                if not await self.check_service_health(service_name, url):
                    all_healthy = False
                    break

            if all_healthy:
                print("✅ All services are healthy!")
                return True

            print("⏳ Waiting for services...")
            await asyncio.sleep(10)

        print("❌ Timeout waiting for services to be healthy")
        return False

    def run_docker_compose(self, command: str):
        """Run docker-compose command"""
        try:
            result = subprocess.run(
                ["docker-compose", *command.split()],
                check=False, cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"✅ Docker-compose {command} succeeded")
                return True
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
        print("🔨 Building Phase 1 services...")

        services_to_build = [
            "openvino-service",
            "ml-service",
            "ai-core-service",
            "ner-service",
            "openai-service",
            "ai-automation-service",
        ]

        for service in services_to_build:
            print(f"Building {service}...")
            if not self.run_docker_compose(f"build {service}"):
                return False

        print("✅ All services built successfully")
        return True

    def start_services(self):
        """Start all services in dependency order"""
        print("🚀 Starting Phase 1 services...")

        # Start base services first
        print("Starting base services...")
        if not self.run_docker_compose("up -d influxdb data-api"):
            return False

        print("Waiting for base services...")
        time.sleep(30)

        # Start model services
        print("Starting model services...")
        if not self.run_docker_compose("up -d ner-service openai-service openvino-service ml-service"):
            return False

        print("Waiting for model services...")
        time.sleep(60)

        # Start orchestrator services
        print("Starting orchestrator services...")
        if not self.run_docker_compose("up -d ai-core-service ai-automation-service"):
            return False

        print("Waiting for orchestrator services...")
        time.sleep(30)

        print("✅ All services started")
        return True

    async def test_services(self):
        """Test all services"""
        print("🧪 Testing Phase 1 services...")

        # Wait for services to be healthy
        if not await self.wait_for_services():
            return False

        # Test individual services
        test_results = {}

        # Test OpenVINO Service
        print("Testing OpenVINO Service...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SERVICES['openvino']}/embeddings",
                    json={"texts": ["test pattern"], "normalize": True},
                )
                test_results["openvino"] = response.status_code == 200
        except Exception as e:
            print(f"OpenVINO test failed: {e}")
            test_results["openvino"] = False

        # Test ML Service
        print("Testing ML Service...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SERVICES['ml']}/cluster",
                    json={"data": [[1, 2], [3, 4]], "algorithm": "kmeans", "n_clusters": 2},
                )
                test_results["ml"] = response.status_code == 200
        except Exception as e:
            print(f"ML test failed: {e}")
            test_results["ml"] = False

        # Test AI Core Service
        print("Testing AI Core Service...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SERVICES['ai_core']}/analyze",
                    json={
                        "data": [{"description": "test pattern"}],
                        "analysis_type": "pattern_detection",
                    },
                )
                test_results["ai_core"] = response.status_code == 200
        except Exception as e:
            print(f"AI Core test failed: {e}")
            test_results["ai_core"] = False

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
            check=False, cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        print(result.stdout)

    def show_service_urls(self):
        """Show service URLs"""
        print("\n🔗 Service URLs:")
        for service, url in SERVICES.items():
            print(f"{service:15} {url}")

    async def run_full_deployment(self):
        """Run complete deployment and testing"""
        print("🚀 Phase 1 Containerized AI Services Deployment")
        print("=" * 60)

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
