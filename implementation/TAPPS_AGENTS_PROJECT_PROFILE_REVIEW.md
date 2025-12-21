# TappsCodingAgents Project Profile System Review

**Date:** January 2025  
**Focus:** How `tapps-agents` uses and creates `project-profile.yaml`

## Executive Summary

The TappsCodingAgents framework includes an automatic project profiling system that detects project characteristics (deployment type, tenancy, compliance, security level) and persists them to `.tapps-agents/project-profile.yaml`. This profile is used to provide context-aware expert guidance and ensure recommendations align with project constraints.

## Architecture Overview

### Core Components

1. **`ProjectProfile` Dataclass** (`tapps_agents/core/project_profile.py`)
   - Data model for project characteristics
   - Includes confidence scores and detection indicators
   - Provides `format_context()` method for expert prompt integration

2. **`ProjectProfileDetector` Class** (`tapps_agents/core/project_profile.py`)
   - Wraps `ProjectDetector` (from `tapps_agents/workflow/detector.py`)
   - Orchestrates detection of all profile characteristics
   - Aggregates results into `ProjectProfile` object

3. **`ProjectDetector` Class** (`tapps_agents/workflow/detector.py`)
   - Lower-level detection logic
   - File-based pattern matching
   - Provides methods: `detect_deployment_type()`, `detect_tenancy()`, `detect_compliance_requirements()`, `detect_security_level()`, `detect_user_scale()`

4. **Storage Functions** (`tapps_agents/core/project_profile.py`)
   - `save_project_profile()` - Saves profile to YAML
   - `load_project_profile()` - Loads profile from YAML

## Detection Process

### What Gets Detected

The system detects the following characteristics with confidence scores (0.0-1.0):

1. **Deployment Type** (`local`, `cloud`, `enterprise`)
   - **Enterprise indicators**: Kubernetes (`k8s/`, `kubernetes/`), Helm charts, compliance files, security files
   - **Cloud indicators**: Dockerfile, docker-compose.yml, serverless.yml, terraform/
   - **Local**: Default if no cloud/enterprise indicators found

2. **Tenancy Model** (`single-tenant`, `multi-tenant`)
   - Searches code for tenant patterns: `tenant_id`, `tenantId`, `tenant-id`, `tenant_uuid`, `tenant_context`, `multi_tenant`
   - Analyzes Python, JavaScript, TypeScript, Java, Go, Rust, C++, C# files
   - Skips files >1MB to avoid performance issues
   - Conservative: defaults to `single-tenant` if no patterns found

3. **Compliance Requirements** (GDPR, HIPAA, PCI, SOC2, ISO27001)
   - Searches file/directory names and paths for compliance keywords
   - Checks `compliance/` directory if present
   - Each requirement has independent confidence score

4. **Security Level** (`basic`, `standard`, `high`, `critical`)
   - Counts security-related files:
     - `.security`, `security.md`, `SECURITY.md`
     - `.bandit`, `.safety`, `.snyk`, `snyk.yml`
     - `.dependabot`, `dependabot.yml`
   - Thresholds: 3+ files = `high`, 2 files = `standard`, 1 file = `standard`, 0 files = `basic`

5. **User Scale** (`single-user`, `small-team`, `department`, `enterprise`)
   - Currently implemented but detection thresholds not fully specified in codebase review

### Detection Flow

```python
# 1. Initialize detector
detector = ProjectProfileDetector(project_root=Path.cwd())

# 2. Run detection (wraps ProjectDetector)
profile = detector.detect_profile()

# 3. Save to YAML
save_project_profile(profile, project_root=Path.cwd())
# Creates: .tapps-agents/project-profile.yaml
```

## File Format

### YAML Structure

```yaml
deployment_type: cloud                    # or "local" or "enterprise"
deployment_type_confidence: 0.9          # 0.0-1.0
deployment_type_indicators:               # Evidence that led to detection
  - has_dockerfile
  - has_docker_compose

tenancy: multi-tenant                    # or "single-tenant"
tenancy_confidence: 0.8
tenancy_indicators:
  - tenant_pattern_in_user_service.py

user_scale: enterprise                   # Optional
user_scale_confidence: 0.75
user_scale_indicators: []

compliance_requirements:                 # List of detected requirements
  - name: GDPR
    confidence: 0.9
    indicators:
      - gdpr_file_found
  - name: SOC2
    confidence: 0.7
    indicators:
      - soc2_pattern_in_paths

security_level: high                     # "basic", "standard", "high", "critical"
security_level_confidence: 0.8
security_level_indicators:
  - has_securitymd
  - has_.bandit
  - has_.snyk

detected_at: "2025-12-15T10:30:00Z"      # ISO 8601 timestamp
```

### Key Characteristics

- **File Location**: `.tapps-agents/project-profile.yaml` (hyphenated, not underscore)
- **Progressive Disclosure**: All fields optional (supports partial detection)
- **Confidence Scores**: Each detection includes confidence (0.0-1.0)
- **Indicators**: Tracks evidence that led to each detection (for explainability)

