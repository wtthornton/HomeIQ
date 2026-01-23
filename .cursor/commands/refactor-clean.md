# Refactor Clean (Simple Mode)

## Overview

Mechanical cleanup: @simple-mode *refactor-clean {file}. Removes unused imports, dead code, duplication. Use *refactor for larger design changes.

## Steps

1. If the user gave a file, use it; otherwise ask.
2. Run: @simple-mode *refactor-clean {file}
3. Execute: @reviewer *duplication and/or Ruff; @implementer *refactor for cleanup. Report changes.
