#!/usr/bin/env python3
"""
Unit Testing Framework for HomeIQ
Runs all unit tests and generates comprehensive coverage reports

This script identifies and runs ONLY unit tests (no external dependencies):
- Python unit tests using pytest with coverage
- TypeScript/React unit tests using Vitest with coverage
- Generates unified coverage reports
- Excludes integration tests, e2e tests, and visual tests

Usage:
    python scripts/run-unit-tests.py
    python scripts/run-unit-tests.py --verbose
    python scripts/run-unit-tests.py --coverage-only
    python scripts/run-unit-tests.py --python-only
    python scripts/run-unit-tests.py --typescript-only
"""

import argparse
import builtins
import contextlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class UnitTestFramework:
    """Main unit testing framework"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = project_root
        self.results = {
            "python": {"passed": 0, "failed": 0, "total": 0, "coverage": 0},
            "typescript": {"passed": 0, "failed": 0, "total": 0, "coverage": 0},
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_seconds": 0,
        }

        # Define unit test patterns (exclude integration/e2e/visual)
        self.python_unit_tests = [
            "services/ai-automation-service/tests/test_safety_validator.py",
            "services/ai-automation-service/tests/test_automation_parser.py",
            "services/ai-automation-service/tests/test_database_models.py",
            "services/ai-automation-service/tests/test_co_occurrence_detector.py",
            "services/ai-automation-service/tests/test_time_of_day_detector.py",
            "services/calendar-service/tests/test_event_parser.py",
            "services/weather-api/tests/test_health_check.py",
            "services/automation-miner/tests/test_parser.py",
            "services/automation-miner/tests/test_deduplicator.py",
            "services/data-api/tests/test_models.py",
            "services/sports-data/tests/test_stats_calculator.py",
        ]

        self.typescript_unit_tests = [
            "services/health-dashboard/src/__tests__/apiUsageCalculator.test.ts",
            "services/health-dashboard/src/__tests__/useTeamPreferences.test.ts",
            "services/health-dashboard/src/hooks/__tests__/useStatistics.test.ts",
        ]

        # Exclude patterns (integration, e2e, visual tests)
        self.exclude_patterns = [
            "integration", "e2e", "visual", "smoke", "deployment",
            "test_real_integration", "test_integration", "test_basic_setup",
            "test_multi_model_extraction", "test_integration_demo",
            "test_ask_ai_direct", "test_device_migration",
            "test_phase1_services", "test_nabu_casa_connection",
            "test_enhanced_integration", "test_device_intelligence_integration",
            "test_relationship_checker_integration", "test_enhanced_integration",
            "test_ha_client", "test_data_api_client", "test_openai_client",
            "test_mqtt_capability_listener", "test_weather_opportunities",
            "test_synergy_suggestion_generator", "test_relationship_analyzer",
            "test_device_pair_analyzer", "test_synergy_crud", "test_synergy_detector",
            "test_approval", "test_refinement", "test_suggestion_refiner",
            "test_description_generator", "test_nl_generator", "test_rollback",
            "test_feature_suggestion_generator", "test_feature_analyzer",
            "test_capability_parser", "test_daily_analysis_scheduler",
            "test_analysis_router", "test_miner_client", "test_enhancement_extractor",
            "test_ml_pattern_detectors", "test_unified_prompt_builder",
            "test_weather_service", "test_main", "test_openvino_service",
            "test_ml_service", "test_storage_api", "test_realtime_monitoring",
            "test_predictive_analytics", "test_health", "test_discovery_service",
            "test_fallback", "test_ai_core_service", "test_context_hierarchy",
            "test_webhook_sqlite", "test_database", "test_ha_endpoints",
            "test_webhook_manager", "test_event_detector", "test_historical_endpoints",
            "test_analytics_uptime", "test_stats_data_sources", "test_influxdb_client_simple",
            "test_utils_config", "test_utils_api_client", "test_pattern_aggregate_performance",
            "test_docker_compose", "test_preprocessing_pipeline", "test_complete_stack",
            "Dashboard.test.tsx", "Dashboard.interactions.test.tsx", "useHealth.test.ts",
            "ServiceDependencyGraph.test.tsx", "ServiceDetailsModal.test.tsx",
            "ServicesTab.test.tsx", "ServiceCard.test.tsx", "api.test.ts",
        ]

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level == "ERROR":
            # Handle Unicode characters for Windows compatibility
            try:
                print(f"[{timestamp}] {level}: {message}")
            except UnicodeEncodeError:
                # Fallback to ASCII-safe version
                safe_message = message.encode("ascii", "replace").decode("ascii")
                print(f"[{timestamp}] {level}: {safe_message}")

    def run_command(self, command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        """Run command and return exit code, stdout, stderr"""
        try:
            self.log(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                check=False, cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out after 5 minutes"
        except Exception as e:
            return 1, "", str(e)

    def filter_unit_tests(self, test_files: list[str]) -> list[str]:
        """Filter out integration/e2e/visual tests, keep only unit tests"""
        unit_tests = []

        for test_file in test_files:
            # Check if file should be excluded
            should_exclude = False
            for exclude_pattern in self.exclude_patterns:
                if exclude_pattern in test_file:
                    should_exclude = True
                    break

            if not should_exclude:
                unit_tests.append(test_file)
            else:
                self.log(f"Excluding integration/e2e test: {test_file}")

        return unit_tests

    def run_python_unit_tests(self) -> dict:
        """Run Python unit tests with coverage"""
        self.log("Starting Python unit tests...")

        # Find all Python test files
        python_tests = []
        for service_dir in (self.project_root / "services").iterdir():
            if service_dir.is_dir():
                tests_dir = service_dir / "tests"
                if tests_dir.exists():
                    for test_file in tests_dir.glob("test_*.py"):
                        python_tests.append(str(test_file.relative_to(self.project_root)))

        # Filter to unit tests only
        unit_tests = self.filter_unit_tests(python_tests)
        self.log(f"Found {len(unit_tests)} Python unit test files")

        if not unit_tests:
            self.log("No Python unit tests found")
            return {"passed": 0, "failed": 0, "total": 0, "coverage": 0}

        # Run tests with coverage
        coverage_dir = self.project_root / "test-results" / "coverage" / "python"
        coverage_dir.mkdir(parents=True, exist_ok=True)

        # Create pytest configuration for unit tests only
        pytest_config = f"""
