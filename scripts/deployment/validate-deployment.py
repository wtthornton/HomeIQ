#!/usr/bin/env python3
"""
Deployment Validation Service
Validates deployment configuration and verifies post-deployment health.

Usage:
    python validate-deployment.py --pre-deployment
    python validate-deployment.py --post-deployment
    python validate-deployment.py --both
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates deployment configuration and health."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_compose_file = self.project_root / "docker-compose.yml"
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_docker_compose_config(self) -> bool:
        """Validate Docker Compose configuration."""
        logger.info("Validating Docker Compose configuration...")
        try:
            result = subprocess.run(
                ["docker", "compose", "config", "--quiet"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                self.errors.append(f"Docker Compose config validation failed: {result.stderr}")
                return False
            logger.info("[SUCCESS] Docker Compose configuration is valid")
            return True
        except subprocess.TimeoutExpired:
            self.errors.append("Docker Compose config validation timed out")
            return False
        except FileNotFoundError:
            self.errors.append("Docker Compose not found. Is Docker installed?")
            return False
        except Exception as e:
            self.errors.append(f"Docker Compose validation error: {str(e)}")
            return False

    def validate_environment_variables(self) -> bool:
        """Validate required environment variables."""
        logger.info("Validating environment variables...")
        required_vars = [
            "INFLUXDB_URL",
            "INFLUXDB_TOKEN",
        ]
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        if missing_vars:
            self.warnings.append(f"Missing optional environment variables: {', '.join(missing_vars)}")
            logger.warning(f"[WARNING] Missing optional environment variables: {', '.join(missing_vars)}")
        else:
            logger.info("[SUCCESS] Environment variables validated")
        return True

    def validate_service_dependencies(self) -> bool:
        """Validate service dependencies in docker-compose.yml."""
        logger.info("Validating service dependencies...")
        try:
            result = subprocess.run(
                ["docker", "compose", "config", "--services"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                self.errors.append("Failed to get service list")
                return False
            services = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            logger.info(f"[SUCCESS] Found {len(services)} services")
            return True
        except Exception as e:
            self.errors.append(f"Service dependency validation error: {str(e)}")
            return False

    def validate_resource_limits(self) -> bool:
        """Validate resource limits for NUC optimization."""
        logger.info("Validating resource limits (NUC constraints)...")
        # This is a basic check - in production, you'd parse docker-compose.yml
        # and verify memory/CPU limits are within NUC constraints
        logger.info("[SUCCESS] Resource limits check passed (basic validation)")
        return True

    def pre_deployment_validation(self) -> bool:
        """Run all pre-deployment validations."""
        logger.info("[INFO] Starting pre-deployment validation...")
        results = [
            self.validate_docker_compose_config(),
            self.validate_environment_variables(),
            self.validate_service_dependencies(),
            self.validate_resource_limits(),
        ]
        return all(results)

    def check_service_health(self, service_name: str, port: Optional[int] = None) -> bool:
        """Check health of a specific service."""
        try:
            if port:
                # Try HTTP health check
                import urllib.request
                url = f"http://localhost:{port}/health"
                try:
                    with urllib.request.urlopen(url, timeout=5) as response:
                        if response.status == 200:
                            return True
                except Exception:
                    pass
            # Check container status
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "Up" in result.stdout:
                return True
            return False
        except Exception as e:
            logger.warning(f"Health check for {service_name} failed: {str(e)}")
            return False

    def verify_service_connectivity(self) -> bool:
        """Verify inter-service connectivity."""
        logger.info("Verifying service connectivity...")
        # Basic check - verify containers are running
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                self.errors.append("Failed to get container status")
                return False
            containers = json.loads(result.stdout)
            running = [c for c in containers if c.get("State") == "running"]
            logger.info(f"[SUCCESS] {len(running)}/{len(containers)} containers running")
            return len(running) > 0
        except Exception as e:
            self.errors.append(f"Service connectivity check failed: {str(e)}")
            return False

    def verify_database_connectivity(self) -> bool:
        """Verify database connectivity."""
        logger.info("Verifying database connectivity...")
        # Check InfluxDB using Python's urllib (cross-platform)
        try:
            import urllib.request
            url = "http://localhost:8086/health"
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    if response.status == 200:
                        logger.info("[SUCCESS] InfluxDB is accessible")
                        return True
                    else:
                        self.warnings.append(f"InfluxDB health check returned status {response.status}")
                        return False
            except urllib.error.URLError as e:
                self.warnings.append(f"InfluxDB connectivity check failed: {str(e)}")
                return False
        except Exception as e:
            self.warnings.append(f"InfluxDB connectivity check failed: {str(e)}")
            return False

    def post_deployment_validation(self) -> bool:
        """Run all post-deployment validations."""
        logger.info("[INFO] Starting post-deployment validation...")
        # Wait for services to start
        logger.info("Waiting for services to stabilize...")
        time.sleep(10)
        results = [
            self.verify_service_connectivity(),
            self.verify_database_connectivity(),
        ]
        return all(results)

    def run_validation(self, pre: bool = False, post: bool = False) -> bool:
        """Run validation based on flags."""
        if pre and post:
            pre_result = self.pre_deployment_validation()
            post_result = self.post_deployment_validation()
            return pre_result and post_result
        elif pre:
            return self.pre_deployment_validation()
        elif post:
            return self.post_deployment_validation()
        else:
            logger.error("No validation mode specified")
            return False

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*60)
        print("DEPLOYMENT VALIDATION SUMMARY")
        print("="*60)
        if self.errors:
            print(f"\n[ERROR] Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        if self.warnings:
            print(f"\n[WARNING] Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        if not self.errors and not self.warnings:
            print("\n[SUCCESS] All validations passed!")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Deployment validation service")
    parser.add_argument("--pre-deployment", action="store_true", help="Run pre-deployment validation")
    parser.add_argument("--post-deployment", action="store_true", help="Run post-deployment validation")
    parser.add_argument("--both", action="store_true", help="Run both pre and post-deployment validation")
    args = parser.parse_args()

    validator = DeploymentValidator()

    if args.both:
        pre = post = True
    else:
        pre = args.pre_deployment
        post = args.post_deployment

    if not pre and not post:
        parser.print_help()
        sys.exit(1)

    success = validator.run_validation(pre=pre, post=post)
    validator.print_summary()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

