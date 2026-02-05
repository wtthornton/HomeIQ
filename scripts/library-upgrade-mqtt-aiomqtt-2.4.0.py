#!/usr/bin/env python3
"""
Phase 2: asyncio-mqtt -> aiomqtt 2.4.0 Migration Script

Migrates services from asyncio-mqtt to aiomqtt.

BREAKING CHANGES:
1. Complete library replacement (asyncio-mqtt -> aiomqtt)
2. Package renamed: asyncio_mqtt -> aiomqtt
3. Client initialization API changed
4. Requires paho-mqtt 2.1.0 as dependency

Story: PHASE2-004
Author: Claude (Phase 2 Migration)
Date: 2026-02-05
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import subprocess
import shutil
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MQTTMigrator:
    """Migrate service from asyncio-mqtt to aiomqtt 2.4.0"""

    def __init__(self, service_path: Path, dry_run: bool = False, skip_tests: bool = False):
        self.service_path = service_path
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.changes: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.backup_dir: Optional[Path] = None

    def migrate(self) -> bool:
        """
        Execute full migration workflow

        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Starting asyncio-mqtt to aiomqtt migration for {self.service_path.name}")

        try:
            # Step 1: Validate service structure
            if not self._validate_service():
                return False

            # Step 2: Check if migration needed
            if not self._needs_migration():
                logger.info("Service already has aiomqtt - no migration needed")
                return True

            # Step 3: Create backup
            if not self.dry_run:
                self._create_backup()

            # Step 4: Find MQTT code usage
            mqtt_files = self._find_mqtt_usage()
            if mqtt_files:
                logger.warning(f"Found {len(mqtt_files)} files using MQTT - manual code review required")
                self.warnings.append(f"Found MQTT usage in {len(mqtt_files)} files - requires manual code migration")

            # Step 5: Migrate code (if needed)
            if mqtt_files:
                self._migrate_mqtt_code(mqtt_files)

            # Step 6: Update requirements.txt
            requirements_updated = self._update_requirements()

            # Step 7: Run tests to validate (unless skipped)
            if not self.dry_run and not self.skip_tests and requirements_updated:
                tests_passed = self._run_tests()
                if not tests_passed:
                    logger.warning("Tests failed after migration - rollback recommended")
                    self._create_rollback_script()
                    return False
            elif self.skip_tests:
                logger.info("  [OK] Skipped test validation (--skip-tests)")
                self.changes.append("Test validation skipped")

            # Step 8: Create rollback script
            if not self.dry_run:
                self._create_rollback_script()

            # Summary
            self._print_summary()

            return len(self.errors) == 0

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.errors.append(str(e))
            return False

    def _validate_service(self) -> bool:
        """Validate service has required structure"""
        logger.info("Validating service structure...")

        if not self.service_path.exists():
            self.errors.append(f"Service path does not exist: {self.service_path}")
            return False

        # Check for requirements.txt
        requirements_file = self.service_path / "requirements.txt"
        if not requirements_file.exists():
            self.errors.append(f"requirements.txt not found: {requirements_file}")
            return False

        logger.info("[OK] Service structure validated")
        return True

    def _needs_migration(self) -> bool:
        """Check if service needs MQTT migration"""
        requirements_file = self.service_path / "requirements.txt"
        content = requirements_file.read_text(encoding='utf-8')

        # Check if already has aiomqtt
        if re.search(r'aiomqtt\s*==\s*2\.4\.0', content):
            return False

        # Check if has asyncio-mqtt
        if not re.search(r'asyncio[-_]mqtt', content):
            logger.warning("Service does not use asyncio-mqtt - skipping")
            return False

        return True

    def _create_backup(self) -> None:
        """Create backup of service files before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.service_path / f".migration_backup_mqtt_{timestamp}"
        self.backup_dir.mkdir(exist_ok=True)

        logger.info(f"Creating backup at {self.backup_dir}")

        # Backup requirements.txt
        requirements = self.service_path / "requirements.txt"
        if requirements.exists():
            shutil.copy2(requirements, self.backup_dir / "requirements.txt")

        # Backup src directory
        src_dir = self.service_path / "src"
        if src_dir.exists():
            shutil.copytree(src_dir, self.backup_dir / "src", dirs_exist_ok=True)

        logger.info("[OK] Backup created")

    def _find_mqtt_usage(self) -> List[Path]:
        """
        Find all Python files using asyncio-mqtt

        Returns:
            List of file paths using MQTT
        """
        logger.info("Finding MQTT usage...")

        src_dir = self.service_path / "src"
        if not src_dir.exists():
            logger.info("No src directory - skipping MQTT code check")
            return []

        mqtt_files = []

        # Find all Python files with MQTT imports or usage
        for py_file in src_dir.glob("**/*.py"):
            content = py_file.read_text(encoding='utf-8')

            # Check for asyncio-mqtt imports
            if any(pattern in content for pattern in [
                'import asyncio_mqtt',
                'from asyncio_mqtt',
                'asyncio_mqtt.',
                'Client('  # MQTT Client usage
            ]):
                mqtt_files.append(py_file)

        logger.info(f"[OK] Found {len(mqtt_files)} files using MQTT")
        return mqtt_files

    def _migrate_mqtt_code(self, mqtt_files: List[Path]) -> None:
        """
        Migrate MQTT code from asyncio-mqtt to aiomqtt

        BREAKING CHANGES:
        1. import asyncio_mqtt -> import aiomqtt
        2. from asyncio_mqtt import Client -> from aiomqtt import Client
        3. asyncio_mqtt.Client(...) -> aiomqtt.Client(...)
        """
        logger.info("Migrating MQTT code...")

        for py_file in mqtt_files:
            updated = self._migrate_mqtt_file(py_file)
            if updated:
                self.changes.append(f"{py_file.relative_to(self.service_path)}: Updated MQTT imports")

    def _migrate_mqtt_file(self, py_file: Path) -> bool:
        """
        Migrate MQTT usage in a single file

        Returns:
            True if file was updated, False otherwise
        """
        content = py_file.read_text(encoding='utf-8')
        original_content = content
        updated = False

        # Replace import statements
        # import asyncio_mqtt -> import aiomqtt
        if 'import asyncio_mqtt' in content:
            content = content.replace('import asyncio_mqtt', 'import aiomqtt')
            updated = True
            logger.info(f"  [OK] Updated 'import asyncio_mqtt' -> 'import aiomqtt' in {py_file.name}")

        # from asyncio_mqtt import -> from aiomqtt import
        if 'from asyncio_mqtt import' in content:
            content = content.replace('from asyncio_mqtt import', 'from aiomqtt import')
            updated = True
            logger.info(f"  [OK] Updated 'from asyncio_mqtt import' -> 'from aiomqtt import' in {py_file.name}")

        # asyncio_mqtt. -> aiomqtt.
        if 'asyncio_mqtt.' in content:
            content = content.replace('asyncio_mqtt.', 'aiomqtt.')
            updated = True
            logger.info(f"  [OK] Updated 'asyncio_mqtt.' -> 'aiomqtt.' in {py_file.name}")

        if updated and not self.dry_run:
            py_file.write_text(content, encoding='utf-8')

        return updated

    def _update_requirements(self) -> bool:
        """Update requirements.txt to aiomqtt 2.4.0"""
        requirements_file = self.service_path / "requirements.txt"

        logger.info("Updating requirements.txt...")

        content = requirements_file.read_text(encoding='utf-8')
        original_content = content

        # Check if asyncio-mqtt exists
        if not re.search(r'asyncio[-_]mqtt', content):
            logger.warning("  [WARNING] asyncio-mqtt not found in requirements.txt")
            return False

        # Replace asyncio-mqtt with aiomqtt
        content = re.sub(
            r'asyncio[-_]mqtt[>=<\d\.,]*.*$',
            'aiomqtt==2.4.0  # Phase 2 upgrade - MIGRATION from asyncio-mqtt (package renamed)',
            content,
            flags=re.MULTILINE
        )

        # Check if paho-mqtt already exists
        has_paho = bool(re.search(r'paho[-_]mqtt', content))

        if not has_paho:
            # Add paho-mqtt after aiomqtt line
            content = re.sub(
                r'(aiomqtt==2\.4\.0.*\n)',
                r'\1paho-mqtt==2.1.0  # Phase 2 upgrade - required by aiomqtt\n',
                content
            )
            self.changes.append("requirements.txt: Added paho-mqtt==2.1.0 (required by aiomqtt)")

        self.changes.append("requirements.txt: Updated asyncio-mqtt -> aiomqtt==2.4.0")
        logger.info("  [OK] Updated MQTT libraries")

        if not self.dry_run:
            requirements_file.write_text(content, encoding='utf-8')

        return True

    def _run_tests(self) -> bool:
        """Run pytest to validate migration"""
        logger.info("Running tests to validate migration...")

        tests_dir = self.service_path / "tests"
        if not tests_dir.exists():
            logger.warning("No tests directory - skipping test validation")
            return True

        try:
            result = subprocess.run(
                ['pytest', 'tests/', '-v', '--tb=short'],
                cwd=self.service_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info("  [OK] All tests passed")
                return True
            else:
                logger.error("  [ERROR] Tests failed")
                logger.error(result.stdout)
                logger.error(result.stderr)
                self.errors.append("Tests failed after migration")
                return False

        except subprocess.TimeoutExpired:
            logger.error("  [ERROR] Tests timed out")
            self.errors.append("Tests timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"  [ERROR] Failed to run tests: {e}")
            self.errors.append(f"Failed to run tests: {e}")
            return False

    def _create_rollback_script(self) -> None:
        """Create rollback script to revert changes"""
        if not self.backup_dir:
            logger.warning("No backup dir - cannot create rollback script")
            return

        rollback_script = self.service_path / f"rollback_mqtt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"

        script_content = f"""#!/bin/bash
