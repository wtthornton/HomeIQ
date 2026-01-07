#!/usr/bin/env python3
"""
Safe Test Runner for HomeIQ
Runs tests in batches to prevent Cursor timeouts and crashes

This script:
- Runs tests in small batches (5-10 files at a time)
- Has timeout protection (5 minutes per batch)
- Provides progress updates
- Saves results incrementally
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Batch size - run this many test files at once
BATCH_SIZE = 5
TIMEOUT_PER_BATCH = 300  # 5 minutes per batch
MAX_FAILURES = 10  # Stop after this many failures

class SafeTestRunner:
    """Safe test runner that prevents timeouts"""
    
    def __init__(self):
        self.project_root = project_root
        self.results = {
            'batches': [],
            'total_passed': 0,
            'total_failed': 0,
            'total_skipped': 0,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'duration_seconds': 0
        }
        self.failure_count = 0
        
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Handle Windows encoding issues - use ASCII-safe fallback
        try:
            print(f"[{timestamp}] {message}")
        except UnicodeEncodeError:
            # Replace Unicode characters with ASCII equivalents
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(f"[{timestamp}] {safe_message}")
        
    def get_test_files_from_config(self) -> List[str]:
        """Read test files from pytest-unit.ini"""
        config_file = project_root / "pytest-unit.ini"
        if not config_file.exists():
            self.log("ERROR: pytest-unit.ini not found")
            return []
            
        test_files = []
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract testpaths line
            for line in content.split('\n'):
                if line.strip().startswith('testpaths'):
                    # Parse the comma-separated list
                    testpaths = line.split('=', 1)[1].strip()
                    # Split by comma and clean up
                    files = [f.strip().replace('\\', '/') for f in testpaths.split(',')]
                    test_files.extend(files)
                    break
                    
        return test_files
    
    def run_test_batch(self, test_files: List[str], batch_num: int) -> Dict:
        """Run a batch of test files"""
        self.log(f"Running batch {batch_num} ({len(test_files)} files)...")
        
        batch_start = time.time()
        batch_results = {
            'batch_num': batch_num,
            'files': test_files,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Convert test files to full paths relative to project root
        full_paths = []
        for test_file in test_files:
            # Handle both Windows and Unix paths
            test_file = test_file.replace('\\', '/')
            full_path = project_root / test_file
            if full_path.exists():
                full_paths.append(str(full_path))
            else:
                self.log(f"  [WARN] Test file not found: {test_file}")
        
        if not full_paths:
            self.log(f"  [SKIP] No valid test files in batch {batch_num}")
            return {
                'batch_num': batch_num,
                'files': test_files,
                'passed': 0,
                'failed': 0,
                'skipped': len(test_files),
                'errors': ['No valid test files found'],
                'duration': 0
            }
        
        # Run pytest on this batch
        cmd = [
            sys.executable, "-m", "pytest",
            *full_paths,
            "--verbose",
            "--tb=short",
            "--maxfail=5",  # Stop batch after 5 failures
            "--disable-warnings",
            "-q"  # Quiet mode to reduce output
        ]
        
        try:
            self.log(f"  Executing: pytest {' '.join([Path(f).name for f in full_paths])}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_PER_BATCH,
                encoding='utf-8',
                errors='replace'  # Handle encoding errors gracefully
            )
            
            batch_duration = time.time() - batch_start
            
            # Parse pytest output
            output = result.stdout + result.stderr
            
            # Look for pytest summary line: "X passed, Y failed in Zs" or "X passed in Zs"
            # Pattern: "======================= 10 passed, 9 warnings in 1.09s ======================="
            for line in output.split('\n'):
                line = line.strip()
                # Look for summary line with passed/failed counts
                if ('passed' in line or 'failed' in line) and ('in' in line or 'warnings' in line):
                    # Extract numbers before "passed" and "failed"
                    import re
                    # Match patterns like "10 passed", "5 failed", "10 passed, 2 failed"
                    passed_match = re.search(r'(\d+)\s+passed', line)
                    failed_match = re.search(r'(\d+)\s+failed', line)
                    skipped_match = re.search(r'(\d+)\s+skipped', line)
                    
                    if passed_match:
                        batch_results['passed'] = int(passed_match.group(1))
                    if failed_match:
                        batch_results['failed'] = int(failed_match.group(1))
                    if skipped_match:
                        batch_results['skipped'] = int(skipped_match.group(1))
                    break
            
            if result.returncode == 0:
                self.log(f"  [OK] Batch {batch_num} PASSED ({batch_results['passed']} tests, {batch_duration:.1f}s)")
            else:
                
                # Extract error summary (last few lines)
                error_lines = output.split('\n')[-10:]
                batch_results['errors'] = [line for line in error_lines if line.strip() and 'FAILED' in line]
                
                self.log(f"  [FAIL] Batch {batch_num} FAILED ({batch_results['failed']} failed, {batch_results['passed']} passed, {batch_duration:.1f}s)")
                self.failure_count += batch_results['failed']
                
                # Show first error
                if batch_results['errors']:
                    self.log(f"  First error: {batch_results['errors'][0][:100]}")
            
            batch_results['duration'] = batch_duration
            return batch_results
            
        except subprocess.TimeoutExpired:
            self.log(f"  [TIMEOUT] Batch {batch_num} TIMED OUT after {TIMEOUT_PER_BATCH}s")
            batch_results['errors'] = [f"Batch timed out after {TIMEOUT_PER_BATCH} seconds"]
            batch_results['failed'] = len(test_files)  # Count all as failed
            self.failure_count += batch_results['failed']
            return batch_results
        except Exception as e:
            self.log(f"  [ERROR] Batch {batch_num} ERROR: {str(e)}")
            batch_results['errors'] = [str(e)]
            batch_results['failed'] = len(test_files)
            self.failure_count += batch_results['failed']
            return batch_results
    
    def save_results(self):
        """Save results to JSON file"""
        results_file = project_root / "test-results" / "safe-test-results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"Results saved to {results_file}")
    
    def run(self):
        """Main execution"""
        self.log("=" * 60)
        self.log("HomeIQ Safe Test Runner")
        self.log("=" * 60)
        self.log("")
        
        # Get test files from config
        test_files = self.get_test_files_from_config()
        if not test_files:
            self.log("ERROR: No test files found in pytest-unit.ini")
            return 1
        
        self.log(f"Found {len(test_files)} test files in pytest-unit.ini")
        self.log(f"Running in batches of {BATCH_SIZE} files")
        self.log(f"Timeout: {TIMEOUT_PER_BATCH}s per batch")
        self.log("")
        
        # Split into batches
        batches = []
        for i in range(0, len(test_files), BATCH_SIZE):
            batch = test_files[i:i+BATCH_SIZE]
            batches.append(batch)
        
        self.log(f"Total batches: {len(batches)}")
        self.log("")
        
        # Run each batch
        for batch_num, batch in enumerate(batches, 1):
            if self.failure_count >= MAX_FAILURES:
                self.log(f"")
                self.log(f"[WARN] Stopping: {self.failure_count} failures reached (max: {MAX_FAILURES})")
                break
            
            batch_result = self.run_test_batch(batch, batch_num)
            self.results['batches'].append(batch_result)
            self.results['total_passed'] += batch_result['passed']
            self.results['total_failed'] += batch_result['failed']
            self.results['total_skipped'] += batch_result.get('skipped', 0)
            
            # Save results after each batch (incremental save)
            self.save_results()
            
            # Small delay between batches to prevent resource exhaustion
            if batch_num < len(batches):
                time.sleep(1)
        
        # Final summary
        self.results['end_time'] = datetime.now().isoformat()
        duration = (datetime.fromisoformat(self.results['end_time']) - 
                   datetime.fromisoformat(self.results['start_time'])).total_seconds()
        self.results['duration_seconds'] = duration
        
        self.log("")
        self.log("=" * 60)
        self.log("Test Summary")
        self.log("=" * 60)
        self.log(f"Total batches: {len(self.results['batches'])}")
        self.log(f"Total passed: {self.results['total_passed']}")
        self.log(f"Total failed: {self.results['total_failed']}")
        self.log(f"Total skipped: {self.results['total_skipped']}")
        self.log(f"Duration: {duration:.1f}s")
        self.log("")
        
        # Save final results
        self.save_results()
        
        # Return exit code
        if self.results['total_failed'] > 0:
            self.log("[FAIL] Some tests failed")
            return 1
        else:
            self.log("[OK] All tests passed!")
            return 0

if __name__ == "__main__":
    runner = SafeTestRunner()
    exit_code = runner.run()
    sys.exit(exit_code)
