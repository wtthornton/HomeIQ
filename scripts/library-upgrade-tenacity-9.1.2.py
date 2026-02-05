#!/usr/bin/env python3
"""
Phase 2: tenacity 9.1.2 Migration Script

Migrates services from tenacity 8.x to 9.1.2.

BREAKING CHANGES in tenacity 9.0+:
1. reraise parameter default changed from True to False
2. Some wait strategy parameter updates
3. Better typing support (non-breaking)

Story: PHASE2-003
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


class TenacityMigrator:
    """Migrate service to tenacity 9.1.2"""

    def __init__(self, service_path: Path, dry_run: bool = False, skip_tests: bool = False):
        self.service_path = service_path
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.changes: List[str] = []
        self.errors: List[str] = []
        self.backup_dir: Optional[Path] = None

    def migrate(self) -> bool:
        """
        Execute full migration workflow

        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Starting tenacity migration for {self.service_path.name}")

        try:
            # Step 1: Validate service structure
            if not self._validate_service():
                return False

            # Step 2: Check if migration needed
            if not self._needs_migration():
                logger.info("Service already has tenacity 9.1.2 - no migration needed")
                return True

            # Step 3: Create backup
            if not self.dry_run:
                self._create_backup()

            # Step 4: Find retry decorators
            retry_files = self._find_retry_usage()

            # Step 5: Migrate retry decorators
            if retry_files:
                self._migrate_retry_decorators(retry_files)

            # Step 6: Update requirements.txt
            requirements_updated = self._update_requirements()

            # Step 7: Run tests to validate (unless skipped)
            if not self.dry_run and not self.skip_tests and (retry_files or requirements_updated):
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
        """Check if service needs tenacity migration"""
        requirements_file = self.service_path / "requirements.txt"
        content = requirements_file.read_text(encoding='utf-8')

        # Check if already has tenacity 9.1.2
        if re.search(r'tenacity\s*==\s*9\.1\.2', content):
            return False

        # Check if has tenacity at all
        if not re.search(r'tenacity', content):
            logger.warning("Service does not use tenacity - skipping")
            return False

        return True

    def _create_backup(self) -> None:
        """Create backup of service files before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.service_path / f".migration_backup_tenacity_{timestamp}"
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

    def _find_retry_usage(self) -> List[Path]:
        """
        Find all Python files using @retry decorator

        Returns:
            List of file paths using tenacity retry
        """
        logger.info("Finding tenacity usage...")

        src_dir = self.service_path / "src"
        if not src_dir.exists():
            logger.info("No src directory - skipping retry pattern check")
            return []

        retry_files = []

        # Find all Python files with @retry decorator
        for py_file in src_dir.glob("**/*.py"):
            content = py_file.read_text(encoding='utf-8')

            if '@retry' in content or 'from tenacity import' in content or 'import tenacity' in content:
                retry_files.append(py_file)

        logger.info(f"[OK] Found {len(retry_files)} files using tenacity")
        return retry_files

    def _migrate_retry_decorators(self, retry_files: List[Path]) -> None:
        """
        Migrate @retry decorators to be compatible with tenacity 9.x

        BREAKING CHANGE: reraise parameter default changed from True to False
        """
        logger.info("Migrating retry decorators...")

        for py_file in retry_files:
            updated = self._migrate_retry_file(py_file)
            if updated:
                self.changes.append(f"{py_file.relative_to(self.service_path)}: Updated retry decorators")

    def _migrate_retry_file(self, py_file: Path) -> bool:
        """
        Migrate retry decorators in a single file

        Returns:
            True if file was updated, False otherwise
        """
        content = py_file.read_text(encoding='utf-8')
        original_content = content
        updated = False

        # Find @retry decorators
        # Pattern: @retry(...) - multiline
        retry_pattern = re.compile(
            r'@retry\s*\(((?:[^()]|\([^()]*\))*)\)',
            re.MULTILINE | re.DOTALL
        )

        for match in retry_pattern.finditer(content):
            decorator_args = match.group(1)

            # Check if reraise is explicitly set
            if 'reraise' not in decorator_args:
                # Add reraise=True to maintain tenacity 8.x behavior
                # Insert before closing paren
                new_args = decorator_args.rstrip()

                # Add comma if there are existing args
                if new_args and not new_args.endswith(','):
                    new_args += ','

                new_args += '\n        reraise=True'

                new_decorator = f'@retry({new_args}\n    )'

                # Replace in content
                content = content.replace(match.group(0), new_decorator)

                updated = True
                logger.info(f"  [OK] Added reraise=True to {py_file.name}")

        if updated and not self.dry_run:
            py_file.write_text(content, encoding='utf-8')

        return updated

    def _update_requirements(self) -> bool:
        """Update requirements.txt to tenacity 9.1.2"""
        requirements_file = self.service_path / "requirements.txt"

        logger.info("Updating requirements.txt...")

        content = requirements_file.read_text(encoding='utf-8')
        original_content = content

        # Replace tenacity version
        pattern = r'tenacity[>=<\d\.,]+'
        if re.search(pattern, content):
            content = re.sub(
                pattern,
                'tenacity==9.1.2  # Phase 2 upgrade - MAJOR version',
                content
            )

            self.changes.append("requirements.txt: Updated tenacity to 9.1.2")
            logger.info("  [OK] Updated tenacity version")

            if not self.dry_run:
                requirements_file.write_text(content, encoding='utf-8')

            return True
        else:
            logger.warning("  [WARNING] tenacity not found in requirements.txt")
            return False

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

        rollback_script = self.service_path / f"rollback_tenacity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"

        script_content = f"""#!/bin/bash
# Rollback script for tenacity migration
# Service: {self.service_path.name}
# Created: {datetime.now().isoformat()}

set -e

SERVICE_DIR="{self.service_path}"
BACKUP_DIR="{self.backup_dir}"

echo "Rolling back tenacity migration for {self.service_path.name}..."

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
        print("\n" + "="*60)
        print(f"tenacity Migration Summary: {self.service_path.name}")
        print("="*60)

        if self.dry_run:
            print("[DRY RUN] - No changes made")

        print(f"\nChanges ({len(self.changes)}):")
        for change in self.changes:
            print(f"  [OK] {change}")

        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  [ERROR] {error}")

        if self.backup_dir and not self.dry_run:
            print(f"\nBackup: {self.backup_dir}")

        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate service to tenacity 9.1.2'
    )
    parser.add_argument(
        'service',
        help='Service name or path (e.g., api-automation-edge or services/api-automation-edge)'
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
        migrator = TenacityMigrator(service_path, dry_run=args.dry_run, skip_tests=args.skip_tests)
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