# Rollback script for MQTT migration
# Service: {self.service_path.name}
# Created: {datetime.now().isoformat()}

set -e

SERVICE_DIR="{self.service_path}"
BACKUP_DIR="{self.backup_dir}"

echo "Rolling back MQTT migration for {self.service_path.name}..."

# Restore requirements.txt
if [ -f "$BACKUP_DIR/requirements.txt" ]; then
    cp "$BACKUP_DIR/requirements.txt" "$SERVICE_DIR/requirements.txt"
    echo "[OK] Restored requirements.txt"
fi

# Restore src directory
if [ -d "$BACKUP_DIR/src" ]; then
    rm -rf "$SERVICE_DIR/src"
    cp -r "$BACKUP_DIR/src" "$SERVICE_DIR/src"
    echo "[OK] Restored src directory"
fi

echo "[OK] Rollback complete"
echo "Run 'docker-compose build {self.service_path.name}' to rebuild with old versions"
"""

        if not self.dry_run:
            rollback_script.write_text(script_content, encoding='utf-8')
            rollback_script.chmod(0o755)
            logger.info(f"[OK] Created rollback script: {rollback_script.name}")

    def _print_summary(self) -> None:
        """Print migration summary"""
        # Use simple ASCII for Windows console compatibility
        print("\n" + "="*60)
        print(f"MQTT Migration Summary: {self.service_path.name}")
        print("="*60)

        if self.dry_run:
            print("[DRY RUN] - No changes made")

        print(f"\nChanges ({len(self.changes)}):")
        for change in self.changes:
            print(f"  [OK] {change}")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  [WARNING] {warning}")

        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  [ERROR] {error}")

        if self.backup_dir and not self.dry_run:
            print(f"\nBackup: {self.backup_dir}")

        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate service from asyncio-mqtt to aiomqtt 2.4.0'
    )
    parser.add_argument(
        'service',
        help='Service name or path (e.g., websocket-ingestion or services/websocket-ingestion)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )
    parser.add_argument(
        '--batch',
        nargs='+',
        help='Migrate multiple services (space-separated)'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test validation after migration'
    )

    args = parser.parse_args()

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Determine services to migrate
    if args.batch:
        services = args.batch
    else:
        services = [args.service]

    # Migrate each service
    results = []
    for service in services:
        # Resolve service path
        if '/' in service or '\\' in service:
            service_path = Path(service)
        else:
            service_path = project_root / 'services' / service

        # Migrate
        migrator = MQTTMigrator(service_path, dry_run=args.dry_run, skip_tests=args.skip_tests)
        success = migrator.migrate()
        results.append((service, success))

    # Print batch summary
    if len(services) > 1:
        print("\n" + "="*60)
        print("Batch Migration Summary")
        print("="*60)
        for service, success in results:
            status = "[SUCCESS]" if success else "[FAILED]"
            print(f"  {status}: {service}")
        print("="*60)

    # Exit with error if any failed
    if not all(success for _, success in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