[tool:pytest]
testpaths = {', '.join(unit_tests)}
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --tb=short
    --cov=src
    --cov-report=html:{coverage_dir}
    --cov-report=xml:{coverage_dir}/coverage.xml
    --cov-report=term-missing
    --cov-fail-under=70
    --maxfail=5
    --disable-warnings
markers =
    unit: Unit tests only
    integration: Integration tests
    e2e: End-to-end tests
    visual: Visual tests
"""

        config_file = self.project_root / "pytest-unit.ini"
        with open(config_file, "w") as f:
            f.write(pytest_config)

        # Run tests for each service separately to avoid import issues
        total_passed = 0
        total_failed = 0
        total_tests = 0
        coverage_sum = 0
        coverage_count = 0

        for test_file in unit_tests:
            service_dir = Path(test_file).parent.parent
            self.log(f"Running tests in {service_dir.name}: {Path(test_file).name}")

            # Run pytest with coverage for this specific test file
            cmd = [
                "python", "-m", "pytest",
                test_file,
                "--verbose",
                "--tb=short",
                f"--cov={service_dir}/src",
                f"--cov-report=html:{coverage_dir}/{service_dir.name}",
                f"--cov-report=xml:{coverage_dir}/{service_dir.name}/coverage.xml",
                "--cov-report=term-missing",
                "--disable-warnings",
                "--maxfail=5",
            ]

            exit_code, stdout, stderr = self.run_command(cmd, cwd=self.project_root)

            # Parse results
            if exit_code == 0:
                self.log(f"✅ {Path(test_file).name}: PASSED")
                # Extract test count from output
                lines = stdout.split("\n")
                for line in lines:
                    if "passed" in line and "failed" in line:
                        # Parse pytest output like "5 passed, 1 failed in 2.34s"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "passed":
                                total_passed += int(parts[i-1])
                            elif part == "failed":
                                total_failed += int(parts[i-1])
                        break
            else:
                self.log(f"❌ {Path(test_file).name}: FAILED", "ERROR")
                self.log(f"Error: {stderr}", "ERROR")
                total_failed += 1

        total_tests = total_passed + total_failed

        # Calculate average coverage
        coverage_avg = coverage_sum / coverage_count if coverage_count > 0 else 0

        self.log(f"Python unit tests completed: {total_passed} passed, {total_failed} failed")

        return {
            "passed": total_passed,
            "failed": total_failed,
            "total": total_tests,
            "coverage": round(coverage_avg, 2),
        }

    def run_typescript_unit_tests(self) -> dict:
        """Run TypeScript/React unit tests with coverage"""
        self.log("Starting TypeScript unit tests...")

        # Check if health-dashboard exists
        health_dashboard_dir = self.project_root / "services" / "health-dashboard"
        if not health_dashboard_dir.exists():
            self.log("Health dashboard not found, skipping TypeScript tests")
            return {"passed": 0, "failed": 0, "total": 0, "coverage": 0}

        # Find TypeScript test files
        typescript_tests = []
        for test_file in health_dashboard_dir.rglob("*.test.ts"):
            typescript_tests.append(str(test_file.relative_to(health_dashboard_dir)))
        for test_file in health_dashboard_dir.rglob("*.test.tsx"):
            typescript_tests.append(str(test_file.relative_to(health_dashboard_dir)))

        # Filter to unit tests only
        unit_tests = self.filter_unit_tests(typescript_tests)
        self.log(f"Found {len(unit_tests)} TypeScript unit test files")

        if not unit_tests:
            self.log("No TypeScript unit tests found")
            return {"passed": 0, "failed": 0, "total": 0, "coverage": 0}

        # Create Vitest configuration for unit tests only
        vitest_config = f"""
