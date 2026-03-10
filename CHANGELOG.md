# Changelog

## [Unreleased] - 2026-03-10

### Added

- **streaming dashboard for auto-bugfix pipeline (E1+E2+E3)** (1c8981b) - Bill Thornton
- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton

### Fixed

- **add --verbose flag required for stream-json output format** (93e53ba) - Bill Thornton
- **replace System.Diagnostics.Process with native PS piping** (51672b7) - Bill Thornton
- **resolve claude CLI full path in stream parser** (28e2975) - Bill Thornton
- **use stdin piping + join output for claude --print in auto-bugfix.ps1** (35f25d3) - Bill Thornton
- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton


### Added

- **streaming dashboard for auto-bugfix pipeline (E1+E2+E3)** (1c8981b) - Bill Thornton
- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton

### Fixed

- **replace System.Diagnostics.Process with native PS piping** (51672b7) - Bill Thornton
- **resolve claude CLI full path in stream parser** (28e2975) - Bill Thornton
- **use stdin piping + join output for claude --print in auto-bugfix.ps1** (35f25d3) - Bill Thornton
- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton


### Added

- **streaming dashboard for auto-bugfix pipeline (E1+E2+E3)** (1c8981b) - Bill Thornton
- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton

### Fixed

- **resolve claude CLI full path in stream parser** (28e2975) - Bill Thornton
- **use stdin piping + join output for claude --print in auto-bugfix.ps1** (35f25d3) - Bill Thornton
- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton


### Added

- **streaming dashboard for auto-bugfix pipeline (E1+E2+E3)** (1c8981b) - Bill Thornton
- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton

### Fixed

- **use stdin piping + join output for claude --print in auto-bugfix.ps1** (35f25d3) - Bill Thornton
- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton

### Fixed

- **use stdin piping + join output for claude --print in auto-bugfix.ps1** (35f25d3) - Bill Thornton
- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton

### Fixed

- **use PowerShell argument splatting for claude --print calls** (2af2d02) - Bill Thornton
- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton

### Fixed

- **use temp file for prompt passing in auto-bugfix.ps1** (1b44ef4) - Bill Thornton
- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton

### Fixed

- **pipe prompts via stdin to claude --print in auto-bugfix.ps1** (0d66146) - Bill Thornton
- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton

### Fixed

- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton


### Added

- **auto-fix infrastructure — pre-commit, lib validation, CI hardening** (5e361e7) - Bill Thornton
- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton

### Fixed

- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton


### Added

- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton

### Fixed

- **Docker deployment — add homeiq-memory lib + resolve port conflicts** (71b3f31) - Bill Thornton
- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton


### Added

- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton

### Fixed

- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton


### Added

- **Epic 41 — Memory Brain quality tuning (7 stories)** (2837a2a) - Bill Thornton
- **Epic 40 — pattern detection ML upgrade (8 stories)** (38b7b4d) - Bill Thornton
- **Epic 39 — enable React Compiler for both frontend apps** (7f8b1df) - Bill Thornton
- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton

### Fixed

- **test infrastructure improvements and model refactoring** (ea7656c) - Bill Thornton
- **resolve memory brain migration enum mismatch + configurable pattern coordinates** (2d3e420) - Bill Thornton
- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton


### Added

- **complete Sprint 8 — pattern detection expansion + ML upgrades** (d32ecb2) - Bill Thornton
- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton

### Fixed

- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton


### Added

- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton

### Fixed

- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton


### Added

- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton

### Fixed

- **use TappsMCP tools for bug scanning instead of pure LLM guessing** (6bdc94f) - Bill Thornton
- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton


### Added

- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton

### Fixed

