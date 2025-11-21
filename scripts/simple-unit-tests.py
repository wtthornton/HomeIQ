#!/usr/bin/env python3
"""
Simple Unit Test Runner for HomeIQ
Provides clear visual progress and runs unit tests with coverage

Usage:
    python scripts/simple-unit-tests.py
    python scripts/simple-unit-tests.py --python-only
    python scripts/simple-unit-tests.py --typescript-only
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class SimpleUnitTestRunner:
    """Simple unit test runner with visual progress"""

    def __init__(self):
        self.project_root = project_root
        self.results = {
            "python": {"passed": 0, "failed": 0, "total": 0},
            "typescript": {"passed": 0, "failed": 0, "total": 0},
            "start_time": datetime.now(),
            "duration": 0,
        }

        # Create results directory
        self.results_dir = self.project_root / "test-results"
        self.results_dir.mkdir(exist_ok=True)
        (self.results_dir / "coverage" / "python").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "coverage" / "typescript").mkdir(parents=True, exist_ok=True)

    def print_header(self):
        """Print header with visual indicators"""
        print("=" * 80)
        print("HomeIQ Unit Testing Framework")
        print("=" * 80)
        print(f"Started: {self.results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Results: {self.results_dir}")
        print("=" * 80)

    def print_progress(self, message, status="INFO"):
        """Print progress message with visual indicator"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if status == "SUCCESS":
            print(f"[PASS] [{timestamp}] {message}")
        elif status == "ERROR":
            print(f"[FAIL] [{timestamp}] {message}")
        elif status == "WARNING":
            print(f"[WARN] [{timestamp}] {message}")
        else:
            print(f"[INFO] [{timestamp}] {message}")

    def run_python_tests(self):
        """Run Python unit tests"""
        self.print_progress("Starting Python unit tests...")

        # Use the updated pytest configuration
        cmd = [
            "python", "-m", "pytest", "-c", "pytest-unit.ini",
            "--verbose",
            "--tb=short",
            "--cov-report=html:test-results/coverage/python",
            "--cov-report=xml:test-results/coverage/python/coverage.xml",
            "--cov-report=term-missing",
            "--disable-warnings",
            "--maxfail=10",
        ]

        try:
            self.print_progress(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=False, cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            # Parse results
            if result.returncode == 0:
                self.print_progress("Python tests completed successfully", "SUCCESS")
                # Extract test counts from output
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line and "failed" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "passed":
                                self.results["python"]["passed"] = int(parts[i-1])
                            elif part == "failed":
                                self.results["python"]["failed"] = int(parts[i-1])
                        break
            else:
                self.print_progress("Python tests had failures", "WARNING")
                self.results["python"]["failed"] = 1

            self.results["python"]["total"] = self.results["python"]["passed"] + self.results["python"]["failed"]

        except subprocess.TimeoutExpired:
            self.print_progress("Python tests timed out after 10 minutes", "ERROR")
            self.results["python"]["failed"] = 1
            self.results["python"]["total"] = 1
        except Exception as e:
            self.print_progress(f"Error running Python tests: {e!s}", "ERROR")
            self.results["python"]["failed"] = 1
            self.results["python"]["total"] = 1

    def run_typescript_tests(self):
        """Run TypeScript unit tests"""
        self.print_progress("Starting TypeScript unit tests...")

        health_dashboard_dir = self.project_root / "services" / "health-dashboard"
        if not health_dashboard_dir.exists():
            self.print_progress("Health dashboard not found, skipping TypeScript tests", "WARNING")
            return

        # Check if package.json exists
        if not (health_dashboard_dir / "package.json").exists():
            self.print_progress("package.json not found, skipping TypeScript tests", "WARNING")
            return

        cmd = [
            "npx", "vitest", "run",
            "--config", "vitest-unit.config.ts",
            "--coverage",
            "--reporter=verbose",
        ]

        try:
            self.print_progress(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=False, cwd=health_dashboard_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                self.print_progress("TypeScript tests completed successfully", "SUCCESS")
                # Parse results
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line and "failed" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "passed":
                                self.results["typescript"]["passed"] = int(parts[i-1])
                            elif part == "failed":
                                self.results["typescript"]["failed"] = int(parts[i-1])
                        break
            else:
                self.print_progress("TypeScript tests had failures", "WARNING")
                self.results["typescript"]["failed"] = 1

            self.results["typescript"]["total"] = self.results["typescript"]["passed"] + self.results["typescript"]["failed"]

        except subprocess.TimeoutExpired:
            self.print_progress("TypeScript tests timed out after 5 minutes", "ERROR")
            self.results["typescript"]["failed"] = 1
            self.results["typescript"]["total"] = 1
        except Exception as e:
            self.print_progress(f"Error running TypeScript tests: {e!s}", "ERROR")
            self.results["typescript"]["failed"] = 1
            self.results["typescript"]["total"] = 1

    def print_summary(self):
        """Print final summary with visual indicators"""
        self.results["duration"] = (datetime.now() - self.results["start_time"]).total_seconds()

        print("\n" + "=" * 80)
        print("UNIT TEST SUMMARY")
        print("=" * 80)

        # Python results
        python_total = self.results["python"]["total"]
        python_passed = self.results["python"]["passed"]
        python_failed = self.results["python"]["failed"]

        if python_total > 0:
            python_rate = (python_passed / python_total) * 100
            status_icon = "[PASS]" if python_failed == 0 else "[WARN]"
            print(f"{status_icon} Python Tests: {python_passed}/{python_total} passed ({python_rate:.1f}%)")

        # TypeScript results
        ts_total = self.results["typescript"]["total"]
        ts_passed = self.results["typescript"]["passed"]
        ts_failed = self.results["typescript"]["failed"]

        if ts_total > 0:
            ts_rate = (ts_passed / ts_total) * 100
            status_icon = "[PASS]" if ts_failed == 0 else "[WARN]"
            print(f"{status_icon} TypeScript Tests: {ts_passed}/{ts_total} passed ({ts_rate:.1f}%)")

        # Overall results
        total_tests = python_total + ts_total
        total_passed = python_passed + ts_passed
        total_failed = python_failed + ts_failed

        if total_tests > 0:
            overall_rate = (total_passed / total_tests) * 100
            if total_failed == 0:
                print(f"[PASS] Overall: {total_passed}/{total_tests} passed ({overall_rate:.1f}%)")
                print("[PASS] All unit tests passed!")
            else:
                print(f"[WARN] Overall: {total_passed}/{total_tests} passed ({overall_rate:.1f}%)")
                print(f"[WARN] {total_failed} test(s) failed")

        print(f"Duration: {self.results['duration']:.1f} seconds")
        print("=" * 80)

        # Coverage reports
        print("Coverage Reports:")
        print("   Python: test-results/coverage/python/index.html")
        print("   TypeScript: test-results/coverage/typescript/index.html")
        print("=" * 80)

        return total_failed == 0

    def run_all_tests(self, python_only=False, typescript_only=False):
        """Run all unit tests"""
        self.print_header()

        # Run Python tests
        if not typescript_only:
            self.run_python_tests()

        # Run TypeScript tests
        if not python_only:
            self.run_typescript_tests()

        # Print summary
        success = self.print_summary()

        return 0 if success else 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Simple HomeIQ Unit Test Runner")
    parser.add_argument("--python-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--typescript-only", action="store_true", help="Run only TypeScript tests")

    args = parser.parse_args()

    runner = SimpleUnitTestRunner()
    return runner.run_all_tests(
        python_only=args.python_only,
        typescript_only=args.typescript_only,
    )


if __name__ == "__main__":
    sys.exit(main())
