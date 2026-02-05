#!/usr/bin/env python3
"""
Phase 2: influxdb3-python 0.17.0 Migration Script

Migrates services from influxdb-client to influxdb3-python.

BREAKING CHANGES:
1. Complete API redesign (influxdb-client -> influxdb3-python)
2. Package renamed: influxdb_client -> influxdb_client_3
3. Client initialization changed: Different constructor parameters
4. Write API changed: New write() interface
5. Query API changed: New query() interface with pandas support
6. Requires pandas for [pandas] extra

Story: PHASE2-005
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


class InfluxDBMigrator:
    """Migrate service from influxdb-client to influxdb3-python 0.17.0"""

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
        logger.info(f"Starting influxdb-client to influxdb3-python migration for {self.service_path.name}")

        try:
            # Step 1: Validate service structure
            if not self._validate_service():
                return False

            # Step 2: Check if migration needed
            if not self._needs_migration():
                logger.info("Service already has influxdb3-python - no migration needed")
                return True

            # Step 3: Create backup
            if not self.dry_run:
                self._create_backup()

            # Step 4: Find InfluxDB code usage
            influxdb_files = self._find_influxdb_usage()
            if influxdb_files:
                logger.warning(f"Found {len(influxdb_files)} files using InfluxDB - manual code review required")
                self.warnings.append(
                    f"Found InfluxDB usage in {len(influxdb_files)} files - API redesign requires manual code migration"
                )
                self.warnings.append(
                    "See migration guide for API changes: Client initialization, write(), query()"
                )

            # Step 5: Migrate imports (basic replacement)
            if influxdb_files:
                self._migrate_influxdb_imports(influxdb_files)

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
        """Check if service needs InfluxDB migration"""
        requirements_file = self.service_path / "requirements.txt"
        content = requirements_file.read_text(encoding='utf-8')

        # Check if already has influxdb3-python
        if re.search(r'influxdb3-python', content):
            return False

        # Check if has influxdb-client
        if not re.search(r'influxdb[-_]client', content):
            logger.warning("Service does not use influxdb-client - skipping")
            return False

        return True

    def _create_backup(self) -> None:
        """Create backup of service files before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.service_path / f".migration_backup_influxdb_{timestamp}"
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

    def _find_influxdb_usage(self) -> List[Path]:
        """
        Find all Python files using influxdb-client

        Returns:
            List of file paths using InfluxDB
        """
        logger.info("Finding InfluxDB usage...")

        src_dir = self.service_path / "src"
        if not src_dir.exists():
            logger.info("No src directory - skipping InfluxDB code check")
            return []

        influxdb_files = []

        # Find all Python files with InfluxDB imports or usage
        for py_file in src_dir.glob("**/*.py"):
            content = py_file.read_text(encoding='utf-8')

            # Check for influxdb-client imports
            if any(pattern in content for pattern in [
                'import influxdb_client',
                'from influxdb_client',
                'influxdb_client.',
                'InfluxDBClient(',
                'Point(',
                'WritePrecision',
            ]):
                influxdb_files.append(py_file)

        logger.info(f"[OK] Found {len(influxdb_files)} files using InfluxDB")
        return influxdb_files

    def _migrate_influxdb_imports(self, influxdb_files: List[Path]) -> None:
        """
        Migrate InfluxDB imports (basic replacement only)

        BREAKING CHANGES:
        1. import influxdb_client -> import influxdb_client_3
        2. from influxdb_client import -> from influxdb_client_3 import

        WARNING: This only migrates imports. API changes require manual migration:
        - Client initialization changed
        - write() API changed
        - query() API changed
        """
        logger.info("Migrating InfluxDB imports...")
        logger.warning("WARNING: API changes require manual code migration after import update")

        for py_file in influxdb_files:
            updated = self._migrate_influxdb_file(py_file)
            if updated:
                self.changes.append(f"{py_file.relative_to(self.service_path)}: Updated InfluxDB imports")

    def _migrate_influxdb_file(self, py_file: Path) -> bool:
        """
        Migrate InfluxDB imports in a single file

        Returns:
            True if file was updated, False otherwise
        """
        content = py_file.read_text(encoding='utf-8')
        original_content = content
        updated = False

        # Replace import statements
        # import influxdb_client -> import influxdb_client_3
        if 'import influxdb_client' in content and 'import influxdb_client_3' not in content:
            content = content.replace('import influxdb_client', 'import influxdb_client_3')
            updated = True
            logger.info(f"  [OK] Updated 'import influxdb_client' -> 'import influxdb_client_3' in {py_file.name}")

        # from influxdb_client import -> from influxdb_client_3 import
        if 'from influxdb_client' in content:
            content = re.sub(
                r'from influxdb_client\b',
                'from influxdb_client_3',
                content
            )
            updated = True
            logger.info(f"  [OK] Updated 'from influxdb_client' -> 'from influxdb_client_3' in {py_file.name}")

        # influxdb_client. -> influxdb_client_3.
        if 'influxdb_client.' in content:
            content = content.replace('influxdb_client.', 'influxdb_client_3.')
            updated = True
            logger.info(f"  [OK] Updated 'influxdb_client.' -> 'influxdb_client_3.' in {py_file.name}")

        if updated:
            logger.warning(f"  [WARNING] {py_file.name}: Manual code changes required for API redesign")
            logger.warning(f"    - Client initialization API changed")
            logger.warning(f"    - write() API changed")
            logger.warning(f"    - query() API changed")

        if updated and not self.dry_run:
            py_file.write_text(content, encoding='utf-8')

        return updated

    def _update_requirements(self) -> bool:
        """Update requirements.txt to influxdb3-python 0.17.0"""
        requirements_file = self.service_path / "requirements.txt"

        logger.info("Updating requirements.txt...")

        content = requirements_file.read_text(encoding='utf-8')
        original_content = content

        # Check if influxdb-client exists
        if not re.search(r'influxdb[-_]client', content):
            logger.warning("  [WARNING] influxdb-client not found in requirements.txt")
            return False

        # Replace influxdb-client with influxdb3-python
        content = re.sub(
            r'influxdb[-_]client[>=<\d\.,]*.*$',
            'influxdb3-python[pandas]==0.17.0  # Phase 2 upgrade - BREAKING: API redesign',
            content,
            flags=re.MULTILINE
        )

        self.changes.append("requirements.txt: Updated influxdb-client -> influxdb3-python[pandas]==0.17.0")
        logger.info("  [OK] Updated InfluxDB library")

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

        rollback_script = self.service_path / f"rollback_influxdb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"

        script_content = f"""#!/bin/bash
# Rollback script for InfluxDB migration
# Service: {self.service_path.name}
# Created: {datetime.now().isoformat()}

set -e

SERVICE_DIR="{self.service_path}"
BACKUP_DIR="{self.backup_dir}"

echo "Rolling back InfluxDB migration for {self.service_path.name}..."

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
        print(f"InfluxDB Migration Summary: {self.service_path.name}")
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

        print("\n" + "="*60)
        print("MANUAL CODE MIGRATION REQUIRED")
        print("="*60)
        print("influxdb3-python has a completely redesigned API.")
        print("After running this script, manually update your code:")
        print("")
        print("1. Client initialization:")
        print("   OLD: InfluxDBClient(url=..., token=..., org=...)")
        print("   NEW: InfluxDBClient3(host=..., token=..., database=...)")
        print("")
        print("2. Write API:")
        print("   OLD: write_api.write(bucket=..., record=...)")
        print("   NEW: client.write(record=...)")
        print("")
        print("3. Query API:")
        print("   OLD: query_api.query(query=...)")
        print("   NEW: client.query(query=...) # Returns pandas DataFrame")
        print("")
        print("See: docs/planning/phase2-influxdb-migration-guide.md")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate service from influxdb-client to influxdb3-python 0.17.0'
    )
    parser.add_argument(
        'service',
        help='Service name or path (e.g., data-api or services/data-api)'
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
        migrator = InfluxDBMigrator(service_path, dry_run=args.dry_run, skip_tests=args.skip_tests)
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
