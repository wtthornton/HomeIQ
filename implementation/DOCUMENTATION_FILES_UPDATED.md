# Documentation Files Updated Automatically

This document lists all files that are automatically updated when code is merged to master.

## Files Updated on Every Merge

### 1. CHANGELOG.md
**Location:** Root directory  
**What's Updated:**
- Adds new `[Unreleased]` section with categorized commits
- Categorizes commits: Added, Changed, Fixed, Deprecated, Removed, Security
- Includes commit hash, author, and date

**Pattern Updated:**
```markdown
## [Unreleased] - YYYY-MM-DD (from branch-name)

### Added
- **Feature description** (abc1234) - Author Name

### Fixed
- **Bug fix description** (def5678) - Author Name
```

### 2. README.md
**Location:** Root directory  
**What's Updated:**
- **Latest Code Review** date (line ~488)
- **Recent Updates** section (line ~420) - Only for notable features/fixes

**Patterns Updated:**
```markdown
**Latest Code Review:** November 11, 2025 - Comprehensive review...

### Recent Updates
- **New feature description** (November 11, 2025)
```

### 3. docs/DOCUMENTATION_INDEX.md
**Location:** `docs/DOCUMENTATION_INDEX.md`  
**What's Updated:**
- **Last Updated** date (line 3)

**Pattern Updated:**
```markdown
**Last Updated:** November 11, 2025
```

### 4. CLAUDE.md
**Location:** Root directory  
**What's Updated:**
- **Last Updated** date (line 3)

**Pattern Updated:**
```markdown
**Last Updated:** November 11, 2025
```

## Files Detected But Not Auto-Updated

### Version Files
These files are detected but require manual configuration for auto-updates:

1. **package.json** (`"version": "1.0.0"`)
   - Currently: Detected only
   - To enable: Implement semantic versioning logic in script

2. **tools/cli/setup.py** (`version="1.0.0"`)
   - Currently: Detected only
   - To enable: Implement semantic versioning logic in script

## Files That Could Be Added (Future Enhancements)

### Potential Additions

1. **docs/architecture/performance-patterns.md**
   - Could update "Last Updated" date if pattern exists

2. **docs/architecture/epic-31-architecture.mdc**
   - Could update "Last Updated" date if pattern exists

3. **CONTRIBUTING.md**
   - Could add "Last Updated" date tracking

4. **LICENSE**
   - Could track copyright year updates

## How to Add New Files

To add a new file to the automatic update process:

1. **Add update method** to `DocumentationUpdater` class in `scripts/update-documentation.py`:
   ```python
   def update_your_file(self) -> bool:
       file_path = self.repo_path / "path" / "to" / "file.md"
       if not file_path.exists():
           return False
       
       content = file_path.read_text()
       today = datetime.now().strftime("%B %d, %Y")
       
       # Your update logic here
       pattern = r'your-pattern-here'
       replacement = f"your replacement with {today}"
       
       if re.search(pattern, content):
           content = re.sub(pattern, replacement, content)
           file_path.write_text(content)
           self.changes_made = True
           print(f"✅ Updated your-file.md")
           return True
       
       return False
   ```

2. **Call the method** in the `run()` method:
   ```python
   # Update your file
   self.update_your_file()
   ```

3. **Update documentation** in `docs/AUTOMATED_DOCUMENTATION_UPDATES.md`

## Pattern Matching

The script uses regex patterns to find and update dates. Common patterns:

- `**Last Updated:** October 24, 2025` → `**Last Updated:** {today}`
- `**Latest Code Review:** November 4, 2025` → `**Latest Code Review:** {today}`
- `Last Updated: 2025-10-24` → `Last Updated: {today}` (if needed)

## Date Formats Used

- **README.md, DOCUMENTATION_INDEX.md, CLAUDE.md**: `November 11, 2025` (Month DD, YYYY)
- **CHANGELOG.md**: `2025-11-11` (YYYY-MM-DD)

## Testing Updates

To test what would be updated:

```bash
# Dry run (check what would change)
python scripts/update-documentation.py \
  --commit-range "HEAD~5..HEAD" \
  --merged-branch "test-branch"

# Check git diff to see changes
git diff README.md CHANGELOG.md docs/DOCUMENTATION_INDEX.md CLAUDE.md
```

## Summary

**Total Files Auto-Updated:** 4
- ✅ CHANGELOG.md (categorized commits)
- ✅ README.md (dates + recent updates)
- ✅ docs/DOCUMENTATION_INDEX.md (last updated date)
- ✅ CLAUDE.md (last updated date)

**Files Detected:** 2 (version files - not auto-updated)
- ⚠️ package.json
- ⚠️ tools/cli/setup.py

**Future Candidates:** 4+ (can be added as needed)

---

**Last Updated:** November 11, 2025  
**Maintained By:** Automated Documentation Update System