## When Profile is Created

### Automatic Creation

The profile is created automatically in two scenarios:

1. **During Workflow Execution** (`CursorWorkflowExecutor._profile_project()`)
   ```python
   # In CursorWorkflowExecutor.start()
   # 1. Try to load existing profile
   self.project_profile = load_project_profile(project_root=self.project_root)
   
   # 2. If no profile exists, detect and save
   if not self.project_profile:
       detector = ProjectProfileDetector(project_root=self.project_root)
       self.project_profile = detector.detect_profile()
       save_project_profile(profile=self.project_profile, project_root=self.project_root)
   ```

2. **During Project Initialization** (optional, via `tapps-agents init`)

### Manual Creation

Users can manually trigger detection:

```python
from pathlib import Path
from tapps_agents.core.project_profile import ProjectProfileDetector, save_project_profile

detector = ProjectProfileDetector(project_root=Path.cwd())
profile = detector.detect_profile()
path = save_project_profile(profile, project_root=Path.cwd())
```

## Where Profile is Used

### 1. Expert Registry (`tapps_agents/experts/expert_registry.py`)

```python
def _get_project_profile(self) -> ProjectProfile | None:
    """Get project profile (cached)."""
    if self._cached_profile is None:
        self._cached_profile = load_project_profile(project_root=self.project_root)
    return self._cached_profile
```

- Cached per registry instance
- Used to provide project context to expert consultations
- Includes high-confidence values (default min_confidence=0.7) in expert prompts

### 2. Workflow Executor (`tapps_agents/workflow/cursor_executor.py`)

- Loaded during workflow initialization
- Stored in `self.project_profile`
- Passed to Skills via workflow context
- Used for context-aware workflow execution

### 3. Suggestion Engine (`tapps_agents/workflow/suggestion_engine.py`)

```python
self.profile_detector = ProjectProfileDetector(project_root)

# During suggestion generation
try:
    project_profile = self.profile_detector.detect()  # Note: calls detect_profile()
except Exception as e:
    logger.warning(f"Failed to detect project profile: {e}")
    project_profile = None
```

- Used for context-aware workflow/agent/action suggestions
- Gracefully handles detection failures

### 4. Context Formatting for Expert Prompts

The `ProjectProfile.format_context()` method filters to high-confidence values:

```python
def format_context(self, min_confidence: float = 0.7) -> str:
    """Format profile as context string for expert prompts."""
    # Only includes values with confidence >= min_confidence
    # Returns formatted string like:
    # "Project Context:
    # - Deployment: cloud (confidence: 0.9)
    # - Security Level: high (confidence: 0.8)
    # - Compliance: GDPR, SOC2"
```

This context is injected into expert consultation prompts to ensure recommendations align with project characteristics.

## Integration Points

### Workflow Execution Flow

1. **Workflow Starts** → `CursorWorkflowExecutor.start()` called
2. **Profile Loaded** → `_profile_project()` called
   - Tries to load existing profile
   - If missing, detects and saves
3. **Profile Available** → Stored in `self.project_profile`
4. **Context Injection** → Profile passed to Skills via workflow context
5. **Expert Consultations** → Profile context included in prompts (via ExpertRegistry)

### Expert Consultation Flow

1. **Expert Query** → Agent needs expert guidance
2. **Registry Called** → `ExpertRegistry.consult()` invoked
3. **Profile Retrieved** → `_get_project_profile()` called (cached)
4. **Context Formatted** → `profile.format_context(min_confidence=0.7)` called
5. **Prompt Enhanced** → Context prepended to expert query
6. **Response Generated** → Expert provides context-aware guidance

## Code Locations

### Core Implementation

- **Profile Model**: `TappsCodingAgents/tapps_agents/core/project_profile.py`
  - `ProjectProfile` dataclass (lines 34-129)
  - `ProjectProfileDetector` class (lines 132-201)
  - `save_project_profile()` function (lines 204-226)
  - `load_project_profile()` function (lines 229-261)

### Detection Logic

- **ProjectDetector**: `TappsCodingAgents/tapps_agents/workflow/detector.py`
  - `detect_deployment_type()` (lines 147-232)
  - `detect_tenancy()` (lines 332-396)
  - `detect_compliance_requirements()` (lines 234-286)
  - `detect_security_level()` (lines 288-330)
  - `detect_user_scale()` (referenced but implementation details not fully visible in review)

### Usage Locations

- **Workflow Executor**: `TappsCodingAgents/tapps_agents/workflow/cursor_executor.py` (lines 165-179)
- **Expert Registry**: `TappsCodingAgents/tapps_agents/experts/expert_registry.py` (lines 87-96)
- **Suggestion Engine**: `TappsCodingAgents/tapps_agents/workflow/suggestion_engine.py` (line 145)

## Design Patterns

### 1. Lazy Loading Pattern

Profile is loaded on-demand and cached:
- `ExpertRegistry` caches profile in `self._cached_profile`
- Loaded only when needed (not during initialization)
- Avoids unnecessary file I/O

