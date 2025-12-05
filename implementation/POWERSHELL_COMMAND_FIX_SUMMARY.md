# PowerShell Command Fix Summary

**Date:** December 4, 2025  
**Status:** ✅ Complete

---

## Issue

The command `curl -s http://localhost:8024/health | ConvertFrom-Json | Select-Object -Property status` does not work in PowerShell and will always fail.

**Root Cause:**
- `curl` in PowerShell is an alias for `Invoke-WebRequest`, not Unix curl
- The `-s` (silent) flag doesn't exist for `Invoke-WebRequest`
- Piping `Invoke-WebRequest` output directly to `ConvertFrom-Json` doesn't work
- This pattern is fundamentally incompatible with PowerShell

---

## Changes Made

### 1. Created PowerShell Best Practices Guide

**File:** `docs/POWERSHELL_BEST_PRACTICES.md`

**Contents:**
- Complete guide for PowerShell commands in Windows environments
- Correct alternatives to Unix-style curl commands
- Command equivalents table (Bash → PowerShell)
- Health check examples
- Error handling patterns
- Quick reference guide

### 2. Created PowerShell Commands Rule

**File:** `.cursor/rules/powershell-commands.mdc`

**Purpose:**
- Always-applied rule to prevent agents from using incorrect curl patterns
- Explicit warnings about forbidden patterns
- Correct patterns with examples
- Command equivalents table
- Agent guidelines for PowerShell environments

**Key Features:**
- `alwaysApply: true` - Ensures rule is always active
- Clear ❌ FORBIDDEN and ✅ CORRECT patterns
- Examples for common use cases
- Error handling patterns

### 3. Updated Development Environment Rule

**File:** `.cursor/rules/development-environment.mdc`

**Changes:**
- Added critical warning section about Unix-style curl commands
- Updated PowerShell HTTP Commands Reference
- Added explicit examples of what NOT to do
- Added references to PowerShell best practices guide

### 4. Updated CLI Reference Documentation

**File:** `docs/CLI_REFERENCE.md`

**Changes:**
- Added PowerShell equivalents for all bash curl commands
- Added warnings about incorrect curl usage
- Separated Linux/Mac (Bash) and Windows (PowerShell) sections
- Added references to PowerShell best practices guide

### 5. Updated Rules Overview

**File:** `.cursor/rules/README.mdc`

**Changes:**
- Added `powershell-commands.mdc` to the list of project rules
- Noted that `development-environment.mdc` was updated

---

## Files Created

1. `docs/POWERSHELL_BEST_PRACTICES.md` - Complete PowerShell guide
2. `.cursor/rules/powershell-commands.mdc` - Always-applied PowerShell rule
3. `implementation/POWERSHELL_COMMAND_FIX_SUMMARY.md` - This summary

## Files Updated

1. `.cursor/rules/development-environment.mdc` - Added curl warnings
2. `.cursor/rules/README.mdc` - Added new rule to list
3. `docs/CLI_REFERENCE.md` - Added PowerShell equivalents

---

## Correct Command Patterns

### ❌ NEVER Use (Will Always Fail)
```powershell
curl -s http://localhost:8024/health | ConvertFrom-Json | Select-Object -Property status
```

### ✅ ALWAYS Use Instead

**Option 1: Invoke-RestMethod (Recommended)**
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8024/health"
$response.status

# One-liner
(Invoke-RestMethod -Uri "http://localhost:8024/health").status
```

**Option 2: Invoke-WebRequest (for non-JSON)**
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8024/health"
$json = $response.Content | ConvertFrom-Json
$json.status
```

---

## Agent Guidelines

**All agents MUST:**
1. ✅ Never suggest `curl -s ... | ConvertFrom-Json` in PowerShell
2. ✅ Always use `Invoke-RestMethod` for JSON APIs
3. ✅ Always use `Invoke-WebRequest` for HTML/text responses
4. ✅ Provide PowerShell equivalents for all bash commands
5. ✅ Reference `docs/POWERSHELL_BEST_PRACTICES.md` when needed
6. ✅ Test commands in PowerShell before suggesting them

**If agents see this pattern:**
```powershell
curl -s http://... | ConvertFrom-Json
```
**They MUST:**
- Replace it with `Invoke-RestMethod`
- Update documentation
- Add a warning comment
- Update rules if needed

---

## Verification

To verify the fix:
1. Check that `powershell-commands.mdc` rule exists and has `alwaysApply: true`
2. Check that `docs/POWERSHELL_BEST_PRACTICES.md` exists
3. Check that `development-environment.mdc` has curl warnings
4. Check that `CLI_REFERENCE.md` has PowerShell equivalents
5. Test that agents no longer suggest the incorrect pattern

---

## References

- **PowerShell Best Practices:** `docs/POWERSHELL_BEST_PRACTICES.md`
- **PowerShell Rule:** `.cursor/rules/powershell-commands.mdc`
- **Development Environment:** `.cursor/rules/development-environment.mdc`
- **CLI Reference:** `docs/CLI_REFERENCE.md`

---

**Report Generated:** December 4, 2025  
**Status:** ✅ Complete  
**Impact:** Prevents all agents from using incorrect curl patterns in PowerShell

