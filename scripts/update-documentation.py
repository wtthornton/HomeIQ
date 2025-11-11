#!/usr/bin/env python3
"""
Automated Documentation Update Script

This script updates documentation files when code is merged to master.
It handles:
- CHANGELOG.md updates (categorized commit entries)
- README.md updates (latest code review date, recent updates section)
- docs/DOCUMENTATION_INDEX.md updates (last updated date)
- CLAUDE.md updates (last updated date)
- Version number updates (if configured)
- Other documentation maintenance tasks

Usage:
    python scripts/update-documentation.py \
        --commit-range "v1.0.0..HEAD" \
        --merged-branch "feature/new-feature" \
        --repo "owner/repo" \
        --sha "abc123"
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import git
    from git import Repo
except ImportError:
    print("ERROR: gitpython not installed. Run: pip install gitpython")
    sys.exit(1)


class DocumentationUpdater:
    """Handles automated documentation updates."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize the updater with repository path."""
        self.repo_path = Path(repo_path).resolve()
        self.repo = Repo(self.repo_path)
        self.changes_made = False
        
    def get_commits_in_range(self, commit_range: str) -> List[git.Commit]:
        """Get list of commits in the specified range."""
        try:
            if ".." in commit_range:
                start, end = commit_range.split("..")
                commits = list(self.repo.iter_commits(f"{start}..{end}"))
            else:
                commits = list(self.repo.iter_commits(commit_range, max_count=50))
            return commits
        except Exception as e:
            print(f"Warning: Could not get commits from range '{commit_range}': {e}")
            # Fallback to last 10 commits
            return list(self.repo.iter_commits(max_count=10))
    
    def categorize_commits(self, commits: List[git.Commit]) -> dict:
        """Categorize commits by type (Added, Changed, Fixed, etc.)."""
        categories = {
            "Added": [],
            "Changed": [],
            "Deprecated": [],
            "Removed": [],
            "Fixed": [],
            "Security": [],
            "Other": []
        }
        
        # Patterns for commit message categorization
        patterns = {
            "Added": [r"^add", r"^feat", r"^new", r"^implement"],
            "Changed": [r"^change", r"^update", r"^modify", r"^refactor", r"^improve"],
            "Deprecated": [r"^deprecate"],
            "Removed": [r"^remove", r"^delete", r"^drop"],
            "Fixed": [r"^fix", r"^bug", r"^resolve", r"^correct"],
            "Security": [r"^security", r"^sec", r"^vuln"]
        }
        
        for commit in commits:
            message = commit.message.strip().split('\n')[0].lower()
            categorized = False
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.match(pattern, message):
                        categories[category].append({
                            "hash": commit.hexsha[:7],
                            "message": commit.message.strip().split('\n')[0],
                            "author": commit.author.name,
                            "date": datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d")
                        })
                        categorized = True
                        break
                if categorized:
                    break
            
            if not categorized:
                categories["Other"].append({
                    "hash": commit.hexsha[:7],
                    "message": commit.message.strip().split('\n')[0],
                    "author": commit.author.name,
                    "date": datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d")
                })
        
        return categories
    
    def update_changelog(self, categories: dict, merged_branch: Optional[str] = None) -> bool:
        """Update CHANGELOG.md with new entries."""
        changelog_path = self.repo_path / "CHANGELOG.md"
        
        if not changelog_path.exists():
            print(f"Warning: CHANGELOG.md not found at {changelog_path}")
            return False
        
        # Read current changelog
        content = changelog_path.read_text()
        
        # Check if there are any meaningful changes
        has_changes = any(
            len(commits) > 0 
            for category, commits in categories.items() 
            if category != "Other"
        )
        
        if not has_changes:
            print("No significant changes to document in CHANGELOG")
            return False
        
        # Generate new changelog entry
        today = datetime.now().strftime("%Y-%m-%d")
        branch_note = f" (from {merged_branch})" if merged_branch else ""
        
        new_entry = f"\n## [Unreleased] - {today}{branch_note}\n\n"
        
        # Add categorized changes
        for category, commits in categories.items():
            if category == "Other" or len(commits) == 0:
                continue
            
            new_entry += f"### {category}\n\n"
            for commit in commits:
                # Clean up commit message (remove prefix like "feat:", "fix:", etc.)
                clean_message = re.sub(r'^(feat|fix|chore|docs|style|refactor|test|perf|ci|build|revert):\s*', 
                                      '', commit["message"], flags=re.IGNORECASE)
                new_entry += f"- **{clean_message}** ({commit['hash']}) - {commit['author']}\n"
            new_entry += "\n"
        
        # Insert after the first "## [Unreleased]" section
        unreleased_pattern = r'(## \[Unreleased\][^\n]*\n)'
        if re.search(unreleased_pattern, content):
            # Replace existing [Unreleased] section
            content = re.sub(
                unreleased_pattern,
                new_entry.strip() + "\n\n",
                content,
                count=1
            )
        else:
            # Insert at the beginning after title
            content = re.sub(
                r'(# Changelog\n\n)',
                r'\1' + new_entry.strip() + "\n\n",
                content
            )
        
        # Write updated changelog
        changelog_path.write_text(content)
        self.changes_made = True
        print(f"✅ Updated CHANGELOG.md")
        return True
    
    def update_version_if_needed(self) -> bool:
        """Update version numbers if version files are modified."""
        version_files = [
            ("package.json", r'"version":\s*"([^"]+)"'),
            ("tools/cli/setup.py", r'version="([^"]+)"'),
        ]
        
        changed = False
        for file_path, pattern in version_files:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                continue
            
            # Check if file was modified in recent commits
            try:
                diff = self.repo.git.diff("HEAD~5..HEAD", "--", str(file_path))
                if not diff:
                    continue
            except:
                continue
            
            # For now, we'll just log that version files exist
            # Actual version bumping should be done manually or via semantic versioning
            print(f"ℹ️  Version file {file_path} exists (not auto-updating version)")
        
        return changed
    
    def update_documentation_index(self) -> bool:
        """Update documentation index last updated date."""
        index_path = self.repo_path / "docs" / "DOCUMENTATION_INDEX.md"
        
        if not index_path.exists():
            return False
        
        content = index_path.read_text()
        today = datetime.now().strftime("%B %d, %Y")
        
        # Update "Last Updated" date
        # Pattern: **Last Updated:** October 24, 2025
        pattern = r'\*\*Last Updated:\*\*\s*[^\n]+'
        replacement = f"**Last Updated:** {today}"
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            index_path.write_text(content)
            self.changes_made = True
            print(f"✅ Updated docs/DOCUMENTATION_INDEX.md last updated date")
            return True
        
        return False
    
    def update_readme(self, commits: List[git.Commit]) -> bool:
        """Update README.md with latest code review date and recent updates."""
        readme_path = self.repo_path / "README.md"
        
        if not readme_path.exists():
            return False
        
        content = readme_path.read_text()
        today = datetime.now().strftime("%B %d, %Y")
        changed = False
        
        # Update "Latest Code Review" date
        # Pattern: **Latest Code Review:** November 4, 2025
        pattern = r'\*\*Latest Code Review:\*\*\s*[^\n]+'
        replacement = f"**Latest Code Review:** {today}"
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changed = True
            print(f"✅ Updated README.md latest code review date")
        
        # Optionally add to "Recent Updates" section if there are significant changes
        # This is conservative - only add if there are notable features/fixes
        recent_updates_pattern = r'(### Recent Updates\n)'
        if re.search(recent_updates_pattern, content) and commits:
            # Check if we have notable commits (features or fixes)
            notable_commits = [
                c for c in commits 
                if any(re.match(pattern, c.message.strip().split('\n')[0].lower()) 
                      for patterns in [
                          [r"^feat", r"^add", r"^implement"],
                          [r"^fix", r"^bug"]
                      ] for pattern in patterns)
            ]
            
            if notable_commits and len(notable_commits) > 0:
                # Get the most significant commit
                top_commit = notable_commits[0]
                clean_message = re.sub(
                    r'^(feat|fix|chore|docs|style|refactor|test|perf|ci|build|revert):\s*', 
                    '', top_commit.message.strip().split('\n')[0], 
                    flags=re.IGNORECASE
                )
                
                # Add bullet point to Recent Updates
                new_update = f"- **{clean_message}** ({today})\n"
                content = re.sub(
                    recent_updates_pattern,
                    r'\1' + new_update,
                    content
                )
                changed = True
                print(f"✅ Added recent update to README.md")
        
        if changed:
            readme_path.write_text(content)
            self.changes_made = True
        
        return changed
    
    def update_claude_md(self) -> bool:
        """Update CLAUDE.md last updated date."""
        claude_path = self.repo_path / "CLAUDE.md"
        
        if not claude_path.exists():
            return False
        
        content = claude_path.read_text()
        today = datetime.now().strftime("%B %d, %Y")
        
        # Update "Last Updated" date
        # Pattern: **Last Updated:** October 24, 2025
        pattern = r'\*\*Last Updated:\*\*\s*[^\n]+'
        replacement = f"**Last Updated:** {today}"
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            claude_path.write_text(content)
            self.changes_made = True
            print(f"✅ Updated CLAUDE.md last updated date")
            return True
        
        return False
    
    def run(self, commit_range: str, merged_branch: Optional[str] = None, 
            last_tag: Optional[str] = None, repo: Optional[str] = None, 
            sha: Optional[str] = None) -> bool:
        """Run all documentation updates."""
        print(f"🔄 Starting documentation update process...")
        print(f"   Commit range: {commit_range}")
        if merged_branch:
            print(f"   Merged branch: {merged_branch}")
        if last_tag:
            print(f"   Last tag: {last_tag}")
        
        # Get commits in range
        commits = self.get_commits_in_range(commit_range)
        print(f"   Found {len(commits)} commits")
        
        if not commits:
            print("⚠️  No commits found in range, skipping documentation update")
            return False
        
        # Categorize commits
        categories = self.categorize_commits(commits)
        
        # Print summary
        print("\n📊 Commit Summary:")
        for category, commit_list in categories.items():
            if commit_list:
                print(f"   {category}: {len(commit_list)} commits")
        
        # Update changelog
        self.update_changelog(categories, merged_branch)
        
        # Update README.md (latest code review date, recent updates)
        self.update_readme(commits)
        
        # Update documentation index
        self.update_documentation_index()
        
        # Update CLAUDE.md
        self.update_claude_md()
        
        # Update version (if needed)
        self.update_version_if_needed()
        
        if self.changes_made:
            print("\n✅ Documentation update complete!")
        else:
            print("\nℹ️  No documentation changes needed")
        
        return self.changes_made


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update documentation files after merge to master"
    )
    parser.add_argument(
        "--commit-range",
        required=True,
        help="Git commit range (e.g., 'v1.0.0..HEAD' or 'HEAD~10..HEAD')"
    )
    parser.add_argument(
        "--merged-branch",
        help="Name of the branch that was merged"
    )
    parser.add_argument(
        "--last-tag",
        help="Last git tag (for reference)"
    )
    parser.add_argument(
        "--repo",
        help="Repository name (owner/repo)"
    )
    parser.add_argument(
        "--sha",
        help="Commit SHA"
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to repository root (default: current directory)"
    )
    
    args = parser.parse_args()
    
    updater = DocumentationUpdater(repo_path=args.repo_path)
    success = updater.run(
        commit_range=args.commit_range,
        merged_branch=args.merged_branch,
        last_tag=args.last_tag,
        repo=args.repo,
        sha=args.sha
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