- **dashboard now embeds state in HTML (fixes Chrome file:// CORS)** (e59bd86) - Bill Thornton
- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton


### Added

- **worktree-based parallel auto-bugfix with shared picker script** (705045c) - Bill Thornton
- **feat(epic-37): add anomaly and duration pattern detectors** (0bbaaf5) - Bill Thornton
- **add worktree-based parallel auto-bugfix scanning** (3aec513) - Bill Thornton
- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton

### Fixed

- **use temp file for python script in parallel orchestrator (PS5 compat)** (0c1d43c) - Bill Thornton
- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton


### Added

- **feat(story-37.1): add SequencePatternDetector to pattern-analyzer** (4cd48f8) - Bill Thornton
- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton

### Fixed

- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton


### Added

- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton

### Fixed

- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton


### Added

- **feat(story-38.3): Upgrade sentence-transformers to 5.x across all ML services** (8782a2f) - Bill Thornton
- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton

### Fixed

- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton


### Added

- **feat(story-38.2): Complete sentence-transformers upgrade assessment - UPGRADE SAFE** (d9f6dee) - Bill Thornton
- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton

### Fixed

- **resolve function-before-definition errors in rotate mode** (beb5a80) - Bill Thornton
- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton


### Added

- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Fixed

- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton


### Added

- **feat(story-38.1): Add embedding compatibility test infrastructure** (c7ca9db) - Bill Thornton
- **add rotating scan units for systematic codebase coverage** (6c62499) - Bill Thornton
- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Fixed

- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Add Sprint 8 epics - Pattern Detection (10 stories) + ML Upgrades (8 stories)** (65afe1c) - Bill Thornton
- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton

### Fixed

- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton

### Fixed

- **Correct ai-automation-ui health check port (80 -> 8080)** (ff02b5d) - Bill Thornton
- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton

### Fixed

- **Resolve voice-gateway build failure (Python 3.12 compat)** (3153edd) - Bill Thornton
- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Implement Memory Brain - Sprint 7 complete (Epics 29-35)** (463ac53) - Bill Thornton
- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton

### Fixed

- **Resolve 4 degraded service health checks** (35907d0) - Bill Thornton
- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton

### Fixed

- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **Complete security hardening + quality gate CI + ML upgrades** (4109be8) - Bill Thornton
- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton

### Fixed

- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton


### Added

- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton

### Fixed

- **Windows browser open + ps1 submodule isolation parity** (577d156) - Bill Thornton
- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton


### Added

- **add auto-bugfix script with TappsMCP validation and feedback loop** (8e2bc8c) - Bill Thornton
- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton

### Fixed

- **auto-bugfix submodule isolation + dashboard & chain mode features** (8e06d81) - Bill Thornton
- **auto-fix 1 bugs across codebase** (d835b5b) - Bill Thornton
- **pass --mcp-config to headless claude for TappsMCP access** (596c727) - Bill Thornton
- **ignore submodule changes in auto-bugfix dirty check** (4164cf5) - Bill Thornton
- **fix(data-api): resolve datetime tz-naive/aware mismatch crashing /api/devices** (561c8cd) - Bill Thornton
- **10 runtime bugs across 8 services (ZeroDivisionError, IndexError, resource leaks)** (7163a45) - Bill Thornton
- **ingestion InfluxDB auth, stats endpoint routing, dark mode card styling** (95f3a6d) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton


### Added

- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(data-api): datetime tz-aware/naive mismatch in compute_device_status() causing 500 on /api/devices** — Health dashboard showed 0 Devices / 0 Entities; replaced 37 naive `datetime.now()` with `datetime.now(UTC)`
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton


### Added

- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton


### Added

- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **Epic 37 — Intent-based E2E test rewrite (55 files, 189 tests)** (b8fe047) - Bill Thornton
- **blueprint port refs, health monitoring, schema init, Docker tooling** (1c0bb5f) - Bill Thornton
- **create missing automation schema tables (suggestions, plans, deployments)** (793ca15) - Bill Thornton
- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton


### Added

- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **Epic 36 — E2E Playwright test remediation (36 failures → 0, 160/167 pass)** (d46ef41) - Bill Thornton
- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton


### Added

- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **resolve 4 service failures — ai-core crash loop, ai-automation config, calendar deps, InfluxDB auth** (c090f11) - Bill Thornton
- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton


### Added

- **Sprints 5-6 — Sapphire-inspired HA enhancements (Epics 25-28, 22 stories)** (0cbb537) - Bill Thornton
- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton


### Added

- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton

### Changed

- **Sprint 4 Wave 4 — final 2 services migrated (ha-simulator + observability)** (ca40d3c) - Bill Thornton
- **Sprint 4 Wave 3 — 10 service migrations (aiohttp conversions + Tier 1)** (c06cd2f) - Bill Thornton
- **Sprint 4 Wave 2 — 14 service migrations (ML, automation, energy, collectors)** (14755a5) - Bill Thornton
- **Sprint 4 Wave 1 — frontend upgrades + 12 service migrations** (9403372) - Bill Thornton
- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(deploy): Epic 8 Phase 5 production deployment — 52/53 services healthy** (bfeed7e) - Bill Thornton
- **fix(docker): remove tailwind.config.js COPY from frontend Dockerfiles** (c70ebe0) - Bill Thornton
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton


### Added

- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton
- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton

### Changed

- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (e99e356) - Bill Thornton
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton


### Sprint 3: Docker Breakout (Epics 21-24) — COMPLETE

- **refactor(infra): Sprint 3 Docker breakout — Epics 21-24 complete** (294b1f1) — 38 files, 21 stories
  - Epic 21: Per-domain Docker isolation — `name:` directives on 9 compose files, container prefix fixes, ensure-network scripts, build context alignment
  - Epic 22: Volume decoupling — `homeiq_logs`, `ai_automation_data`, `ai_automation_models` given single owners with external refs
  - Epic 23: Dockerfile hardening — 2 root-user fixes, 4 healthchecks, 3 UID standardization, 3 multi-stage conversions, install order fixes, CRLF + .gitattributes
  - Epic 24: Deployment tooling — `domain.sh`, `start-stack.sh`, `ensure-network.sh` (+ PowerShell), `deploy.sh` archived

### Added

- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton
- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton

### Changed

- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (7aa819b) - Bill Thornton
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (16e8e93) - Bill Thornton
- **refactor(core-platform): decompose websocket-ingestion & data-api for quality gate 80+ (Stories 17.2, 17.3)** (c4ad4d2) - Bill Thornton
- **refactor(admin-api): decompose main.py for quality gate 80+ (Story 17.1)** (367da52) - Bill Thornton
- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (41f3d83) - Bill Thornton
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (c1b5e11) - Bill Thornton
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (96f9125) - Bill Thornton
- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (398e074) - Bill Thornton
- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton

### Sprint 2: Quality Baseline Remediation (Epics 16-20) — COMPLETE

- **fix(lint): resolve I001, F401, ARG001/ARG002 across domains/ and libs/** (39b5762) — 653 files, 1571 violations fixed
- **fix(lint): resolve UP017, UP041, DTZ003 across 215 Python files** (6b9b27f) — datetime.UTC modernization, TimeoutError alias
- **fix(lint): suppress S104 bind-all warnings in remaining Docker services** (aa8ad41) — 35 intentional Docker binds suppressed
- **fix(quality): remediate 5 services to pass TAPPS quality gate (Epic 19.4-19.7)** (881f27c) — ai-core, openvino, ha-ai-agent, automation-linter, automation-trace
- **refactor(admin-api): decompose main.py into 7 modules for strict quality gate 80+** (adacd52) — 67.2 → 80.34
- **refactor(core-platform): decompose websocket-ingestion & data-api for strict quality gate 80+** (01dfb8c) — ws 70.9→84.94, data-api 72.1→84.9
- **refactor(data-collectors): Epic 18 quality remediation — all 8 services pass 70+ gate** (95c6bff) — 0/8 → 8/8 pass rate
- **refactor(epic-19): remediate 3 lowest-scoring services to pass 70+ quality gate** (cc7aa29) — activity-writer 51.9→81.9, ha-setup 54.4→77.0, ml-service 57.1→74.9

### Added

- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton
- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton

### Changed

- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(scripts): verify-deployment use correct alerts URL and allow 401** (168e345) - Bill Thornton
- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(data-api,device-intelligence,ai-automation-ui): devices endpoints, team tracker API, and UI updates** (24e3821) - Bill Thornton
- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton

### Changed

- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton

### Changed

- **refactor(openai): migrate from chat.completions to responses API** (8bc7fd5) - Bill Thornton

### Fixed

- **fix(calendar-service): pass full URL to InfluxDBClient3 host param** (7465a72) - Bill Thornton
- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton

### Fixed

- **fix(carbon-intensity): align compose InfluxDB defaults with actual instance** (c01270f) - Bill Thornton
- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton

### Fixed

- **fix(carbon-intensity): pass full URL to InfluxDBClient3 (fixes HTTPS/443 default)** (214c5f3) - Bill Thornton
- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton

### Fixed

- **fix(carbon-intensity): fix 6 bugs, clean dead fields, upgrade tests to WattTime v3** (74cb87b) - Bill Thornton
- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton
- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton

### Fixed

- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and update 7 stale docs** (55b1eee) - Bill Thornton
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton
- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton
- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a46) - Bill Thornton

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton


### Added

- **feat(ai-automation-ui): Epic 3 — quality, architecture, and test improvements (8 stories)** (3889209) - Bill Thornton
- **shared library standardization — Epics 12, 13, 14 (10 stories)** (9316602) - Bill Thornton
- **feat(health-dashboard): Epic 2 — quality, performance, and test coverage improvements** (d7240b9) - Bill Thornton
- **implement Epic 7 feature gaps across 4 services (6 stories)** (162ce8b) - Bill Thornton
- **feat(health-dashboard): Epic 11 browser review — status consistency, log pagination, UX improvements** (f406bfc) - Bill Thornton
- **feat(epic-6): ML library upgrades, fix skipped tests, implement test stubs** (0f0bbcf) - Bill Thornton
- **add Epic 8 production deployment scripts and documentation** (2bd9da9) - Bill Thornton
- **feat(ai-automation-ui): Epic 10 Stories 3-4 UX and accessibility improvements** (1030a80) - Bill Thornton
- **standardize Docker builds, migrate JSON to JSONB, and add CI/docs tooling** (fe69c9f) - Bill Thornton
- **standardize PostgreSQL initialization with DatabaseManager across all 13 services** (d93bcac) - Bill Thornton
- **TAPPS quality gate fixes + browser review critical stories (6 stories, 52 files)** (c224571) - Bill Thornton
- **complete SQLite removal — PostgreSQL is sole database (Epic 0)** (6c5480b) - Bill Thornton
- **Phase 4.7 — cross-group service-to-service Bearer token auth** (b99aef7) - Bill Thornton
- **Phase 4.6 — group-level health dashboard with color-coded aggregation** (2af65d4) - Bill Thornton
- **Phase 4.5 — AI fallback with CircuitBreaker for ml-engine degradation** (d885f05) - Bill Thornton
- **Phase 4b frontend redesign — teal palette, sidebar nav, app consolidation** (9c170ff) - Bill Thornton
- **infra fixes, library bumps, and proactive-agent RAG integration** (74ee779) - Bill Thornton
- **implement 5 service stubs across 4 domains** (c0c7919) - Bill Thornton
- **implement 6 stub services and wire persistent eval sinks** (88a4a31) - Bill Thornton
- **operational readiness — Alembic, monitoring, CI, backups, E2E, runbooks** (41c61dd) - Bill Thornton
- **SQLite to PostgreSQL migration + library version standardization** (8508f97) - Bill Thornton
- **Phase 1 dependency updates, Dockerfile modernization, and documentation refresh** (7066ce7) - Bill Thornton
- **complete domain architecture restructuring (Epics 1-4)** (d47f7c0) - Bill Thornton
- **service groups decomposition + cross-group resilience rollout** (6e9cf95) - Bill Thornton
- **DatabaseManager standardization across all 13 PostgreSQL services** — new `DatabaseManager` class in homeiq-data shared library replaces 4 different database initialization patterns with a single, standardized approach. `initialize()` never raises, enabling graceful degradation. Added `validate_database_url()` to prevent empty-string URLs from reaching SQLAlchemy. 14 database modules + 12 lifespan handlers updated. Fixes proactive-agent-service crash when `POSTGRES_URL` is unset.
- **508 accessibility compliance for health dashboard status indicators** — replaced color-only dots with distinct SVG icon shapes (CheckCircle, AlertTriangle, Octagon/stop-sign, CircleMinus), added ARIA roles/labels, replaced emoji indicators in ConnectionStatusIndicator with Lucide icons
- **Phase 3 readiness report, Story 6.5 cutover plan, Phase 5 deployment plan, quality audit** (b7d0c19)
- **upgrade LLM/ML model stack — OpenAI SDK 2.x, gpt-5.2-codex, library alignment** (b62f1a6)
- **feat(activity-recognition): Phase 1+2 integration and quality improvements** (78f19c4)
- **feat(ai-automation-service-new): separate plan (gpt-4o-mini) and YAML (Codex) models** (1bb834b)
- **feat(patterns): Pattern Intelligence epic — scoring, tuning & feedback loop** (35dccf6)
- **feat(agent): data-api Bearer auth, multi-sensor motion context, docs update** (a30197f)
- **feat(automation): multi-sensor OR/AND motion trigger + gpt-5-mini compat** (b929ef5)

### Fixed

- **fix(infrastructure): correct 10 health check ports, 3 live service port bugs, and 7 stale docs** — admin-api health_endpoints.py had 10 wrong container ports causing false-unhealthy for ML Engine, Pattern Analysis, Device Management, and Energy Analytics groups; 3 config.py defaults pointed device-intelligence-service to wrong ports (8023/8028 instead of 8019); 7 documentation files updated to match actual Docker compose port mappings
- **fix(tests): verification scripts and smoke tests without false-positive fallbacks** (2c15e58) - Bill Thornton
- **fix(health-dashboard): Vite process.env, crawl spec, smoke test resilience** (a9a9be4) - Bill Thornton
- **fix(ai-automation-ui): E2E chat tests - add data-testid, fix selectors, doc** (bb578b2) - Bill Thornton
- **fix(ai-automation-ui): fix light mode, rebrand to HomeIQ, align teal design system** (27ce940) - Bill Thornton
- **resolve 3 degraded service health checks post-deployment** (1883ffd) - Bill Thornton
- **post-blitz stabilization — React 19, pytest fixes, ruff cleanup, converter bug** (6830bfa) - Bill Thornton
- **fix(ai-automation-ui): add missing api-client module and fix test assertions** (7ad7687) - Bill Thornton
- **resolve observability dashboard critical bugs and add test coverage (Epic 4)** (8eb4a14) - Bill Thornton
- **resolve 3 deployment issues in DatabaseManager rollout** (e7ec2a2) - Bill Thornton
- **update E2E test to accept degraded status from api-automation-edge** (a525412) - Bill Thornton
- **508-compliant status indicators + resolve 12 false health statuses** (3b40295) - Bill Thornton
- **eliminate false-positive health status for data sources** (e5d3cb6) - Bill Thornton
- **resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) - Bill Thornton
- **resolve 5 blocking security/quality findings + add deployment planning docs** (9d570d2) - Bill Thornton
- **wire HealthEndpointManager into simple_main.py for /health/groups** (6991a46) - Bill Thornton
- **add missing logging_config module to homeiq-data package** (e26008a) - Bill Thornton
- **switch Claude Code hooks from .sh to .ps1 for Windows compatibility** (06dfa52) - Bill Thornton
- **remove 20 files committed with literal ${workspaceFolder} path prefix** (850d47a) - Bill Thornton
- **update pytest-asyncio config for explicit loop scope across all services** (141da0d) - Bill Thornton
- **resolve data-api startup and legacy shared.* imports (Phase 1 complete)** (296ce95) - Bill Thornton
- **resolve pre-existing e2e test failures** (d1d0921) - Bill Thornton
- **OTel mock fallbacks, blueprint-suggestion Docker context, resilience E2E tests** (7d6c3e9) - Bill Thornton
- **resolve 3 deployment bugs in resilience startup and health probes** (e20679) - Bill Thornton
- **proactive-agent-service crash when POSTGRES_URL is unset** — empty string passed to SQLAlchemy caused service to never start. Now handled by DatabaseManager graceful degradation.
- **health dashboard: 10 services showing false-positive RED** — changed health endpoints to return HTTP 200 with `"status": "degraded"` instead of HTTP 503 for expected conditions (missing HA config, unavailable DB, downstream services down)
- **health dashboard: 2 services showing false-positive GREEN** — air-quality-service now reports "degraded" when 0% fetch success rate; calendar-service no longer returns 503 for "no_calendars_found"
- **health dashboard: weather-api and carbon-intensity-service incorrectly shown as stopped** — removed hardcoded STOPPED status in admin-api mock container data; added Compose label fallback for service name matching
- **fix(ha-ai-agent): inject entity inventory, fix device-intel auth, switch to gpt-4.1** (9d9c397)
- **resolve 5 deployment bugs across data-api, ha-ai-agent, ai-pattern, smart-meter** (e4e2c8e)
- **platform-wide code quality review — 6,500+ lint fixes across 46 services** (9aae7e5)
- **fix(ai-automation-service-new): tests, schema, and OpenAI default model** (4f92f92)
- **YAML tests, deployment router, entity extraction, and validator** (34f6f50)
- **Fix activity-recognition bugs; ai-automation-service updates** (a8bbcf9)
- **fix(activity-recognition): quality gate fixes, tests, and refactors** (be3f154)
- **fix(activity-recognition): thread safety, ONNX probs shape, checkpoint load, sequences, healthcheck** (7e4a019)
- **fix(ai-automation-service-new): fix null-safe .get() usage and test imports** (624419d)
- **fix(ai-automation-service-new): resolve 30+ ruff/lint bugs and syntax errors** (998501c)
- **fix(ai-automation-service-new): resolve 40+ lint, security, and exception-handling issues** (e0099bb)
- **resolve 10 bugs via TappsMCP and misc updates** (93ab49f)
- **fix(enhancement): GPT-5.2-Codex temperature compatibility + preview modal** (b6aeb25)
- **fix(automation-trace): InfluxDB v2 compat + batch data-api POSTs** (3cb5415)
- **fix: Ideas page suggestions API failure (browser-review Story 1)** — 10s fetch timeout via AbortController in api.ts, auth error classification (401/403), exponential backoff retries, error/empty state UI
- **fix: Overview KPI perpetual loading (browser-review Story 1)** — `fetchWithTimeout(10s)` in useHealth/useStatistics hooks, `KPIValue` component with 3 states (loading/unavailable/stale)
- **fix: Explore page devices API and mobile nav (browser-review Story 2)** — Demo mode banner with retry in Discovery.tsx, loading skeleton, dropdown disabled with spinner in DeviceExplorer

### Major

- **feat: complete SQLite removal — PostgreSQL is sole database (Epic 0)** (81a233d) — 311 files changed across all 10 stories: removed SQLite from 11 compose files, 12 database init files, 11 config files, 19 requirements files, 13 Alembic configs, 12 test fixtures, CI workflows, 100+ docs; deleted 24 SQLite-specific scripts; archived migration tools

### Security

- **security: harden all 3 frontends (Epic 1, Stories 1-6)** (e5364de) - Bill Thornton
- **fix: Logs tab secret sanitization (browser-review Story 2)** — Added `sanitizeLogMessage()` with 7 regex patterns to redact Bearer tokens, API keys, passwords, connection strings, and secrets in LogTailViewer; 11 new tests
- **fix: resolve Bandit security findings (TAPPS Story 2)** — B104 nosec for Docker bind-all in blueprint-suggestion-service and energy-correlator; B112 narrowed bare except to specific types in correlator.py
- **fix: resolve 5 blocking security/quality findings** (b7d0c19) — SQL injection prevention in `database_pool.py`, timing-safe auth token comparison, CORS credentials bypass guard in admin-api, race condition lock on shared engine creation, timezone-aware datetimes in data-api and admin-api

### Testing

- **fix: resolve 119 E2E test failures after frontend sidebar redesign** (c27e453) — Updated all Playwright E2E tests for Phase 4b sidebar navigation: page objects, route mappings, removed aria-selected assertions, deleted obsolete test files, added API timeout handling; 234 passed, 0 failed
- **fix: eliminate false-positive health status for data sources** (833be42) — Admin-api now overrides "healthy" when credentials are missing or all fetches failed; calendar-service tracks discovered vs configured calendars

### Improved

- **refactor: raise converter.py and yaml_transformer.py quality scores (TAPPS Story 1)** — converter.py MI 64→71 (CC 14→7 via data-driven field mapping), yaml_transformer.py MI 68→70 (CC 10→6 via strategy dispatch dict)

### Chores

- **miscellaneous fixes — compose configs, lint cleanup, CI updates** (4a27d78)
- **Phase 3 ML prerequisites, rollback script, and planning updates** (06c028c)
- **cross-group integration test workflow (Step 3.5)** (98e6609)
- **align ML library version pins and fix import ordering** (247d12f)
- **untrack runtime files and update .gitignore** (cf20454)
