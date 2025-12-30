#!/usr/bin/env python3
"""
Unified Git Cleanup Script for HomeIQ
Uses TappsCodingAgents infrastructure for better integration and automation.

This script provides a more robust, automated approach to cleaning up:
- Orphaned git branches (merged and unmerged)
- Git worktrees (using TappsCodingAgents WorktreeManager)
- Stale worktree references

Benefits over PowerShell scripts:
- Uses TappsCodingAgents WorktreeManager for proper worktree handling
- Better error handling and logging
- Can be integrated into CI/CD pipelines
- More reliable git command execution
- Unified approach for branches and worktrees
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add TappsCodingAgents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "TappsCodingAgents"))

try:
    from tapps_agents.core.worktree import WorktreeManager
    from tapps_agents.core.config import ProjectConfig, load_config
except ImportError:
    print("Warning: TappsCodingAgents not found, using basic git commands only")
    WorktreeManager = None
    ProjectConfig = None
    load_config = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedGitCleanup:
    """Unified git cleanup tool for branches and worktrees."""
    
    def __init__(self, project_root: Path | None = None, dry_run: bool = False):
        """
        Initialize cleanup tool.
        
        Args:
            project_root: Project root directory (default: current directory)
            dry_run: If True, only report what would be cleaned up
        """
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.dry_run = dry_run
        self.worktree_manager = None
        
        # Initialize WorktreeManager if available
        if WorktreeManager:
            try:
                self.worktree_manager = WorktreeManager(
                    base_path=self.project_root,
                    worktree_base=self.project_root / ".tapps-agents" / "worktrees"
                )
            except Exception as e:
                logger.warning(f"Could not initialize WorktreeManager: {e}")
        
        # Verify we're in a git repository
        if not (self.project_root / ".git").exists():
            raise ValueError(f"Not a git repository: {self.project_root}")
    
    def run_git_command(self, cmd: list[str], check: bool = True) -> tuple[str, str, int]:
        """
        Run a git command and return output.
        
        Args:
            cmd: Git command as list
            check: If True, raise exception on non-zero exit
            
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        try:
            result = subprocess.run(
                ["git"] + cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"Error: {e.stderr}")
            if check:
                raise
            return e.stdout.strip(), e.stderr.strip(), e.returncode
    
    def fetch_and_prune(self) -> None:
        """Fetch latest from remote and prune deleted branches."""
        logger.info("Fetching latest from remote and pruning...")
        if not self.dry_run:
            self.run_git_command(["fetch", "--prune", "origin"])
        else:
            logger.info("[DRY RUN] Would run: git fetch --prune origin")
    
    def get_merged_remote_branches(self) -> list[str]:
        """Get list of remote branches merged into master."""
        stdout, _, _ = self.run_git_command(
            ["branch", "-r", "--merged", "origin/master"],
            check=False
        )
        
        branches = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and "origin/HEAD" not in line and "origin/master" not in line:
                # Remove "origin/" prefix
                branch_name = line.replace("origin/", "").strip()
                if branch_name:
                    branches.append(branch_name)
        
        return branches
    
    def get_unmerged_remote_branches(self) -> list[str]:
        """Get list of remote branches NOT merged into master."""
        stdout, _, _ = self.run_git_command(
            ["branch", "-r", "--no-merged", "origin/master"],
            check=False
        )
        
        branches = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and "origin/HEAD" not in line and "origin/master" not in line:
                branch_name = line.replace("origin/", "").strip()
                if branch_name:
                    branches.append(branch_name)
        
        return branches
    
    def get_local_branches(self) -> list[str]:
        """Get list of local branches."""
        stdout, _, _ = self.run_git_command(["branch"], check=False)
        
        branches = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("*") and "master" not in line:
                branch_name = line.replace("*", "").strip()
                if branch_name:
                    branches.append(branch_name)
        
        return branches
    
    def get_merged_local_branches(self) -> list[str]:
        """Get list of local branches merged into master."""
        stdout, _, _ = self.run_git_command(
            ["branch", "--merged", "master"],
            check=False
        )
        
        branches = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("*") and "master" not in line:
                branch_name = line.replace("*", "").strip()
                if branch_name:
                    branches.append(branch_name)
        
        return branches
    
    def delete_remote_branch(self, branch_name: str) -> bool:
        """Delete a remote branch."""
        logger.info(f"Deleting remote branch: origin/{branch_name}")
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: origin/{branch_name}")
            return True
        
        _, stderr, returncode = self.run_git_command(
            ["push", "origin", "--delete", branch_name],
            check=False
        )
        
        if returncode == 0:
            logger.info(f"✓ Deleted origin/{branch_name}")
            return True
        else:
            logger.error(f"✗ Failed to delete origin/{branch_name}: {stderr}")
            return False
    
    def delete_local_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete a local branch."""
        logger.info(f"Deleting local branch: {branch_name}")
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: {branch_name}")
            return True
        
        cmd = ["branch", "-D" if force else "-d", branch_name]
        _, stderr, returncode = self.run_git_command(cmd, check=False)
        
        if returncode == 0:
            logger.info(f"✓ Deleted {branch_name}")
            return True
        else:
            logger.warning(f"✗ Failed to delete {branch_name}: {stderr}")
            if not force and "not fully merged" in stderr:
                logger.info(f"  (Use --force to delete anyway)")
            return False
    
    def list_worktrees(self) -> list[dict[str, str]]:
        """List all git worktrees."""
        stdout, _, _ = self.run_git_command(["worktree", "list"], check=False)
        
        worktrees = []
        # Normalize paths for comparison (handle Windows path differences)
        main_path_normalized = str(self.project_root.resolve()).replace("\\", "/").lower()
        
        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Parse: "path commit-hash [branch-name]"
            parts = line.split()
            if len(parts) >= 2:
                path = parts[0]
                commit = parts[1]
                branch = parts[2] if len(parts) > 2 else "(detached HEAD)"
                
                # Normalize path for comparison
                path_normalized = Path(path).resolve().as_posix().lower()
                
                # Skip main repository (compare normalized paths)
                if path_normalized != main_path_normalized:
                    worktrees.append({
                        "path": path,
                        "commit": commit,
                        "branch": branch
                    })
        
        return worktrees
    
    def remove_worktree(self, worktree_path: str) -> bool:
        """Remove a git worktree."""
        logger.info(f"Removing worktree: {worktree_path}")
        if self.dry_run:
            logger.info(f"[DRY RUN] Would remove: {worktree_path}")
            return True
        
        # Try using WorktreeManager first
        if self.worktree_manager:
            try:
                # Extract agent_id from path
                worktree_path_obj = Path(worktree_path)
                if worktree_path_obj.parent == self.worktree_manager.worktree_base:
                    agent_id = worktree_path_obj.name
                    if self.worktree_manager.remove_worktree(agent_id):
                        logger.info(f"✓ Removed worktree via WorktreeManager: {worktree_path}")
                        return True
            except Exception as e:
                logger.warning(f"WorktreeManager removal failed: {e}, trying git command")
        
        # Fallback to git command
        _, stderr, returncode = self.run_git_command(
            ["worktree", "remove", worktree_path, "--force"],
            check=False
        )
        
        if returncode == 0:
            logger.info(f"✓ Removed worktree: {worktree_path}")
            return True
        else:
            logger.error(f"✗ Failed to remove worktree {worktree_path}: {stderr}")
            return False
    
    def prune_worktrees(self) -> bool:
        """Prune stale worktree references."""
        logger.info("Pruning stale worktree references...")
        if self.dry_run:
            logger.info("[DRY RUN] Would run: git worktree prune")
            return True
        
        _, stderr, returncode = self.run_git_command(
            ["worktree", "prune", "--verbose"],
            check=False
        )
        
        if returncode == 0:
            logger.info("✓ Pruned stale worktree references")
            return True
        else:
            logger.warning(f"Prune completed with warnings: {stderr}")
            return True  # Prune usually succeeds even with warnings
    
    def cleanup_merged_remote_branches(self) -> dict[str, Any]:
        """Clean up merged remote branches."""
        logger.info("=== Cleaning up merged remote branches ===")
        merged = self.get_merged_remote_branches()
        
        if not merged:
            logger.info("No merged remote branches to clean up")
            return {"deleted": 0, "total": 0}
        
        logger.info(f"Found {len(merged)} merged remote branch(es)")
        deleted = 0
        
        for branch in merged:
            if self.delete_remote_branch(branch):
                deleted += 1
        
        return {"deleted": deleted, "total": len(merged)}
    
    def cleanup_merged_local_branches(self, force: bool = False) -> dict[str, Any]:
        """Clean up merged local branches."""
        logger.info("=== Cleaning up merged local branches ===")
        merged = self.get_merged_local_branches()
        
        if not merged:
            logger.info("No merged local branches to clean up")
            return {"deleted": 0, "total": 0}
        
        logger.info(f"Found {len(merged)} merged local branch(es)")
        deleted = 0
        
        for branch in merged:
            if self.delete_local_branch(branch, force=force):
                deleted += 1
        
        return {"deleted": deleted, "total": len(merged)}
    
    def cleanup_worktrees(self, prune_stale: bool = True) -> dict[str, Any]:
        """Clean up worktrees."""
        logger.info("=== Cleaning up worktrees ===")
        worktrees = self.list_worktrees()
        
        if not worktrees:
            logger.info("No additional worktrees to clean up")
            if prune_stale:
                self.prune_worktrees()
            return {"removed": 0, "total": 0}
        
        logger.info(f"Found {len(worktrees)} additional worktree(s)")
        removed = 0
        
        for wt in worktrees:
            if self.remove_worktree(wt["path"]):
                removed += 1
        
        if prune_stale:
            self.prune_worktrees()
        
        return {"removed": removed, "total": len(worktrees)}
    
    def cleanup_workflow_branches(self) -> dict[str, Any]:
        """Clean up local workflow branches."""
        logger.info("=== Cleaning up workflow branches ===")
        local_branches = self.get_local_branches()
        workflow_branches = [b for b in local_branches if b.startswith("workflow/")]
        
        if not workflow_branches:
            logger.info("No workflow branches to clean up")
            return {"deleted": 0, "total": 0}
        
        logger.info(f"Found {len(workflow_branches)} workflow branch(es)")
        deleted = 0
        
        for branch in workflow_branches:
            if self.delete_local_branch(branch, force=True):
                deleted += 1
        
        return {"deleted": deleted, "total": len(workflow_branches)}
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of cleanup status."""
        return {
            "merged_remote_branches": len(self.get_merged_remote_branches()),
            "unmerged_remote_branches": len(self.get_unmerged_remote_branches()),
            "local_branches": len(self.get_local_branches()),
            "merged_local_branches": len(self.get_merged_local_branches()),
            "worktrees": len(self.list_worktrees()),
            "workflow_branches": len([
                b for b in self.get_local_branches()
                if b.startswith("workflow/")
            ])
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Git Cleanup Tool for HomeIQ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be cleaned
  python scripts/cleanup-git-unified.py --dry-run
  
  # Clean up merged remote branches
  python scripts/cleanup-git-unified.py --merged-remote
  
  # Clean up everything (merged branches + worktrees)
  python scripts/cleanup-git-unified.py --all
  
  # Clean up specific items
  python scripts/cleanup-git-unified.py --merged-remote --worktrees --workflow
        """
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them"
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch and prune before cleanup"
    )
    parser.add_argument(
        "--merged-remote",
        action="store_true",
        help="Clean up merged remote branches"
    )
    parser.add_argument(
        "--merged-local",
        action="store_true",
        help="Clean up merged local branches"
    )
    parser.add_argument(
        "--worktrees",
        action="store_true",
        help="Clean up worktrees"
    )
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Clean up workflow branches"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean up everything (merged branches + worktrees + workflow branches)"
    )
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Force delete local branches (even if not fully merged)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary only (no cleanup)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        cleanup = UnifiedGitCleanup(
            project_root=args.project_root,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            logger.info("=== DRY RUN MODE - No changes will be made ===")
        
        # Fetch if requested
        if args.fetch:
            cleanup.fetch_and_prune()
        
        results = {}
        
        # Show summary if requested
        if args.summary:
            summary = cleanup.get_summary()
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                logger.info("=== Cleanup Summary ===")
                logger.info(f"Merged remote branches: {summary['merged_remote_branches']}")
                logger.info(f"Unmerged remote branches: {summary['unmerged_remote_branches']}")
                logger.info(f"Local branches: {summary['local_branches']}")
                logger.info(f"Merged local branches: {summary['merged_local_branches']}")
                logger.info(f"Worktrees: {summary['worktrees']}")
                logger.info(f"Workflow branches: {summary['workflow_branches']}")
            return
        
        # Execute cleanup
        if args.all:
            results["merged_remote"] = cleanup.cleanup_merged_remote_branches()
            results["merged_local"] = cleanup.cleanup_merged_local_branches(
                force=args.force_local
            )
            results["worktrees"] = cleanup.cleanup_worktrees()
            results["workflow"] = cleanup.cleanup_workflow_branches()
        else:
            if args.merged_remote:
                results["merged_remote"] = cleanup.cleanup_merged_remote_branches()
            if args.merged_local:
                results["merged_local"] = cleanup.cleanup_merged_local_branches(
                    force=args.force_local
                )
            if args.worktrees:
                results["worktrees"] = cleanup.cleanup_worktrees()
            if args.workflow:
                results["workflow"] = cleanup.cleanup_workflow_branches()
        
        # Output results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            logger.info("=== Cleanup Complete ===")
            for key, value in results.items():
                if isinstance(value, dict):
                    deleted = value.get("deleted", value.get("removed", 0))
                    total = value.get("total", 0)
                    logger.info(f"{key}: {deleted}/{total} cleaned")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