### 2. Progressive Enhancement Pattern

All profile fields are optional:
- Supports partial detection (some characteristics detected, others not)
- Allows graceful degradation if detection fails
- User can manually override detected values

### 3. Confidence-Based Filtering

Only high-confidence values are used:
- Default threshold: 0.7 (70% confidence)
- Low-confidence detections are stored but not used in prompts
- Prevents incorrect assumptions from weak indicators

### 4. Evidence Tracking

Each detection includes indicators:
- Explains why a characteristic was detected
- Useful for debugging and user understanding
- Allows manual verification of detection accuracy

## Example: Real Profile from TappsCodingAgents Framework

```yaml
# From TappsCodingAgents/.tapps-agents/project-profile.yaml
deployment_type: local
deployment_type_confidence: 0.5
deployment_type_indicators:
  - has_security
  - no_cloud_infrastructure

tenancy: single-tenant
tenancy_confidence: 0.7
tenancy_indicators:
  - no_tenant_patterns_found

user_scale: null
user_scale_confidence: 0.0
user_scale_indicators: []

compliance_requirements:
  - name: GDPR
    confidence: 0.3  # Low confidence - likely false positive
    indicators:
      - gdpr_pattern_in_paths
  - name: HIPAA
    confidence: 0.3
    indicators:
      - hipaa_pattern_in_paths
  - name: PCI
    confidence: 0.3
    indicators:
      - pci_pattern_in_paths

security_level: standard
security_level_confidence: 0.7
security_level_indicators:
  - has_securitymd
  - has_SECURITYmd

detected_at: '2025-12-13T22:23:13.003383Z'
```

**Analysis:**
- Deployment detected as "local" (low confidence: 0.5)
- Tenancy detected as "single-tenant" (confidence: 0.7)
- Compliance detections are low-confidence (0.3) - likely false positives from pattern matching
- Security level: "standard" (2 security files found)

## Manual Override Capability

Users can manually edit `.tapps-agents/project-profile.yaml` to override incorrect detections:

```yaml
# Manual override example
deployment_type: cloud  # Override detected "local"
deployment_type_confidence: 1.0  # Manual override has full confidence
security_level: critical  # Increase from "standard"
```

**Note:** Manual edits are preserved and not overwritten by automatic detection (detection only happens if file doesn't exist).

## Limitations & Observations

### 1. Detection Accuracy

- **File-based pattern matching** can produce false positives:
  - Example: Compliance keywords in documentation paths may trigger compliance detection
  - Low-confidence detections (like 0.3) are filtered out in context formatting, but still stored

### 2. Performance Considerations

- **Tenancy detection** scans all code files (with 1MB file size limit)
- Could be slow on large codebases
- Uses file extension filtering to limit scope

### 3. User Scale Detection

- Implementation exists but detection logic/details not fully visible in codebase review
- May need additional refinement

### 4. Profile Regeneration

- Currently only regenerates if file doesn't exist
- No automatic refresh/update mechanism
- User must manually delete file to trigger re-detection

### 5. Validation

- No schema validation for manually edited YAML
- Relies on `ProjectProfile.from_dict()` error handling
- Invalid YAML silently fails (returns None)

## Best Practices for Using Project Profile

### For Framework Developers

1. **Always check if profile exists** before using it:
   ```python
   profile = load_project_profile()
   if profile:
       context = profile.format_context()
   ```

2. **Use confidence filtering** when including in prompts:
   ```python
   context = profile.format_context(min_confidence=0.7)  # Default
   ```

3. **Handle detection failures gracefully**:
   ```python
   try:
       profile = detector.detect_profile()
   except Exception as e:
       logger.warning(f"Profile detection failed: {e}")
       profile = None  # Continue without profile
   ```

### For Framework Users

1. **Review after first workflow run** - Check `.tapps-agents/project-profile.yaml`
2. **Manually override incorrect detections** - Edit YAML directly
3. **Commit to version control** - Share profile with team for consistency
4. **Regenerate when needed** - Delete file to trigger re-detection after major changes

## Future Enhancements (Planned)

Based on documentation references:

1. **SDLC Quality Engine Integration**
   - Load appropriate validators based on detected characteristics
   - Adapt validation checks to security level and compliance requirements

2. **Dynamic Expert Engine Integration**
   - Pre-load relevant expert guidance based on profile
   - Route to appropriate experts based on project characteristics

3. **Profile Refresh Mechanism**
   - Automatic re-detection on project changes
   - Incremental updates (detect only changed characteristics)

## Conclusion

The project profile system provides a robust foundation for context-aware recommendations in TappsCodingAgents. Key strengths:

✅ **Automatic detection** - No manual configuration required  
✅ **Confidence scoring** - Filters low-confidence detections  
✅ **Evidence tracking** - Indicators explain detection rationale  
✅ **Manual override** - Users can correct incorrect detections  
✅ **Graceful degradation** - Works even with partial detection  

The system is well-integrated into the workflow execution and expert consultation flows, ensuring that recommendations align with project characteristics automatically.

