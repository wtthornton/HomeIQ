#!/usr/bin/env python3
"""
Phase 2: Batch Rebuild Orchestrator

Coordinates migration of 35+ services across 5 breaking changes:
- pytest-asyncio 1.3.0
- tenacity 9.1.2
- asyncio-mqtt -> aiomqtt 2.4.0
- influxdb3-python 0.17.0
- python-dotenv 1.2.1 (non-breaking)

Story: PHASE2-006
Author: Claude (Phase 2 Migration)
Date: 2026-02-05
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Types of migrations"""
    PYTEST_ASYNCIO = "pytest-asyncio"
    TENACITY = "tenacity"
    MQTT = "mqtt"
    INFLUXDB = "influxdb"


@dataclass
class ServiceMigration:
    """Service migration configuration"""
    name: str
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    migrations: List[MigrationType]
    phase: str  # A, B, C, D

    @property
    def risk_level(self) -> str:
        """Calculate risk level based on priority and migration count"""
        if self.priority == "CRITICAL":
            return "VERY HIGH"
        elif len(self.migrations) >= 3:
            return "VERY HIGH"
        elif len(self.migrations) == 2:
            return "HIGH"
        elif self.priority == "HIGH":
            return "HIGH"
        elif self.priority == "MEDIUM":
            return "MEDIUM"
        else:
            return "LOW"


