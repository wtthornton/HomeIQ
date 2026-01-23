# TDD (Simple Mode)

## Overview

Run the TDD workflow: @simple-mode *tdd "<description>" or *tdd {file}. Red-Green-Refactor with coverage ≥80%.

## Steps

1. If the user gave a file or description, use it; otherwise ask.
2. Run: @simple-mode *tdd "<description>" or @simple-mode *tdd {file}
3. Execute: define interfaces → failing tests (RED) → minimal code (GREEN) → refactor (IMPROVE) → @tester *test for coverage. Do not skip steps.
