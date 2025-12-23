# TappsCodingAgents Upgrade Plan: v2.4.1 → v2.4.3

**Date:** January 2026  
**Current Version:** 2.4.3 ✅ (Already at Latest)  
**Target Version:** 2.4.3 (Latest Release - Dec 23, 2025)  
**Status:** ✅ **COMPLETE - Already Upgraded**

## Executive Summary

**UPDATE:** After review, TappsCodingAgents is already at v2.4.3 (latest version). This document is preserved for reference. See `TAPPS_AGENTS_UPGRADE_AND_CLEANUP_REPORT.md` for current status.

This plan outlined the upgrade of TappsCodingAgents from v2.4.1 to v2.4.3, including cleanup of old versions and verification of the HomeIQ codebase.

### Key Changes in v2.4.3

Based on git log analysis (`v2.4.1..v2.4.3`):
1. **Command Reference Updates** - Comprehensive command reference improvements
2. **Test and Validator Improvements** - Additional test coverage and validator enhancements
3. **Bug Fix** - Fixed TypeError in reviewer score_validator when processing scores with non-numeric keys
4. **Version Bump** - Updated to 2.4.3

## Current Installation Status

### Installation Details
- **Installed Version:** 2.4.3 ✅ (Already at Latest)
- **Installation Type:** Editable install (`pip install -e`)
- **Installation Location:** `C:\Users\tappt\AppData\Roaming\Python\Python313\site-packages`
- **Source Location:** `C:\cursor\HomeIQ\TappsCodingAgents` (editable project location)
- **Git Status:** Detached HEAD at v2.4.3 ✅
- **Git Remote:** `https://github.com/wtthornton/TappsCodingAgents.git`

### Configuration
- **Configuration Directory:** `.tapps-agents/`
- **Config File:** `.tapps-agents/config.yaml`
- **Knowledge Base:** `.tapps-agents/kb/context7-cache/`
- **Sessions:** 23+ enhancement sessions in `.tapps-agents/sessions/`
- **Customizations:** `.tapps-agents/customizations/`

### Dependencies
- No references to `tapps-agents` in HomeIQ requirements files (good - not a dependency)
- Framework is used as a development tool, not a runtime dependency

## Upgrade Strategy

### Option 1: Git-Based Upgrade (Recommended)
Since TappsCodingAgents is installed as an editable package from a local git repository, we'll:
1. Update the git repository to v2.4.3
2. Reinstall the package to pick up changes
3. Verify the upgrade

### Option 2: PyPI-Based Upgrade (Alternative)
If git-based upgrade fails:
1. Uninstall current editable install
2. Install from PyPI: `pip install tapps-agents==2.4.3`
3. Note: This would lose the editable install benefit

**Recommendation:** Use Option 1 (Git-based) to maintain editable install.

## Step-by-Step Upgrade Plan

### Phase 1: Pre-Upgrade Backup and Verification

#### Step 1.1: Backup Current Configuration
```powershell
# Create backup directory
New-Item -ItemType Directory -Path "implementation/backups/tapps-agents-2.4.1" -Force

# Backup configuration
Copy-Item -Path ".tapps-agents/config.yaml" -Destination "implementation/backups/tapps-agents-2.4.1/config.yaml"
Copy-Item -Path ".tapps-agents/experts.yaml" -Destination "implementation/backups/tapps-agents-2.4.1/experts.yaml"
Copy-Item -Path ".tapps-agents/domains.md" -Destination "implementation/backups/tapps-agents-2.4.1/domains.md"

# Backup customizations if any
if (Test-Path ".tapps-agents/customizations") {
    Copy-Item -Path ".tapps-agents/customizations" -Destination "implementation/backups/tapps-agents-2.4.1/customizations" -Recurse
}
```

#### Step 1.2: Verify Current Installation
```powershell
# Check current version
python -m pip show tapps-agents

# Test current functionality
python -m tapps_agents.cli --version
python -m tapps_agents.cli reviewer --help
```

#### Step 1.3: Document Current State
- Current version: 2.4.1
- Installation type: Editable
- Configuration location: `.tapps-agents/`
- Any custom modifications in TappsCodingAgents directory

### Phase 2: Upgrade Execution

#### Step 2.1: Update Git Repository
```powershell
# Navigate to TappsCodingAgents directory
cd TappsCodingAgents

# Fetch latest tags
git fetch --tags

# Checkout v2.4.3 tag
git checkout v2.4.3

# Verify version
git describe --tags
```

#### Step 2.2: Verify Version Files
```powershell
# Check version in __init__.py
Select-String -Path "tapps_agents/__init__.py" -Pattern "__version__"

# Check version in pyproject.toml
Select-String -Path "pyproject.toml" -Pattern "version ="
```

#### Step 2.3: Reinstall Package
```powershell
# Return to project root
cd ..

# Uninstall current version (if needed)
python -m pip uninstall tapps-agents -y

# Reinstall as editable
python -m pip install -e TappsCodingAgents

# Verify installation
python -m pip show tapps-agents
```

#### Step 2.4: Verify Upgrade
```powershell
# Check version
python -m tapps_agents.cli --version

# Test basic functionality
python -m tapps_agents.cli reviewer --help
python -m tapps_agents.cli enhancer --help
```

### Phase 3: Post-Upgrade Verification

#### Step 3.1: Configuration Verification
```powershell
# Verify config file is intact
Test-Path ".tapps-agents/config.yaml"

# Check config version compatibility
python -m tapps_agents.cli init --check
```

