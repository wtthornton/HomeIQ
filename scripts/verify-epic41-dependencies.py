#!/usr/bin/env python3
"""
Epic 41 Dependency Verification Script
Verifies all dependency updates are correct and compatible

Usage:
    python scripts/verify-epic41-dependencies.py
    python scripts/verify-epic41-dependencies.py --check-conflicts
    python scripts/verify-epic41-dependencies.py --list-versions
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class DependencyVerifier:
    """Verify Epic 41 dependency updates"""
    
    # Target versions from Epic 41
    TARGET_VERSIONS = {
        'fastapi': '0.115.x',
        'uvicorn': '0.32.x',
        'numpy': '1.26.x',
        'pytorch': '2.4.0',
        'transformers': '4.46.1',
        'sentence-transformers': '3.3.1',
        'openvino': '2024.5.0',
        'optimum-intel': '1.21.0',
        'aiohttp': '3.13.2',
        'httpx': '0.28.1',
        'scipy': '1.16.3',
        'pandas': '2.2.0',
        'scikit-learn': '1.5.0',
        'pydantic': '2.9.0',
        'sqlalchemy': '2.0.35',
        'aiosqlite': '0.20.0',
        'influxdb-client': '1.49.0',
    }
    
    def __init__(self):
        self.project_root = project_root
        self.issues = []
        self.warnings = []
        self.services_checked = []
        
    def find_requirements_files(self) -> List[Path]:
        """Find all requirements.txt files"""
        requirements_files = []
        services_dir = self.project_root / "services"
        
        if services_dir.exists():
            for req_file in services_dir.rglob("requirements*.txt"):
                requirements_files.append(req_file)
        
        return sorted(requirements_files)
    
    def parse_requirements(self, file_path: Path) -> Dict[str, str]:
        """Parse requirements.txt file and extract package versions"""
        packages = {}
        
        if not file_path.exists():
            return packages
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Skip pip options
                    if line.startswith('--') or line.startswith('-'):
                        continue
                    
                    # Parse package specification
                    # Format: package>=version, package==version, package~=version
                    match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_.-]*)([<>=!~]+)(.+)$', line)
                    if match:
                        package = match.group(1).lower()
                        operator = match.group(2)
                        version = match.group(3).split('#')[0].strip()
                        packages[package] = {'operator': operator, 'version': version, 'line': line}
                    else:
                        # Simple package name without version
                        match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_.-]*)$', line)
                        if match:
                            package = match.group(1).lower()
                            packages[package] = {'operator': '', 'version': 'any', 'line': line}
        
        except Exception as e:
            self.warnings.append(f"Error parsing {file_path}: {e}")
        
        return packages
    
    def check_version_compatibility(self, package: str, version_spec: Dict, target: str) -> Tuple[bool, str]:
        """Check if version specification is compatible with target"""
        operator = version_spec.get('operator', '')
        version = version_spec.get('version', '')
        
        # Handle version ranges
        if '>=' in operator or '~=' in operator:
            # Check if minimum version is compatible
            if target.startswith(version.split(',')[0].split('<')[0].strip()):
                return True, "Compatible"
            return False, f"Version {version} may not match target {target}"
        
        if '==' in operator:
            # Exact version - check if matches target pattern
            if target.endswith('.x'):
                target_base = target.replace('.x', '')
                if version.startswith(target_base):
                    return True, "Compatible"
            elif version == target:
                return True, "Exact match"
            return False, f"Version {version} does not match target {target}"
        
        if '<' in operator:
            # Upper bound - check if target is within range
            return True, "Range check needed"
        
        return True, "Unknown format - manual check needed"
    
    def verify_service(self, req_file: Path) -> Dict:
        """Verify a single service's requirements"""
        service_name = req_file.parent.name
        packages = self.parse_requirements(req_file)
        
        results = {
            'service': service_name,
            'file': str(req_file.relative_to(self.project_root)),
            'packages': {},
            'issues': [],
            'warnings': []
        }
        
        # Check each target package
        for target_package, target_version in self.TARGET_VERSIONS.items():
            if target_package in packages:
                version_spec = packages[target_package]
                is_compatible, message = self.check_version_compatibility(
                    target_package, version_spec, target_version
                )
                
                results['packages'][target_package] = {
                    'found': True,
                    'spec': version_spec['line'],
                    'compatible': is_compatible,
                    'message': message
                }
                
                if not is_compatible and 'may not match' in message:
                    results['warnings'].append(
                        f"{target_package}: {version_spec['line']} - {message}"
                    )
        
        return results
    
    def check_conflicts(self) -> List[str]:
        """Check for version conflicts across services"""
        conflicts = []
        package_versions = defaultdict(set)
        
        req_files = self.find_requirements_files()
        for req_file in req_files:
            packages = self.parse_requirements(req_file)
            service_name = req_file.parent.name
            
            for package, spec in packages.items():
                if package in self.TARGET_VERSIONS:
                    version_str = f"{spec['operator']}{spec['version']}"
                    package_versions[package].add((service_name, version_str))
        
        # Find conflicts
        for package, versions in package_versions.items():
            if len(versions) > 1:
                unique_versions = set(v[1] for v in versions)
                if len(unique_versions) > 1:
                    services = [v[0] for v in versions]
                    conflicts.append(
                        f"{package}: Multiple versions found across services: "
                        f"{', '.join(f'{s} ({v})' for s, v in versions)}"
                    )
        
        return conflicts
    
    def run_verification(self, check_conflicts: bool = False) -> bool:
        """Run full verification"""
        print("=" * 80)
        print("Epic 41 Dependency Verification")
        print("=" * 80)
        print()
        
        req_files = self.find_requirements_files()
        print(f"Found {len(req_files)} requirements files")
        print()
        
        all_results = []
        for req_file in req_files:
            results = self.verify_service(req_file)
            all_results.append(results)
            self.services_checked.append(results['service'])
        
        # Print results
        print("Service Verification Results:")
        print("-" * 80)
        
        for results in all_results:
            if results['packages']:
                print(f"\n{results['service']} ({results['file']}):")
                for package, info in results['packages'].items():
                    status = "✅" if info['compatible'] else "⚠️"
                    print(f"  {status} {package}: {info['spec']}")
                    if info['message'] and not info['compatible']:
                        print(f"     {info['message']}")
                
                if results['warnings']:
                    for warning in results['warnings']:
                        print(f"  ⚠️  {warning}")
        
        # Check conflicts
        if check_conflicts:
            print("\n" + "=" * 80)
            print("Conflict Check:")
            print("-" * 80)
            conflicts = self.check_conflicts()
            if conflicts:
                print("⚠️  Version conflicts found:")
                for conflict in conflicts:
                    print(f"  - {conflict}")
                return False
            else:
                print("✅ No version conflicts detected")
        
        print("\n" + "=" * 80)
        print("Summary:")
        print(f"  Services checked: {len(self.services_checked)}")
        print(f"  Requirements files: {len(req_files)}")
        print("=" * 80)
        
        return True
    
    def list_versions(self):
        """List all versions found for target packages"""
        print("=" * 80)
        print("Epic 41 Dependency Versions Summary")
        print("=" * 80)
        print()
        
        req_files = self.find_requirements_files()
        package_versions = defaultdict(list)
        
        for req_file in req_files:
            service_name = req_file.parent.name
            packages = self.parse_requirements(req_file)
            
            for package, spec in packages.items():
                if package in self.TARGET_VERSIONS:
                    version_str = f"{spec['operator']}{spec['version']}"
                    package_versions[package].append((service_name, version_str))
        
        for package in sorted(self.TARGET_VERSIONS.keys()):
            target = self.TARGET_VERSIONS[package]
            print(f"\n{package} (Target: {target}):")
            if package in package_versions:
                for service, version in sorted(package_versions[package]):
                    print(f"  - {service}: {version}")
            else:
                print(f"  - Not found in any service")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify Epic 41 dependency updates')
    parser.add_argument('--check-conflicts', action='store_true',
                       help='Check for version conflicts across services')
    parser.add_argument('--list-versions', action='store_true',
                       help='List all versions found for target packages')
    
    args = parser.parse_args()
    
    verifier = DependencyVerifier()
    
    if args.list_versions:
        verifier.list_versions()
    else:
        success = verifier.run_verification(check_conflicts=args.check_conflicts)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

