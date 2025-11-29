#!/usr/bin/env python3
"""
Import Validation Script (Epic 44.2: Import Validation at Build Time)

Validates all imports for a service/module to catch import errors before deployment.
Can be run during Docker build or as a standalone check.

Usage:
    python scripts/validate_imports.py                    # Validate all services
    python scripts/validate_imports.py --service <name> # Validate specific service
    python scripts/validate_imports.py --skip <name>     # Skip specific service
"""

import argparse
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Project root
project_root = Path(__file__).parent.parent


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory."""
    python_files = []
    for path in directory.rglob("*.py"):
        # Skip __pycache__ and virtual environments
        if "__pycache__" not in str(path) and ".venv" not in str(path):
            python_files.append(path)
    return python_files


def extract_imports(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """
    Extract import statements from a Python file.
    
    Returns:
        Tuple of (absolute_imports, relative_imports)
    """
    absolute_imports: Set[str] = set()
    relative_imports: Set[str] = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    absolute_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level > 0:
                        # Relative import
                        relative_imports.add(f".{node.module}" if node.level == 1 else f"{'.' * node.level}{node.module}")
                    else:
                        # Absolute import
                        absolute_imports.add(node.module)
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}")
        return absolute_imports, relative_imports
    except Exception as e:
        print(f"❌ Error parsing {file_path}: {e}")
        return absolute_imports, relative_imports
    
    return absolute_imports, relative_imports


def validate_import(module_name: str, service_path: Path) -> Tuple[bool, str]:
    """
    Validate that an import can be resolved.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Try to find the module
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            # Check if it's a relative import that might work at runtime
            # (we can't fully validate relative imports statically)
            if module_name.startswith('.'):
                return True, "Relative import (validated at runtime)"
            return False, f"Module '{module_name}' not found"
        return True, "OK"
    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def validate_service_imports(service_path: Path, service_name: str) -> Dict[str, List[Tuple[str, bool, str]]]:
    """
    Validate all imports for a service.
    
    Returns:
        Dictionary mapping file paths to list of (import_name, success, error_message)
    """
    results: Dict[str, List[Tuple[str, bool, str]]] = {}
    
    python_files = find_python_files(service_path)
    
    if not python_files:
        print(f"⚠️  No Python files found in {service_path}")
        return results
    
    print(f"\n📦 Validating imports for {service_name} ({len(python_files)} files)...")
    
    for file_path in python_files:
        relative_path = file_path.relative_to(project_root)
        absolute_imports, relative_imports = extract_imports(file_path)
        
        file_results: List[Tuple[str, bool, str]] = []
        
        # Validate absolute imports
        for import_name in sorted(absolute_imports):
            # Skip standard library and common third-party packages
            if import_name.split('.')[0] in ['sys', 'os', 'json', 'logging', 'pathlib', 'typing', 'datetime', 'asyncio']:
                continue
            
            success, error_msg = validate_import(import_name, service_path)
            file_results.append((import_name, success, error_msg))
        
        # Note relative imports (can't fully validate statically)
        for import_name in relative_imports:
            file_results.append((import_name, True, "Relative import (validated at runtime)"))
        
        if file_results:
            results[str(relative_path)] = file_results
    
    return results


def print_validation_results(results: Dict[str, Dict[str, List[Tuple[str, bool, str]]]]) -> bool:
    """
    Print validation results and return whether validation passed.
    
    Returns:
        True if all imports valid, False otherwise
    """
    all_passed = True
    
    for service_name, service_results in results.items():
        service_passed = True
        failed_imports = []
        
        for file_path, imports in service_results.items():
            for import_name, success, error_msg in imports:
                if not success:
                    service_passed = False
                    all_passed = False
                    failed_imports.append((file_path, import_name, error_msg))
        
        if service_passed:
            print(f"✅ {service_name}: All imports valid")
        else:
            print(f"❌ {service_name}: Import errors found")
            for file_path, import_name, error_msg in failed_imports:
                print(f"   {file_path}: {import_name} - {error_msg}")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Validate imports for Python services (Epic 44.2)"
    )
    parser.add_argument(
        '--service',
        type=str,
        help='Validate specific service (e.g., device-intelligence-service)'
    )
    parser.add_argument(
        '--skip',
        type=str,
        action='append',
        help='Skip specific service (can be used multiple times)'
    )
    parser.add_argument(
        '--skip-import-check',
        action='store_true',
        help='Skip import validation (for testing)'
    )
    
    args = parser.parse_args()
    
    if args.skip_import_check:
        print("⚠️  Skipping import validation (--skip-import-check flag)")
        return 0
    
    services_dir = project_root / "services"
    
    if not services_dir.exists():
        print(f"❌ Services directory not found: {services_dir}")
        return 1
    
    # Find all services
    services = [d for d in services_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    if args.service:
        # Validate specific service
        service_path = services_dir / args.service
        if not service_path.exists():
            print(f"❌ Service not found: {args.service}")
            return 1
        services = [service_path]
    
    # Filter out skipped services
    skip_list = args.skip or []
    services = [s for s in services if s.name not in skip_list]
    
    if not services:
        print("⚠️  No services to validate")
        return 0
    
    print("="*80)
    print("IMPORT VALIDATION (Epic 44.2)")
    print("="*80)
    print(f"Validating {len(services)} service(s)...")
    
    all_results: Dict[str, Dict[str, List[Tuple[str, bool, str]]]] = {}
    
    for service_path in sorted(services):
        service_name = service_path.name
        service_results = validate_service_imports(service_path, service_name)
        if service_results:
            all_results[service_name] = service_results
    
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    all_passed = print_validation_results(all_results)
    
    if all_passed:
        print("\n✅ All imports validated successfully")
        return 0
    else:
        print("\n❌ Import validation failed - fix errors before deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())

