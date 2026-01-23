# Test Coverage (Simple Mode)

## Overview

Coverage-driven test generation: @simple-mode *test-coverage <file> [--target 80]. Finds gaps and generates tests for uncovered paths.

## Steps

1. If the user gave a file and optional --target, use them; otherwise ask or use defaults.
2. Run: @simple-mode *test-coverage <file> --target 80 (or user's target)
3. Execute: use coverage.xml/coverage.json; find low/uncovered modules; @tester *test for those paths. Report coverage change.