class Phase2Orchestrator:
    """Orchestrates Phase 2 batch migrations"""

    def __init__(self, dry_run: bool = False, phase: Optional[str] = None, skip_tests: bool = False):
        self.dry_run = dry_run
        self.phase = phase
        self.skip_tests = skip_tests
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent

        # Migration scripts
        self.scripts = {
            MigrationType.PYTEST_ASYNCIO: self.script_dir / "library-upgrade-pytest-asyncio-1.3.0.py",
            MigrationType.TENACITY: self.script_dir / "library-upgrade-tenacity-9.1.2.py",
            MigrationType.MQTT: self.script_dir / "library-upgrade-mqtt-aiomqtt-2.4.0.py",
            MigrationType.INFLUXDB: self.script_dir / "library-upgrade-influxdb3-python-0.17.0.py",
        }

        # Service configuration (from dependency analysis)
        self.services = self._load_service_config()

        # Results tracking
        self.results: Dict[str, Dict] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def _load_service_config(self) -> Dict[str, ServiceMigration]:
        """Load service migration configuration"""
        # Based on phase2-dependency-analysis.md
        services = {}

        # Phase A: Low-Risk Test Group (4 services)
        services["automation-miner"] = ServiceMigration("automation-miner", "LOW", [MigrationType.PYTEST_ASYNCIO], "A")
        services["blueprint-index"] = ServiceMigration("blueprint-index", "LOW", [MigrationType.PYTEST_ASYNCIO], "A")
        services["ha-setup-service"] = ServiceMigration("ha-setup-service", "LOW", [MigrationType.PYTEST_ASYNCIO], "A")
        services["ha-simulator"] = ServiceMigration("ha-simulator", "LOW", [MigrationType.PYTEST_ASYNCIO], "A")  # MQTT already done

        # Phase A: InfluxDB low-risk
        services["air-quality-service"] = ServiceMigration("air-quality-service", "LOW", [MigrationType.INFLUXDB], "A")
        services["calendar-service"] = ServiceMigration("calendar-service", "LOW", [MigrationType.INFLUXDB], "A")
        services["carbon-intensity-service"] = ServiceMigration("carbon-intensity-service", "LOW", [MigrationType.INFLUXDB], "A")
        services["electricity-pricing-service"] = ServiceMigration("electricity-pricing-service", "LOW", [MigrationType.INFLUXDB], "A")

        # Phase A: Tenacity low-risk
        services["rag-service"] = ServiceMigration("rag-service", "MEDIUM", [MigrationType.TENACITY], "A")
        services["ai-automation-service-new"] = ServiceMigration("ai-automation-service-new", "HIGH", [MigrationType.TENACITY], "A")

        # Phase B: Medium-Risk Services (pytest-asyncio + tenacity)
        services["ai-pattern-service"] = ServiceMigration("ai-pattern-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "B")
        services["device-intelligence-service"] = ServiceMigration("device-intelligence-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "B")
        services["openvino-service"] = ServiceMigration("openvino-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "B")
        services["proactive-agent-service"] = ServiceMigration("proactive-agent-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "B")
        services["ha-ai-agent-service"] = ServiceMigration("ha-ai-agent-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "B")

        # Phase B: Medium-Risk Services (pytest-asyncio + influxdb)
        services["sports-api"] = ServiceMigration("sports-api", "LOW", [MigrationType.PYTEST_ASYNCIO, MigrationType.INFLUXDB], "B")
        services["weather-api"] = ServiceMigration("weather-api", "LOW", [MigrationType.PYTEST_ASYNCIO, MigrationType.INFLUXDB], "B")

        # Phase B: Medium-Risk Services (other)
        services["ai-query-service"] = ServiceMigration("ai-query-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO], "B")
        services["ai-training-service"] = ServiceMigration("ai-training-service", "MEDIUM", [MigrationType.PYTEST_ASYNCIO], "B")
        services["blueprint-suggestion-service"] = ServiceMigration("blueprint-suggestion-service", "LOW", [MigrationType.PYTEST_ASYNCIO], "B")

        # Phase B: InfluxDB medium-risk
        services["energy-correlator"] = ServiceMigration("energy-correlator", "MEDIUM", [MigrationType.INFLUXDB], "B")
        services["energy-forecasting"] = ServiceMigration("energy-forecasting", "MEDIUM", [MigrationType.INFLUXDB], "B")
        services["smart-meter-service"] = ServiceMigration("smart-meter-service", "MEDIUM", [MigrationType.INFLUXDB], "B")
        services["observability-dashboard"] = ServiceMigration("observability-dashboard", "LOW", [MigrationType.INFLUXDB], "B")

        # Phase C: High-Risk Services
        services["ai-core-service"] = ServiceMigration("ai-core-service", "HIGH", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "C")
        services["ml-service"] = ServiceMigration("ml-service", "HIGH", [MigrationType.PYTEST_ASYNCIO, MigrationType.TENACITY], "C")
        services["admin-api"] = ServiceMigration("admin-api", "HIGH", [MigrationType.PYTEST_ASYNCIO, MigrationType.INFLUXDB], "C")
        services["data-retention"] = ServiceMigration("data-retention", "HIGH", [MigrationType.PYTEST_ASYNCIO, MigrationType.MQTT, MigrationType.INFLUXDB], "C")

        # Phase D: Critical Services (SEQUENTIAL)
        services["api-automation-edge"] = ServiceMigration("api-automation-edge", "CRITICAL", [MigrationType.TENACITY, MigrationType.INFLUXDB], "D")
        services["data-api"] = ServiceMigration("data-api", "CRITICAL", [MigrationType.PYTEST_ASYNCIO, MigrationType.INFLUXDB], "D")
        services["websocket-ingestion"] = ServiceMigration("websocket-ingestion", "CRITICAL", [MigrationType.PYTEST_ASYNCIO, MigrationType.MQTT, MigrationType.INFLUXDB], "D")

        return services

    def run(self) -> bool:
        """
        Execute batch migration orchestration

        Returns:
            True if all migrations successful, False otherwise
        """
        self.start_time = datetime.now()

        logger.info("=" * 80)
        logger.info("Phase 2: Batch Rebuild Orchestration")
        logger.info("=" * 80)

        if self.dry_run:
            logger.warning("DRY RUN MODE - No changes will be made")

        # Determine phases to run
        phases_to_run = self._get_phases_to_run()

        logger.info(f"Phases to run: {', '.join(phases_to_run)}")
        logger.info(f"Total services: {sum(1 for s in self.services.values() if s.phase in phases_to_run)}")
        logger.info("")

        # Run each phase
        all_success = True
        for phase in phases_to_run:
            logger.info("=" * 80)
            logger.info(f"PHASE {phase}")
            logger.info("=" * 80)

            success = self._run_phase(phase)
            if not success:
                logger.error(f"Phase {phase} failed - stopping orchestration")
                all_success = False
                break

            logger.info(f"Phase {phase} completed successfully")
            logger.info("")

        self.end_time = datetime.now()

        # Print summary
        self._print_summary()

        return all_success

    def _get_phases_to_run(self) -> List[str]:
        """Determine which phases to run"""
        if self.phase:
            if self.phase.upper() == "ALL":
                return ["A", "B", "C", "D"]
            else:
                return [self.phase.upper()]
        return ["A", "B", "C", "D"]

    def _run_phase(self, phase: str) -> bool:
        """
        Run migrations for a specific phase

        Args:
            phase: Phase letter (A, B, C, D)

        Returns:
            True if phase successful, False otherwise
        """
        # Get services for this phase
        phase_services = [s for s in self.services.values() if s.phase == phase]

        if not phase_services:
            logger.warning(f"No services in phase {phase}")
            return True

        logger.info(f"Phase {phase}: {len(phase_services)} services")

        # Phase D (Critical) runs sequentially with manual validation
        if phase == "D":
            return self._run_phase_sequential(phase_services)
        else:
            return self._run_phase_parallel(phase_services)

    def _run_phase_parallel(self, services: List[ServiceMigration]) -> bool:
        """Run migrations in parallel (batch processing)"""
        success_count = 0
        failure_count = 0

        for service in services:
            logger.info(f"Migrating: {service.name} ({service.priority}, {len(service.migrations)} migrations)")

            success = self._migrate_service(service)

            if success:
                success_count += 1
                logger.info(f"[OK] {service.name} migrated successfully")
            else:
                failure_count += 1
                logger.error(f"[ERROR] {service.name} migration failed")

            logger.info("")

        # Summary
        logger.info("-" * 80)
        logger.info(f"Phase Summary: {success_count} success, {failure_count} failed")
        logger.info("-" * 80)

        # Fail if >20% failed
        if failure_count > 0 and (failure_count / len(services)) > 0.2:
            logger.error(f"Phase failed: >20% failure rate ({failure_count}/{len(services)})")
            return False

        return True

    def _run_phase_sequential(self, services: List[ServiceMigration]) -> bool:
        """Run critical services sequentially with manual validation"""
        for service in services:
            logger.info(f"[CRITICAL] Migrating: {service.name}")
            logger.info(f"Migrations: {[m.value for m in service.migrations]}")
            logger.info(f"Risk Level: {service.risk_level}")
            logger.info("")

            success = self._migrate_service(service)

            if not success:
                logger.error(f"[ERROR] CRITICAL service {service.name} migration failed")
                logger.error("Stopping Phase D - manual intervention required")
                return False

            logger.info(f"[OK] {service.name} migrated successfully")

            # Prompt for validation before next critical service (if not dry run and not last)
            if not self.dry_run and service != services[-1]:
                logger.info("")
                logger.warning(f"CRITICAL service migrated: {service.name}")
                logger.warning("Please validate service health before continuing")
                input("Press Enter to continue to next critical service, or Ctrl+C to stop...")
                logger.info("")

        logger.info("-" * 80)
        logger.info(f"Phase D Summary: All {len(services)} critical services migrated successfully")
        logger.info("-" * 80)

        return True

    def _migrate_service(self, service: ServiceMigration) -> bool:
        """
        Migrate a single service across all required migrations

        Args:
            service: Service configuration

        Returns:
            True if all migrations successful, False otherwise
        """
        service_path = self.project_root / "services" / service.name

        # Track results for this service
        service_results = {
            "name": service.name,
            "priority": service.priority,
            "migrations": {},
            "overall_success": True
        }

        # Run each migration type
        for migration_type in service.migrations:
            migration_success = self._run_migration(
                service_path,
                migration_type
            )

            service_results["migrations"][migration_type.value] = migration_success

            if not migration_success:
                service_results["overall_success"] = False
                logger.error(f"  [ERROR] {migration_type.value} migration failed for {service.name}")

        self.results[service.name] = service_results

        return service_results["overall_success"]

    def _run_migration(self, service_path: Path, migration_type: MigrationType) -> bool:
        """
        Run a specific migration type on a service

        Args:
            service_path: Path to service directory
            migration_type: Type of migration to run

        Returns:
            True if migration successful, False otherwise
        """
        script = self.scripts.get(migration_type)
        if not script or not script.exists():
            logger.error(f"Migration script not found: {script}")
            return False

        # Build command
        cmd = ["python", str(script), str(service_path)]

        if self.dry_run:
            cmd.append("--dry-run")

        if self.skip_tests:
            cmd.append("--skip-tests")

        logger.info(f"  Running: {migration_type.value} migration")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info(f"  [OK] {migration_type.value} migration completed")
                return True
            else:
                logger.error(f"  [ERROR] {migration_type.value} migration failed")
                logger.error(f"  Output: {result.stdout}")
                logger.error(f"  Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"  [ERROR] {migration_type.value} migration timed out")
            return False
        except Exception as e:
            logger.error(f"  [ERROR] {migration_type.value} migration exception: {e}")
            return False

    def _print_summary(self) -> None:
        """Print orchestration summary"""
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0

        print("\n" + "=" * 80)
        print("Phase 2 Batch Orchestration Summary")
        print("=" * 80)

        if self.dry_run:
            print("[DRY RUN] - No changes made")

        # Count results
        total = len(self.results)
        successful = sum(1 for r in self.results.values() if r["overall_success"])
        failed = total - successful

        print(f"\nTotal Services: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Duration: {duration:.1f}s")

        # By priority
        print("\nBy Priority:")
        for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            priority_services = [r for r in self.results.values() if r["priority"] == priority]
            if priority_services:
                priority_success = sum(1 for r in priority_services if r["overall_success"])
                print(f"  {priority}: {priority_success}/{len(priority_services)} successful")

        # By migration type
        print("\nBy Migration Type:")
        migration_stats = {}
        for service_result in self.results.values():
            for migration_type, success in service_result["migrations"].items():
                if migration_type not in migration_stats:
                    migration_stats[migration_type] = {"total": 0, "success": 0}
                migration_stats[migration_type]["total"] += 1
                if success:
                    migration_stats[migration_type]["success"] += 1

        for migration_type, stats in migration_stats.items():
            print(f"  {migration_type}: {stats['success']}/{stats['total']} successful")

        # Failed services
        if failed > 0:
            print("\nFailed Services:")
            for service_name, result in self.results.items():
                if not result["overall_success"]:
                    failed_migrations = [m for m, s in result["migrations"].items() if not s]
                    print(f"  {service_name}: {', '.join(failed_migrations)}")

        print("=" * 80)

        # Export results to JSON
        if not self.dry_run:
            results_file = self.project_root / f"phase2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nResults exported to: {results_file}")

        print("")


def main():
    parser = argparse.ArgumentParser(
        description='Phase 2 Batch Rebuild Orchestrator'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no changes)'
    )
    parser.add_argument(
        '--phase',
        choices=['a', 'b', 'c', 'd', 'A', 'B', 'C', 'D', 'all', 'ALL'],
        help='Run specific phase (a, b, c, d, or all)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test validation after migration'
    )

    args = parser.parse_args()

    orchestrator = Phase2Orchestrator(
        dry_run=args.dry_run,
        phase=args.phase,
        skip_tests=args.skip_tests
    )

    success = orchestrator.run()

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
