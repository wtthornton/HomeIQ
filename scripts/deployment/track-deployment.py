#!/usr/bin/env python3
"""
Deployment Tracking Service
Tracks deployment history, metrics, and audit logs.

Usage:
    python track-deployment.py --deployment-id <id> --status <status> --commit <sha> --branch <branch>
    python track-deployment.py --list
    python track-deployment.py --metrics
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentTracker:
    """Tracks deployment history and metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "deployments.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize deployment tracking database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create deployments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                branch TEXT NOT NULL,
                duration_seconds INTEGER,
                services_count INTEGER,
                passed_checks INTEGER,
                failed_checks INTEGER,
                rollback_performed INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        
        # Create deployment_metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployment_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (deployment_id) REFERENCES deployments(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployments_timestamp 
            ON deployments(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployments_status 
            ON deployments(status)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized deployment tracking database: {self.db_path}")

    def track_deployment(
        self,
        deployment_id: str,
        status: str,
        commit: str,
        branch: str,
        duration: Optional[int] = None,
        services_count: Optional[int] = None,
        passed_checks: Optional[int] = None,
        failed_checks: Optional[int] = None,
        rollback_performed: bool = False,
        notes: Optional[str] = None
    ):
        """Track a deployment."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO deployments 
            (id, timestamp, status, commit_sha, branch, duration_seconds, 
             services_count, passed_checks, failed_checks, rollback_performed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deployment_id,
            timestamp,
            status,
            commit,
            branch,
            duration,
            services_count,
            passed_checks,
            failed_checks,
            1 if rollback_performed else 0,
            notes
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Tracked deployment: {deployment_id} ({status})")

    def add_metric(self, deployment_id: str, metric_name: str, metric_value: float):
        """Add a metric for a deployment."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO deployment_metrics (deployment_id, metric_name, metric_value, timestamp)
            VALUES (?, ?, ?, ?)
        """, (deployment_id, metric_name, metric_value, timestamp))
        
        conn.commit()
        conn.close()
        logger.info(f"Added metric {metric_name}={metric_value} for deployment {deployment_id}")

    def list_deployments(self, limit: int = 10) -> List[Dict]:
        """List recent deployments."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM deployments 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def get_metrics(self) -> Dict:
        """Get deployment metrics."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total deployments
        cursor.execute("SELECT COUNT(*) FROM deployments")
        total_deployments = cursor.fetchone()[0]
        
        # Successful deployments
        cursor.execute("SELECT COUNT(*) FROM deployments WHERE status = 'success'")
        successful_deployments = cursor.fetchone()[0]
        
        # Failed deployments
        cursor.execute("SELECT COUNT(*) FROM deployments WHERE status = 'failure'")
        failed_deployments = cursor.fetchone()[0]
        
        # Rollbacks
        cursor.execute("SELECT COUNT(*) FROM deployments WHERE rollback_performed = 1")
        rollbacks = cursor.fetchone()[0]
        
        # Average duration
        cursor.execute("""
            SELECT AVG(duration_seconds) 
            FROM deployments 
            WHERE duration_seconds IS NOT NULL
        """)
        avg_duration = cursor.fetchone()[0] or 0
        
        # Success rate
        success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0
        
        # Recent deployments (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM deployments 
            WHERE timestamp > datetime('now', '-7 days')
        """)
        recent_deployments = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "failed_deployments": failed_deployments,
            "rollbacks": rollbacks,
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "recent_deployments_7d": recent_deployments
        }

    def get_deployment(self, deployment_id: str) -> Optional[Dict]:
        """Get a specific deployment."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None


def main():
    parser = argparse.ArgumentParser(description="Deployment tracking service")
    parser.add_argument("--deployment-id", help="Deployment ID")
    parser.add_argument("--status", choices=["success", "failure", "in_progress"], help="Deployment status")
    parser.add_argument("--commit", help="Commit SHA")
    parser.add_argument("--branch", help="Branch name")
    parser.add_argument("--duration", type=int, help="Deployment duration in seconds")
    parser.add_argument("--services-count", type=int, help="Number of services deployed")
    parser.add_argument("--passed-checks", type=int, help="Number of passed health checks")
    parser.add_argument("--failed-checks", type=int, help="Number of failed health checks")
    parser.add_argument("--rollback", action="store_true", help="Rollback was performed")
    parser.add_argument("--notes", help="Additional notes")
    parser.add_argument("--list", action="store_true", help="List recent deployments")
    parser.add_argument("--metrics", action="store_true", help="Show deployment metrics")
    parser.add_argument("--db-path", help="Path to deployment database")
    
    args = parser.parse_args()
    
    db_path = Path(args.db_path) if args.db_path else None
    tracker = DeploymentTracker(db_path)
    
    if args.list:
        deployments = tracker.list_deployments()
        print("\nRecent Deployments:")
        print("=" * 80)
        for dep in deployments:
            print(f"ID: {dep['id']}")
            print(f"  Status: {dep['status']}")
            print(f"  Timestamp: {dep['timestamp']}")
            print(f"  Commit: {dep['commit_sha'][:7]}")
            print(f"  Branch: {dep['branch']}")
            if dep['duration_seconds']:
                print(f"  Duration: {dep['duration_seconds']}s")
            if dep['rollback_performed']:
                print(f"  Rollback: Yes")
            print()
        sys.exit(0)
    
    if args.metrics:
        metrics = tracker.get_metrics()
        print("\nDeployment Metrics:")
        print("=" * 80)
        print(f"Total Deployments: {metrics['total_deployments']}")
        print(f"Successful: {metrics['successful_deployments']}")
        print(f"Failed: {metrics['failed_deployments']}")
        print(f"Rollbacks: {metrics['rollbacks']}")
        print(f"Success Rate: {metrics['success_rate']}%")
        print(f"Average Duration: {metrics['average_duration_seconds']}s")
        print(f"Recent (7 days): {metrics['recent_deployments_7d']}")
        print()
        sys.exit(0)
    
    if not args.deployment_id or not args.status:
        parser.print_help()
        sys.exit(1)
    
    tracker.track_deployment(
        deployment_id=args.deployment_id,
        status=args.status,
        commit=args.commit or "unknown",
        branch=args.branch or "unknown",
        duration=args.duration,
        services_count=args.services_count,
        passed_checks=args.passed_checks,
        failed_checks=args.failed_checks,
        rollback_performed=args.rollback,
        notes=args.notes
    )
    
    print(f"✅ Deployment tracked: {args.deployment_id} ({args.status})")


if __name__ == "__main__":
    main()