import {{ defineConfig }} from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  test: {{
    environment: 'happy-dom',
    include: [
      {', '.join([f'"{test}"' for test in unit_tests])}
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**',
      '**/integration/**',
      '**/visual/**',
      '**/*.integration.test.*',
      '**/*.e2e.test.*',
      '**/*.visual.test.*'
    ],
    coverage: {{
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      reportsDirectory: '../../test-results/coverage/typescript',
      include: ['src/**/*'],
      exclude: [
        'src/**/*.test.*',
        'src/**/*.spec.*',
        'src/tests/**',
        'src/**/__tests__/**',
        'src/**/*.stories.*',
        'src/**/*.config.*'
      ],
      thresholds: {{
        global: {{
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        }}
      }}
    }},
    globals: true,
    setupFiles: ['./src/tests/setup.ts']
  }}
}})
"""

        config_file = health_dashboard_dir / "vitest-unit.config.ts"
        with open(config_file, "w") as f:
            f.write(vitest_config)

        # Run Vitest with coverage
        cmd = [
            "npx", "vitest", "run",
            "--config", "vitest-unit.config.ts",
            "--coverage",
            "--reporter=verbose",
        ]

        exit_code, stdout, stderr = self.run_command(cmd, cwd=health_dashboard_dir)

        # Parse results
        total_passed = 0
        total_failed = 0
        coverage = 0

        if exit_code == 0:
            self.log("✅ TypeScript unit tests: PASSED")
            # Parse Vitest output
            lines = stdout.split("\n")
            for line in lines:
                if "passed" in line and "failed" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            total_passed = int(parts[i-1])
                        elif part == "failed":
                            total_failed = int(parts[i-1])
                elif "All files" in line and "%" in line:
                    # Extract coverage percentage
                    with contextlib.suppress(builtins.BaseException):
                        coverage = float(line.split("%")[0].split()[-1])
        else:
            self.log("❌ TypeScript unit tests: FAILED", "ERROR")
            self.log(f"Error: {stderr}", "ERROR")
            total_failed = 1

        total_tests = total_passed + total_failed

        self.log(f"TypeScript unit tests completed: {total_passed} passed, {total_failed} failed")

        return {
            "passed": total_passed,
            "failed": total_failed,
            "total": total_tests,
            "coverage": round(coverage, 2),
        }

    def generate_summary_report(self):
        """Generate comprehensive test summary report"""
        self.results["end_time"] = datetime.now().isoformat()
        start_time = datetime.fromisoformat(self.results["start_time"])
        end_time = datetime.fromisoformat(self.results["end_time"])
        self.results["duration_seconds"] = (end_time - start_time).total_seconds()

        # Create results directory
        results_dir = self.project_root / "test-results"
        results_dir.mkdir(exist_ok=True)

        # Generate JSON report
        report_file = results_dir / "unit-test-results.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Generate HTML report
        html_report = f"""
