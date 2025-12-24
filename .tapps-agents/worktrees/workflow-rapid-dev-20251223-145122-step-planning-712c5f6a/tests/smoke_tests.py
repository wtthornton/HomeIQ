#!/usr/bin/env python3
"""
Smoke Tests for HomeIQ Services
Comprehensive health checks for all services before production deployment.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmokeTestRunner:
    """Run smoke tests against all HomeIQ services."""
    
    def __init__(self, timeout: int = 10, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Service endpoints to test
        self.services = {
            'influxdb': {
                'url': 'http://localhost:8086/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': True
            },
            'websocket-ingestion': {
                'url': 'http://localhost:8001/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': True
            },
            'admin-api': {
                'url': 'http://localhost:8003/api/v1/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': True
            },
            'data-api': {
                'url': 'http://localhost:8006/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': True
            },
            'device-intelligence': {
                'url': 'http://localhost:8028/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': False
            },
            'ai-automation-service': {
                'url': 'http://localhost:8024/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': False
            },
            'health-dashboard': {
                'url': 'http://localhost:3000',
                'method': 'GET',
                'expected_status': 200,
                'critical': False
            },
            'data-retention': {
                'url': 'http://localhost:8080/health',
                'method': 'GET',
                'expected_status': 200,
                'critical': False
            }
        }
    
    def test_endpoint(self, service_name: str, config: Dict) -> Tuple[bool, Dict]:
        """Test a single service endpoint."""
        url = config['url']
        method = config['method']
        expected_status = config['expected_status']
        critical = config['critical']
        
        result = {
            'service': service_name,
            'url': url,
            'status': 'unknown',
            'passed': False,
            'response_time_ms': 0,
            'error': None,
            'critical': critical
        }
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=self.timeout)
            else:
                response = requests.request(method, url, timeout=self.timeout)
            
            response_time = (time.time() - start_time) * 1000
            result['response_time_ms'] = round(response_time, 2)
            result['status_code'] = response.status_code
            
            if response.status_code == expected_status:
                result['status'] = 'healthy'
                result['passed'] = True
                if self.verbose:
                    logger.debug(f"✅ {service_name}: {url} - {response.status_code} ({response_time:.2f}ms)")
            else:
                result['status'] = f'unexpected_status_{response.status_code}'
                result['error'] = f"Expected {expected_status}, got {response.status_code}"
                if self.verbose:
                    logger.warning(f"⚠️  {service_name}: {url} - {response.status_code} (expected {expected_status})")
        
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['error'] = f"Request timed out after {self.timeout}s"
            logger.error(f"❌ {service_name}: {url} - Timeout")
        
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
            result['error'] = "Connection refused - service may not be running"
            logger.error(f"❌ {service_name}: {url} - Connection refused")
        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"❌ {service_name}: {url} - Error: {e}")
        
        return result['passed'], result
    
    def run_all_tests(self) -> Dict:
        """Run all smoke tests and return results."""
        logger.info("="*80)
        logger.info("Running Smoke Tests")
        logger.info("="*80)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.services),
            'passed': 0,
            'failed': 0,
            'critical_passed': 0,
            'critical_failed': 0,
            'services': []
        }
        
        for service_name, config in self.services.items():
            logger.info(f"Testing {service_name}...")
            passed, result = self.test_endpoint(service_name, config)
            
            results['services'].append(result)
            
            if passed:
                results['passed'] += 1
                if config['critical']:
                    results['critical_passed'] += 1
                logger.info(f"✅ {service_name}: PASSED")
            else:
                results['failed'] += 1
                if config['critical']:
                    results['critical_failed'] += 1
                logger.warning(f"❌ {service_name}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Overall status
        all_critical_passed = results['critical_failed'] == 0
        all_passed = results['failed'] == 0
        
        results['overall_status'] = 'pass' if all_critical_passed else 'fail'
        results['all_critical_passed'] = all_critical_passed
        results['all_passed'] = all_passed
        
        logger.info("="*80)
        logger.info("Smoke Test Summary")
        logger.info("="*80)
        logger.info(f"Total Tests: {results['total_tests']}")
        logger.info(f"Passed: {results['passed']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Critical Passed: {results['critical_passed']}")
        logger.info(f"Critical Failed: {results['critical_failed']}")
        logger.info(f"Overall Status: {results['overall_status'].upper()}")
        logger.info("="*80)
        
        return results


def main():
    """Main entry point for smoke tests."""
    parser = argparse.ArgumentParser(description='Run smoke tests for HomeIQ services')
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--output',
        type=str,
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        help='Save results to file (JSON format)'
    )
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(timeout=args.timeout, verbose=args.verbose)
    results = runner.run_all_tests()
    
    # Save to file if requested
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    
    # Output in requested format
    if args.output == 'json':
        print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if results['overall_status'] == 'pass':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

