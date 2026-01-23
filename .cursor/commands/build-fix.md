# Build Fix (Simple Mode)

## Overview

Fix build/compile errors: @simple-mode *build-fix "<build-output or description>". For Python, npm, tsc, cargo, etc. Distinct from *fix (runtime) and *fix-tests.

## Steps

1. If the user gave build output or a description, use it; otherwise ask them to paste or describe the error.
2. Run: @simple-mode *build-fix "<description or build output>"
3. Execute: parse errors → @debugger *debug → @implementer *refactor → re-run build to verify. Do not skip steps.