#### Step 3.2: Functionality Testing
```powershell
# Test reviewer agent
python -m tapps_agents.cli reviewer score services/websocket-ingestion/src/main.py

# Test enhancer agent
python -m tapps_agents.cli enhancer enhance "Test prompt"

# Test Simple Mode (if available)
# In Cursor: @simple-mode *help
```

#### Step 3.3: Knowledge Base Verification
```powershell
# Check Context7 KB cache
Test-Path ".tapps-agents/kb/context7-cache"

# Verify KB index
Test-Path ".tapps-agents/kb/context7-cache/index.yaml"
```

### Phase 4: Codebase Deep Review

#### Step 4.1: Search for Version References
```powershell
# Search for version strings
Get-ChildItem -Recurse -Include *.md,*.py,*.yaml,*.yml,*.txt | 
    Select-String -Pattern "2\.4\.[0-3]|tapps-agents.*2\.4" | 
    Select-Object Path, LineNumber, Line
```

#### Step 4.2: Update Documentation References
Files to check and update:
- `README.md` - May reference TappsCodingAgents version
- `docs/TAPPS_AGENTS_*.md` - Any version-specific documentation
- `.cursor/rules/*.mdc` - Cursor rules that reference versions
- `implementation/*.md` - Implementation notes

#### Step 4.3: Clean Up Old Versions
```powershell
# Search for old version directories (if any)
Get-ChildItem -Directory | Where-Object { $_.Name -like "*tapps*2.4.1*" -or $_.Name -like "*tapps*old*" }

# Search for old egg-info directories
Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -like "*tapps_agents.egg-info*" }
```

#### Step 4.4: Verify No Duplicate Installations
```powershell
# Check all Python installations
python -m pip list | Select-String "tapps"

# Check site-packages
python -c "import site; print(site.getsitepackages())"
```

### Phase 5: Cleanup and Finalization

#### Step 5.1: Remove Backup Files (After Verification)
```powershell
# Only after confirming everything works
# Remove-Item -Path "implementation/backups/tapps-agents-2.4.1" -Recurse -Force
```

#### Step 5.2: Update Version Tracking
```powershell
# Create version tracking file
@"
TappsCodingAgents Version History
=================================
2026-01-XX: Upgraded from 2.4.1 to 2.4.3
- Fixed TypeError in reviewer score_validator
- Command reference improvements
- Test and validator enhancements
"@ | Out-File -FilePath ".tapps-agents/.framework-version" -Encoding UTF8
```

#### Step 5.3: Document Upgrade Results
- Create upgrade completion report
- Document any issues encountered
- Note any configuration changes required

## Risk Assessment

### Low Risk
- ✅ Version jump is small (2.4.1 → 2.4.3)
- ✅ No breaking changes expected (patch version)
- ✅ Configuration format unchanged
- ✅ Editable install allows easy rollback

### Medium Risk
- ⚠️ Custom modifications in TappsCodingAgents directory (if any)
- ⚠️ Configuration compatibility (should be fine, but verify)

### Mitigation Strategies
1. **Backup First** - All configuration backed up before upgrade
2. **Git Checkout** - Can easily revert to v2.4.1 if needed
3. **Editable Install** - Changes are immediately reflected
4. **Incremental Testing** - Test after each step

## Rollback Plan

If upgrade fails or causes issues:

```powershell
# Rollback to v2.4.1
cd TappsCodingAgents
git checkout v2.4.1
cd ..
python -m pip install -e TappsCodingAgents --force-reinstall

# Restore configuration if needed
Copy-Item -Path "implementation/backups/tapps-agents-2.4.1/config.yaml" -Destination ".tapps-agents/config.yaml" -Force
```

## Verification Checklist

- [ ] Current version verified (2.4.1)
- [ ] Backup created
- [ ] Git repository updated to v2.4.3
- [ ] Package reinstalled
- [ ] Version verified (2.4.3)
- [ ] Basic commands work (`--version`, `--help`)
- [ ] Reviewer agent functional
- [ ] Enhancer agent functional
- [ ] Configuration intact
- [ ] Knowledge base intact
- [ ] No duplicate installations found
- [ ] Documentation updated
- [ ] Codebase reviewed for old references
- [ ] All tests pass (if applicable)

## Post-Upgrade Tasks

1. **Update Documentation**
   - Update README.md if it references version
   - Update any version-specific guides
   - Update Cursor rules if needed

2. **Test Integration**
   - Test Simple Mode in Cursor
   - Test all agent commands
   - Verify Context7 KB integration

3. **Monitor for Issues**
   - Watch for any errors in logs
   - Monitor agent execution
   - Check for deprecation warnings

## Expected Outcomes

After successful upgrade:
- ✅ TappsCodingAgents v2.4.3 installed and functional
- ✅ All configuration preserved
- ✅ All functionality working
- ✅ No old versions remaining
- ✅ Documentation updated
- ✅ Codebase clean of old references

## Notes

- The upgrade is low-risk due to small version jump
- Editable install makes rollback easy
- Configuration should be compatible (no breaking changes)
- HomeIQ doesn't depend on TappsCodingAgents as a runtime dependency (good)

## References

- [TappsCodingAgents GitHub Repository](https://github.com/wtthornton/TappsCodingAgents)
- [Release v2.4.3](https://github.com/wtthornton/TappsCodingAgents/releases/tag/v2.4.3)
- [CHANGELOG.md](TappsCodingAgents/CHANGELOG.md)
- [Troubleshooting Guide](TappsCodingAgents/docs/TROUBLESHOOTING.md)

