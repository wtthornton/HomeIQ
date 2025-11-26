#!/usr/bin/env python3
"""
Pattern & Synergy Test Runner

Runs all pattern and synergy detection tests and generates a comprehensive report.
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path

# Test files to run
PATTERN_TESTS = [
    "tests/datasets/test_pattern_detection_comprehensive.py",
    "tests/datasets/test_pattern_detection_with_datasets.py",
    "tests/datasets/test_single_home_patterns.py",
    "tests/test_ml_pattern_detectors.py",
]

SYNERGY_TESTS = [
    "tests/datasets/test_synergy_detection_comprehensive.py",
    "tests/test_synergy_detector.py",
    "tests/test_synergy_crud.py",
    "tests/test_synergy_suggestion_generator.py",
]

ALL_TESTS = PATTERN_TESTS + SYNERGY_TESTS


def check_environment():
    """Check if required environment variables are set"""
    required_vars = ["HA_URL", "HA_TOKEN", "MQTT_BROKER", "OPENAI_API_KEY"]
    missing = []
    
    import os
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("⚠️  Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 Create a .env.test file or set environment variables")
        return False
    
    return True


def run_test_file(test_file: str, verbose: bool = True) -> dict:
    """Run a single test file and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {test_file}")
    print(f"{'='*80}")
    
    cmd = ["pytest", test_file, "--tb=short"]
    if verbose:
        cmd.append("-v")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent / "services" / "ai-automation-service"
    )
    
    return {
        "file": test_file,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0
    }


def run_all_tests(test_files: list[str], verbose: bool = True) -> dict:
    """Run all test files and collect results"""
    results = {}
    total_passed = 0
    total_failed = 0
    
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
        
        result = run_test_file(test_file, verbose)
        results[test_file] = result
        
        if result["success"]:
            total_passed += 1
        else:
            total_failed += 1
    
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "passed": total_passed,
            "failed": total_failed,
            "timestamp": datetime.now().isoformat()
        }
    }


def generate_report(test_results: dict, output_file: str = None):
    """Generate a test report"""
    summary = test_results["summary"]
    
    print("\n" + "="*80)
    print("TEST EXECUTION SUMMARY")
    print("="*80)
    print(f"Total test files: {summary['total']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"Timestamp: {summary['timestamp']}")
    
    # Show failed tests
    if summary['failed'] > 0:
        print("\n" + "="*80)
        print("FAILED TESTS")
        print("="*80)
        for test_file, result in test_results["results"].items():
            if not result["success"]:
                print(f"\n❌ {test_file}")
                print(f"   Return code: {result['returncode']}")
                # Show last few lines of output
                lines = result["stdout"].split("\n")
                if lines:
                    print(f"   Last output: {lines[-3:]}")
    
    # Save JSON report
    if output_file:
        with open(output_file, "w") as f:
            json.dump(test_results, f, indent=2)
        print(f"\n📄 Detailed report saved to: {output_file}")
    
    return test_results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run pattern and synergy tests")
    parser.add_argument(
        "--pattern-only",
        action="store_true",
        help="Run only pattern tests"
    )
    parser.add_argument(
        "--synergy-only",
        action="store_true",
        help="Run only synergy tests"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check environment variables and exit"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for JSON report"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Check environment
    if args.check_env:
        if check_environment():
            print("✅ All required environment variables are set")
            return 0
        else:
            return 1
    
    # Select tests to run
    if args.pattern_only:
        test_files = PATTERN_TESTS
    elif args.synergy_only:
        test_files = SYNERGY_TESTS
    else:
        test_files = ALL_TESTS
    
    # Run tests
    print("🧪 Pattern & Synergy Test Runner")
    print("="*80)
    
    if not check_environment():
        print("\n⚠️  Some environment variables are missing, but continuing anyway...")
        print("   Tests may fail if they require these variables\n")
    
    test_results = run_all_tests(test_files, verbose=not args.quiet)
    
    # Generate report
    output_file = args.output or f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    generate_report(test_results, output_file)
    
    # Return exit code
    return 0 if test_results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

