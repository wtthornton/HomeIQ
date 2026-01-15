"""
CLI tool for validating automation specs

Epic C3: Lint + validate locally, render execution plan (dry run)
"""

import argparse
import json
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from homeiq_automation.spec_validator import SpecValidator


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Validate HomeIQ Automation Spec"
    )
    parser.add_argument(
        "spec_file",
        type=Path,
        help="Path to spec file (JSON or YAML)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render execution plan (dry run) - not yet implemented"
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    if not args.spec_file.exists():
        print(f"Error: File not found: {args.spec_file}", file=sys.stderr)
        sys.exit(1)
    
    # Validate spec
    validator = SpecValidator()
    is_valid, errors = validator.validate_file(args.spec_file)
    
    # Output results
    if args.format == "json":
        output = {
            "valid": is_valid,
            "errors": errors,
            "file": str(args.spec_file)
        }
        print(json.dumps(output, indent=2))
    else:
        if is_valid:
            print(f"✓ Spec is valid: {args.spec_file}")
        else:
            print(f"✗ Spec validation failed: {args.spec_file}")
            print(validator.format_errors(errors))
    
    # Exit with error code if invalid
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