<!DOCTYPE html>
<html>
<head>
    <title>HomeIQ Unit Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; }}
        .python {{ border-left: 4px solid #3776ab; }}
        .typescript {{ border-left: 4px solid #3178c6; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        .coverage {{ color: #007bff; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 HomeIQ Unit Test Results</h1>
        <p>Generated: {self.results['end_time']}</p>
        <p>Duration: {self.results['duration_seconds']:.1f} seconds</p>
    </div>

    <div class="summary">
        <div class="card python">
            <h2>🐍 Python Unit Tests</h2>
            <p><strong>Total:</strong> {self.results['python']['total']}</p>
            <p class="success"><strong>Passed:</strong> {self.results['python']['passed']}</p>
            <p class="failure"><strong>Failed:</strong> {self.results['python']['failed']}</p>
            <p class="coverage"><strong>Coverage:</strong> {self.results['python']['coverage']}%</p>
        </div>

        <div class="card typescript">
            <h2>📘 TypeScript Unit Tests</h2>
            <p><strong>Total:</strong> {self.results['typescript']['total']}</p>
            <p class="success"><strong>Passed:</strong> {self.results['typescript']['passed']}</p>
            <p class="failure"><strong>Failed:</strong> {self.results['typescript']['failed']}</p>
            <p class="coverage"><strong>Coverage:</strong> {self.results['typescript']['coverage']}%</p>
        </div>
    </div>

    <div class="card">
        <h2>📊 Overall Summary</h2>
        <p><strong>Total Tests:</strong> {self.results['python']['total'] + self.results['typescript']['total']}</p>
        <p><strong>Total Passed:</strong> {self.results['python']['passed'] + self.results['typescript']['passed']}</p>
        <p><strong>Total Failed:</strong> {self.results['python']['failed'] + self.results['typescript']['failed']}</p>
        <p><strong>Success Rate:</strong> {((self.results['python']['passed'] + self.results['typescript']['passed']) / max(1, self.results['python']['total'] + self.results['typescript']['total']) * 100):.1f}%</p>
    </div>

    <div class="footer">
        <p>Coverage reports available in test-results/coverage/</p>
        <p>Detailed results in test-results/unit-test-results.json</p>
    </div>
</body>
</html>
"""

        html_file = results_dir / "unit-test-report.html"
        with open(html_file, "w") as f:
            f.write(html_report)

        self.log(f"📊 Summary report generated: {html_file}")
        self.log(f"📄 Detailed results: {report_file}")

    def run_all_tests(self, python_only: bool = False, typescript_only: bool = False):
        """Run all unit tests"""
        start_time = time.time()

        self.log("🚀 Starting HomeIQ Unit Test Framework")
        self.log("=" * 60)

        # Run Python tests
        if not typescript_only:
            self.results["python"] = self.run_python_unit_tests()

        # Run TypeScript tests
        if not python_only:
            self.results["typescript"] = self.run_typescript_unit_tests()

        # Generate reports
        self.generate_summary_report()

        # Print summary
        total_tests = self.results["python"]["total"] + self.results["typescript"]["total"]
        total_passed = self.results["python"]["passed"] + self.results["typescript"]["passed"]
        total_failed = self.results["python"]["failed"] + self.results["typescript"]["failed"]

        self.log("=" * 60)
        self.log("🎯 UNIT TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {total_tests}")
        self.log(f"✅ Passed: {total_passed}")
        self.log(f"❌ Failed: {total_failed}")
        self.log(f"📊 Success Rate: {(total_passed/max(1,total_tests)*100):.1f}%")
        self.log(f"⏱️  Duration: {time.time() - start_time:.1f}s")
        self.log("=" * 60)

        if total_failed > 0:
            self.log("⚠️  Some tests failed. Check the detailed reports.", "ERROR")
            return 1
        self.log("🎉 All unit tests passed!")
        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="HomeIQ Unit Testing Framework")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--python-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--typescript-only", action="store_true", help="Run only TypeScript tests")
    parser.add_argument("--coverage-only", action="store_true", help="Generate coverage reports only")

    args = parser.parse_args()

    framework = UnitTestFramework(verbose=args.verbose)

    if args.coverage_only:
        framework.generate_summary_report()
        return 0

    return framework.run_all_tests(
        python_only=args.python_only,
        typescript_only=args.typescript_only,
    )


if __name__ == "__main__":
    sys.exit(main())
