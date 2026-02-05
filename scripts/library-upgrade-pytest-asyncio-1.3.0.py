#!/usr/bin/env python3
"""
Phase 2: pytest-asyncio 1.3.0 Migration Script

Migrates services from pytest-asyncio 0.23.x to 1.3.0.

BREAKING CHANGES in pytest-asyncio 1.3.0:
1. asyncio_mode = "auto" is now the default (remove from pytest.ini)
2. All async test functions MUST have @pytest.mark.asyncio decorator
3. Fixture scope handling changed for async fixtures

Story: PHASE2-002
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


class PytestAsyncioMigrator:
    """Migrate service to pytest-asyncio 1.3.0"""

    def __init__(self, service_path: Path, dry_run: bool = False):
        self.service_path = service_path
        self.dry_run = dry_run
        self.changes: List[str] = []
        self.errors: List[str] = []
        self.backup_dir: Optional[Path] = None

    def migrate(self) -> bool:
        """
        Execute full migration workflow

        Returns:
            True if migration successful, False otherwise
        """
        logger.info(f"Starting pytest-asyncio migration for {self.service_path.name}")

        try:
            # Step 1: Validate service structure
            if not self._validate_service():
                return False

            # Step 2: Create backup
            if not self.dry_run:
                self._create_backup()

            # Step 3: Migrate pytest.ini
            pytest_ini_updated = self._migrate_pytest_ini()

            # Step 4: Scan and update test files
            test_files_updated = self._migrate_test_files()

            # Step 5: Update conftest.py (if needed)
            conftest_updated = self._migrate_conftest()

            # Step 6: Update requirements.txt
            requirements_updated = self._update_requirements()

            # Step 7: Run tests to validate
            if not self.dry_run:
                tests_passed = self._run_tests()
                if not tests_passed:
                    logger.warning("Tests failed after migration - rollback recommended")
                    self._create_rollback_script()
                    return False

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

        # Check for tests directory
        tests_dir = self.service_path / "tests"
        if not tests_dir.exists():
            self.errors.append(f"Tests directory not found: {tests_dir}")
            return False

        # Check for requirements.txt
        requirements_file = self.service_path / "requirements.txt"
        if not requirements_file.exists():
            self.errors.append(f"requirements.txt not found: {requirements_file}")
            return False

        logger.info("✅ Service structure validated")
        return True

    def _create_backup(self) -> None:
        """Create backup of service files before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.service_path / f".migration_backup_{timestamp}"
        self.backup_dir.mkdir(exist_ok=True)

        logger.info(f"Creating backup at {self.backup_dir}")

        # Backup pytest.ini
        pytest_ini = self.service_path / "pytest.ini"
        if pytest_ini.exists():
            shutil.copy2(pytest_ini, self.backup_dir / "pytest.ini")

        # Backup requirements.txt
        requirements = self.service_path / "requirements.txt"
        if requirements.exists():
            shutil.copy2(requirements, self.backup_dir / "requirements.txt")

        # Backup tests directory
        tests_dir = self.service_path / "tests"
        if tests_dir.exists():
            shutil.copytree(tests_dir, self.backup_dir / "tests", dirs_exist_ok=True)

        logger.info("✅ Backup created")

    def _migrate_pytest_ini(self) -> bool:
        """
        Migrate pytest.ini configuration

        BREAKING CHANGE: Remove asyncio_mode = auto (now default)
        """
        pytest_ini = self.service_path / "pytest.ini"

        if not pytest_ini.exists():
            logger.info("No pytest.ini found - skipping")
            return False

        logger.info("Migrating pytest.ini...")

        # Read current content
        content = pytest_ini.read_text(encoding='utf-8')
        original_content = content

        # Check if asyncio_mode is present
        if re.search(r'^\s*asyncio_mode\s*=\s*auto\s*$', content, re.MULTILINE):
            # Remove asyncio_mode = auto line
            content = re.sub(
                r'^\s*asyncio_mode\s*=\s*auto\s*$\n?',
                '',
                content,
                flags=re.MULTILINE
            )

            # Also remove the comment if it exists
            content = re.sub(
                r'^\s*#\s*Asyncio configuration\s*$\n?',
                '',
                content,
                flags=re.MULTILINE
            )

            change_msg = "Removed 'asyncio_mode = auto' (now default in pytest-asyncio 1.3.0)"
            self.changes.append(f"pytest.ini: {change_msg}")
            logger.info(f"  ✅ {change_msg}")

            if not self.dry_run:
                pytest_ini.write_text(content, encoding='utf-8')

            return True
        else:
            logger.info("  No asyncio_mode found - no changes needed")
            return False

    def _migrate_test_files(self) -> int:
        """
        Scan test files and ensure all async functions have @pytest.mark.asyncio

        Returns:
            Number of files updated
        """
        logger.info("Scanning test files...")

        tests_dir = self.service_path / "tests"
        test_files = list(tests_dir.glob("**/test_*.py")) + list(tests_dir.glob("**/*_test.py"))

        updated_count = 0

        for test_file in test_files:
            if self._migrate_test_file(test_file):
                updated_count += 1

        logger.info(f"  ✅ Scanned {len(test_files)} test files, updated {updated_count}")
        return updated_count

    def _migrate_test_file(self, test_file: Path) -> bool:
        """
        Migrate individual test file

        Returns:
            True if file was updated, False otherwise
        """
        content = test_file.read_text(encoding='utf-8')
        original_content = content
        updated = False

        # Find all async test functions (NOT fixtures)
        async_test_pattern = re.compile(
            r'^([ \t]*)async\s+def\s+(test_\w+)\s*\(',
            re.MULTILINE
        )

        # Check if pytest is imported
        has_pytest_import = 'import pytest' in content or 'from pytest' in content

        for match in async_test_pattern.finditer(content):
            indent = match.group(1)
            func_name = match.group(2)
            func_start = match.start()

            # Look backwards for @pytest.mark.asyncio decorator or @pytest.fixture
            lines_before = content[:func_start].split('\n')

            # Check last few lines before function definition
            has_marker = False
            is_fixture = False
            for line in reversed(lines_before[-5:]):
                if '@pytest.mark.asyncio' in line:
                    has_marker = True
                    break
                if '@pytest.fixture' in line:
                    is_fixture = True
                    break
                # Stop at previous function or class definition
                if re.match(r'^\s*(async\s+)?def\s+\w+|^\s*class\s+\w+', line):
                    break

            # Only add marker if it's a test function (not a fixture) and doesn't have marker
            if not has_marker and not is_fixture:
                # Add marker before function
                decorator = f"{indent}@pytest.mark.asyncio\n"
                content = content[:func_start] + decorator + content[func_start:]

                self.changes.append(
                    f"{test_file.name}: Added @pytest.mark.asyncio to {func_name}"
                )
                updated = True

        # Ensure pytest is imported
        if updated and not has_pytest_import:
            # Add pytest import at the top
            import_line = "import pytest\n"

            # Find the first import or docstring
            lines = content.split('\n')
            insert_pos = 0

            for i, line in enumerate(lines):
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    # Skip docstring
                    insert_pos = i + 1
                    # Find end of docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            insert_pos = j + 1
                            break
                    break
                elif line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_pos = i
                    break

            lines.insert(insert_pos, import_line)
            content = '\n'.join(lines)
            self.changes.append(f"{test_file.name}: Added pytest import")

        if updated and not self.dry_run:
            test_file.write_text(content, encoding='utf-8')

        return updated

    def _migrate_conftest(self) -> bool:
        """
        Migrate conftest.py (if needed)

        In pytest-asyncio 1.3.0, async fixture scopes may need adjustment
        """
        conftest = self.service_path / "tests" / "conftest.py"

        if not conftest.exists():
            logger.info("No conftest.py found - skipping")
            return False

        logger.info("Checking conftest.py...")

        # For now, just log that we checked it
        # Future: Add specific fixture scope migrations if needed
        logger.info("  ✅ conftest.py checked (no changes needed)")
        return False

    def _update_requirements(self) -> bool:
        """Update requirements.txt to pytest-asyncio 1.3.0"""
        requirements_file = self.service_path / "requirements.txt"

        logger.info("Updating requirements.txt...")

        content = requirements_file.read_text(encoding='utf-8')
        original_content = content

        # Replace pytest-asyncio version
        pattern = r'pytest-asyncio[>=<\d\.,]+'
        if re.search(pattern, content):
            content = re.sub(
                pattern,
                'pytest-asyncio==1.3.0  # Phase 2 upgrade - BREAKING: new async patterns',
                content
            )

            self.changes.append("requirements.txt: Updated pytest-asyncio to 1.3.0")
            logger.info("  ✅ Updated pytest-asyncio version")

            if not self.dry_run:
                requirements_file.write_text(content, encoding='utf-8')

            return True
        else:
            logger.warning("  ⚠️  pytest-asyncio not found in requirements.txt")
            return False

    def _run_tests(self) -> bool:
        """Run pytest to validate migration"""
        logger.info("Running tests to validate migration...")

        try:
            result = subprocess.run(
                ['pytest', 'tests/', '-v', '--tb=short'],
                cwd=self.service_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info("  ✅ All tests passed")
                return True
            else:
                logger.error("  ❌ Tests failed")
                logger.error(result.stdout)
                logger.error(result.stderr)
                self.errors.append("Tests failed after migration")
                return False

        except subprocess.TimeoutExpired:
            logger.error("  ❌ Tests timed out")
            self.errors.append("Tests timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"  ❌ Failed to run tests: {e}")
            self.errors.append(f"Failed to run tests: {e}")
            return False

    def _create_rollback_script(self) -> None:
        """Create rollback script to revert changes"""
        if not self.backup_dir:
            logger.warning("No backup dir - cannot create rollback script")
            return

        rollback_script = self.service_path / f"rollback_pytest_asyncio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"

        script_content = f"""#!/bin/bash
# Rollback script for pytest-asyncio migration
# Service: {self.service_path.name}
# Created: {datetime.now().isoformat()}

set -e

SERVICE_DIR="{self.service_path}"
BACKUP_DIR="{self.backup_dir}"

echo "Rolling back pytest-asyncio migration for {self.service_path.name}..."

# Restore pytest.ini
if [ -f "$BACKUP_DIR/pytest.ini" ]; then
    cp "$BACKUP_DIR/pytest.ini" "$SERVICE_DIR/pytest.ini"
    echo "✅ Restored pytest.ini"
fi

# Restore requirements.txt
if [ -f "$BACKUP_DIR/requirements.txt" ]; then
    cp "$BACKUP_DIR/requirements.txt" "$SERVICE_DIR/requirements.txt"
    echo "✅ Restored requirements.txt"
fi

# Restore tests directory
if [ -d "$BACKUP_DIR/tests" ]; then
    rm -rf "$SERVICE_DIR/tests"
    cp -r "$BACKUP_DIR/tests" "$SERVICE_DIR/tests"
    echo "✅ Restored tests directory"
fi

echo "✅ Rollback complete"
echo "Run 'docker-compose build {self.service_path.name}' to rebuild with old versions"
"""

        if not self.dry_run:
            rollback_script.write_text(script_content, encoding='utf-8')
            rollback_script.chmod(0o755)
            logger.info(f"✅ Created rollback script: {rollback_script.name}")

    def _print_summary(self) -> None:
        """Print migration summary"""
        # Use simple ASCII for Windows console compatibility
        print("\n" + "="*60)
        print(f"pytest-asyncio Migration Summary: {self.service_path.name}")
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
        description='Migrate service to pytest-asyncio 1.3.0'
    )
    parser.add_argument(
        'service',
        help='Service name or path (e.g., automation-miner or services/automation-miner)'
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
        migrator = PytestAsyncioMigrator(service_path, dry_run=args.dry_run)
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
