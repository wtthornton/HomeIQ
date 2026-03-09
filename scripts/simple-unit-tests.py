#!/usr/bin/env python3
"""
Simple Unit Test Runner for HomeIQ
Provides clear visual progress and runs unit tests with coverage

Usage:
    python scripts/simple-unit-tests.py
    python scripts/simple-unit-tests.py --python-only
    python scripts/simple-unit-tests.py --typescript-only
"""

import json
import re
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
            'python': {'passed': 0, 'failed': 0, 'total': 0, 'coverage': 0},
            'typescript': {'passed': 0, 'failed': 0, 'total': 0, 'coverage': 0},
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration_seconds': 0
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
        start_time_str = self.results['start_time']
        if isinstance(start_time_str, str):
            # Parse ISO format and format it nicely
            start_dt = datetime.fromisoformat(start_time_str)
            print(f"Started: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"Started: {start_time_str.strftime('%Y-%m-%d %H:%M:%S')}")
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
    
    # Test directories to run independently (avoids cross-directory import conflicts)
    TEST_DIRS = [
        "libs/homeiq-patterns/tests",
        "libs/homeiq-resilience/tests",
        "libs/homeiq-data/tests",
        "libs/homeiq-ha/tests",
        "libs/homeiq-observability/tests",
        "libs/homeiq-memory/tests",
        "domains/core-platform/admin-api/tests",
        "domains/core-platform/data-api/tests",
        "domains/core-platform/data-retention/tests",
        "domains/core-platform/ha-simulator/tests",
        "domains/core-platform/websocket-ingestion/tests",
        "domains/automation-core/ai-automation-service-new/tests",
        "domains/automation-core/ai-code-executor/tests",
        "domains/automation-core/ai-query-service/tests",
        "domains/automation-core/automation-linter/tests",
        "domains/automation-core/automation-trace-service/tests",
        "domains/automation-core/ha-ai-agent-service/tests",
        "domains/automation-core/yaml-validation-service/tests",
        "domains/blueprints/automation-miner/tests",
        "domains/blueprints/blueprint-index/tests",
        "domains/data-collectors/air-quality-service/tests",
        "domains/data-collectors/calendar-service/tests",
        "domains/data-collectors/carbon-intensity-service/tests",
        "domains/data-collectors/electricity-pricing-service/tests",
        "domains/data-collectors/log-aggregator/tests",
        "domains/data-collectors/smart-meter-service/tests",
        "domains/data-collectors/sports-api/tests",
        "domains/data-collectors/weather-api/tests",
        "domains/device-management/ha-setup-service/tests",
        "domains/energy-analytics/energy-correlator/tests",
        "domains/energy-analytics/energy-forecasting/tests",
        "domains/energy-analytics/proactive-agent-service/tests",
        "domains/frontends/observability-dashboard/tests",
        "domains/ml-engine/ai-core-service/tests",
        "domains/ml-engine/ai-training-service/tests",
        "domains/ml-engine/device-intelligence-service/tests",
        "domains/ml-engine/ml-service/tests",
        "domains/ml-engine/openvino-service/tests",
        "domains/ml-engine/rag-service/tests",
        "domains/pattern-analysis/ai-pattern-service/tests",
    ]

    def run_python_tests(self):
        """Run Python unit tests per-directory to avoid import conflicts."""
        self.print_progress("Starting Python unit tests...")

        total_passed = 0
        total_failed = 0
        failed_dirs = []

        for test_dir in self.TEST_DIRS:
            test_path = self.project_root / test_dir
            if not test_path.exists():
                continue

            cmd = [
                sys.executable, "-m", "pytest", str(test_path),
                "--tb=short", "--no-header", "-q",
                "--disable-warnings", "--maxfail=10"
            ]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                output = result.stdout + result.stderr
                passed = 0
                failed = 0
                for line in output.split('\n'):
                    passed_matches = re.findall(r'(\d+)\s+passed', line, re.IGNORECASE)
                    failed_matches = re.findall(r'(\d+)\s+failed', line, re.IGNORECASE)
                    error_matches = re.findall(r'(\d+)\s+error', line, re.IGNORECASE)
                    if passed_matches:
                        passed = int(passed_matches[0])
                    if failed_matches:
                        failed = int(failed_matches[0])
                    if error_matches:
                        failed += int(error_matches[0])

                total_passed += passed
                total_failed += failed

                status = "SUCCESS" if failed == 0 and result.returncode == 0 else "WARNING"
                self.print_progress(f"  {test_dir}: {passed} passed, {failed} failed", status)
                if failed > 0:
                    failed_dirs.append(test_dir)

            except subprocess.TimeoutExpired:
                self.print_progress(f"  {test_dir}: TIMEOUT", "ERROR")
                total_failed += 1
                failed_dirs.append(test_dir)
            except Exception as e:
                self.print_progress(f"  {test_dir}: ERROR - {e}", "ERROR")
                total_failed += 1
                failed_dirs.append(test_dir)

        self.results['python']['passed'] = total_passed
        self.results['python']['failed'] = total_failed
        self.results['python']['total'] = total_passed + total_failed

        if total_failed == 0:
            self.print_progress(f"Python tests completed: {total_passed} passed", "SUCCESS")
        else:
            self.print_progress(
                f"Python tests: {total_passed} passed, {total_failed} failed in {len(failed_dirs)} dir(s)",
                "WARNING"
            )
    
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
            "--reporter=verbose"
        ]
        
        try:
            self.print_progress(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=health_dashboard_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.print_progress("TypeScript tests completed successfully", "SUCCESS")
                # Parse results
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and 'failed' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'passed':
                                self.results['typescript']['passed'] = int(parts[i-1])
                            elif part == 'failed':
                                self.results['typescript']['failed'] = int(parts[i-1])
                        break
            else:
                self.print_progress("TypeScript tests had failures", "WARNING")
                self.results['typescript']['failed'] = 1
            
            self.results['typescript']['total'] = self.results['typescript']['passed'] + self.results['typescript']['failed']
            
        except subprocess.TimeoutExpired:
            self.print_progress("TypeScript tests timed out after 5 minutes", "ERROR")
            self.results['typescript']['failed'] = 1
            self.results['typescript']['total'] = 1
        except Exception as e:
            self.print_progress(f"Error running TypeScript tests: {str(e)}", "ERROR")
            self.results['typescript']['failed'] = 1
            self.results['typescript']['total'] = 1
    
    def save_results(self):
        """Save results to JSON and generate HTML report"""
        self.results['end_time'] = datetime.now().isoformat()
        start_time = datetime.fromisoformat(self.results['start_time'])
        end_time = datetime.fromisoformat(self.results['end_time'])
        self.results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        # Save JSON results
        json_file = self.results_dir / "unit-test-results.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        self.print_progress(f"Results saved to: {json_file}", "SUCCESS")
        
        # Generate HTML report
        html_report = f"""<!DOCTYPE html>
<html>
<head>
    <title>HomeIQ Unit Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
        .card {{ background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .python {{ border-left: 4px solid #3776ab; }}
        .typescript {{ border-left: 4px solid #3178c6; }}
        .success {{ color: #28a745; font-weight: bold; }}
        .failure {{ color: #dc3545; font-weight: bold; }}
        .coverage {{ color: #007bff; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
        h1 {{ margin: 0 0 10px 0; }}
        h2 {{ margin-top: 0; }}
        .overall {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 HomeIQ Unit Test Results</h1>
        <p><strong>Generated:</strong> {self.results['end_time']}</p>
        <p><strong>Duration:</strong> {self.results['duration_seconds']:.1f} seconds</p>
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
    
    <div class="overall">
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
</html>"""
        
        html_file = self.results_dir / "unit-test-report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        self.print_progress(f"HTML report generated: {html_file}", "SUCCESS")
    
    def print_summary(self):
        """Print final summary with visual indicators"""
        self.results['end_time'] = datetime.now().isoformat()
        start_time = datetime.fromisoformat(self.results['start_time'])
        end_time = datetime.fromisoformat(self.results['end_time'])
        self.results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("UNIT TEST SUMMARY")
        print("=" * 80)
        
        # Python results
        python_total = self.results['python']['total']
        python_passed = self.results['python']['passed']
        python_failed = self.results['python']['failed']
        
        if python_total > 0:
            python_rate = (python_passed / python_total) * 100
            status_icon = "[PASS]" if python_failed == 0 else "[WARN]"
            print(f"{status_icon} Python Tests: {python_passed}/{python_total} passed ({python_rate:.1f}%)")
        
        # TypeScript results
        ts_total = self.results['typescript']['total']
        ts_passed = self.results['typescript']['passed']
        ts_failed = self.results['typescript']['failed']
        
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
        
        print(f"Duration: {self.results['duration_seconds']:.1f} seconds")
        print("=" * 80)
        
        # Coverage reports
        print("Coverage Reports:")
        print(f"   Python: test-results/coverage/python/index.html")
        print(f"   TypeScript: test-results/coverage/typescript/index.html")
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
        
        # Save results and generate reports
        self.save_results()
        
        # Print summary
        success = self.print_summary()
        
        return 0 if success else 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple HomeIQ Unit Test Runner')
    parser.add_argument('--python-only', action='store_true', help='Run only Python tests')
    parser.add_argument('--typescript-only', action='store_true', help='Run only TypeScript tests')
    
    args = parser.parse_args()
    
    runner = SimpleUnitTestRunner()
    return runner.run_all_tests(
        python_only=args.python_only,
        typescript_only=args.typescript_only
    )


if __name__ == "__main__":
    sys.exit(main())
