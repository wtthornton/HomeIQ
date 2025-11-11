# Automated Documentation Updates

This directory contains scripts and workflows for automatically updating documentation when code is merged to master.

## Overview

The automated documentation update system consists of:

1. **GitHub Actions Workflow** (`.github/workflows/update-documentation.yml`)
   - Triggers automatically on merge to master/main
   - Runs the documentation update script
   - Commits changes back to the repository

2. **Update Script** (`scripts/update-documentation.py`)
   - Analyzes commits in the merge
   - Updates CHANGELOG.md with categorized changes
   - Updates version numbers (if configured)
   - Updates documentation indexes

## How It Works

### Automatic Trigger

When a pull request is merged to `master` or `main`:

1. GitHub Actions detects the merge commit
2. Extracts commit information (range, branch name, etc.)
3. Runs `scripts/update-documentation.py`
4. The script:
   - Analyzes commits since the last tag (or last 50 commits)
   - Categorizes changes (Added, Changed, Fixed, etc.)
   - Updates CHANGELOG.md with new entries
5. Changes are committed and pushed back to master

### Manual Trigger

You can also trigger the workflow manually:

1. Go to GitHub Actions tab
2. Select "Update Documentation on Merge to Master"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Configuration

### Required GitHub Secrets

No secrets are required for basic operation. The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.

### Optional Configuration

You can customize the script behavior by modifying:

- **Commit categorization patterns** in `scripts/update-documentation.py`
- **Changelog format** in the `update_changelog()` method
- **Version update logic** in the `update_version_if_needed()` method

## What Gets Updated

### CHANGELOG.md

The script automatically:
- Adds new entries under `[Unreleased]` section
- Categorizes commits by type:
  - **Added**: New features
  - **Changed**: Modifications to existing features
  - **Deprecated**: Soon-to-be removed features
  - **Removed**: Removed features
  - **Fixed**: Bug fixes
  - **Security**: Security patches
- Includes commit hash, author, and date

### README.md

The script automatically updates:
- **Latest Code Review** date - Updated to current date on each merge
- **Recent Updates** section - Adds notable features/fixes automatically (only for significant commits)

### docs/DOCUMENTATION_INDEX.md

The script automatically updates:
- **Last Updated** date - Updated to current date on each merge

### CLAUDE.md

The script automatically updates:
- **Last Updated** date - Updated to current date on each merge

### Version Files

Currently, version files are detected but not automatically updated. To enable automatic version bumping:

1. Modify `update_version_if_needed()` in the script
2. Implement semantic versioning logic
3. Update `package.json` and `setup.py` accordingly

## Testing Locally

You can test the script locally:

```bash
# Test with recent commits
python scripts/update-documentation.py \
  --commit-range "HEAD~10..HEAD" \
  --merged-branch "test-branch"

# Test with tag range
python scripts/update-documentation.py \
  --commit-range "v1.0.0..HEAD" \
  --merged-branch "feature/new-feature"
```

## Troubleshooting

### Workflow Not Triggering

- Ensure the workflow file is in `.github/workflows/update-documentation.yml`
- Check that branch name matches (`master` or `main`)
- Verify the merge commit message contains "Merge"

### No Changes Detected

- Check that commits exist in the specified range
- Verify commit messages follow conventional format (feat:, fix:, etc.)
- Review script output in GitHub Actions logs

### Permission Errors

- Ensure workflow has `contents: write` permission
- Check that `GITHUB_TOKEN` is available (automatic in GitHub Actions)

## Customization

### Adding New Documentation Updates

To add new documentation update tasks:

1. Add a new method to `DocumentationUpdater` class:
   ```python
   def update_custom_docs(self) -> bool:
       # Your update logic here
       return changed
   ```

2. Call it in the `run()` method:
   ```python
   self.update_custom_docs()
   ```

### Changing Commit Categorization

Modify the `patterns` dictionary in `categorize_commits()`:

```python
patterns = {
    "Added": [r"^add", r"^feat", r"^new", r"^implement", r"^your-pattern"],
    # ... other categories
}
```

### Custom Changelog Format

Modify the `update_changelog()` method to change the format of changelog entries.

## Best Practices

1. **Commit Messages**: Use conventional commit format for better categorization:
   - `feat: Add new feature`
   - `fix: Fix bug in X`
   - `docs: Update documentation`

2. **Branch Naming**: Use descriptive branch names (they appear in changelog)

3. **Review Changes**: Always review auto-generated changelog entries before merging

4. **Manual Overrides**: You can manually edit CHANGELOG.md if needed - the script will merge changes intelligently

## Related Files

- `.github/workflows/update-documentation.yml` - GitHub Actions workflow
- `scripts/update-documentation.py` - Update script
- `CHANGELOG.md` - Generated changelog file
- `package.json` - Version file (if version updates enabled)

## Support

For issues or questions:
1. Check GitHub Actions logs
2. Review script output
3. Test locally with `--commit-range` parameter
4. Check commit message format
