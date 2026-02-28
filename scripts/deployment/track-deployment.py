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
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")


class DeploymentTracker:
    """Tracks deployment history and metrics."""

    def __init__(self, pg_url: str = POSTGRES_URL):
        self.pg_url = pg_url
        self._init_database()

    def _get_conn(self):
        """Get a new database connection."""
        return psycopg2.connect(self.pg_url)

    def _init_database(self):
        """Initialize deployment tracking tables."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Create deployments table in core schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core.deployments (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                branch TEXT NOT NULL,
                duration_seconds INTEGER,
                services_count INTEGER,
                passed_checks INTEGER,
                failed_checks INTEGER,
                rollback_performed BOOLEAN DEFAULT FALSE,
                notes TEXT
            )
        """)

        # Create deployment_metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core.deployment_metrics (
                id SERIAL PRIMARY KEY,
                deployment_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (deployment_id) REFERENCES core.deployments(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployments_timestamp
            ON core.deployments(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployments_status
            ON core.deployments(status)
        """)

        conn.commit()
        conn.close()
        logger.info(f"Initialized deployment tracking tables in PostgreSQL")

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
        conn = self._get_conn()
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc)

        cursor.execute("""
            INSERT INTO core.deployments
            (id, timestamp, status, commit_sha, branch, duration_seconds,
             services_count, passed_checks, failed_checks, rollback_performed, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                timestamp = EXCLUDED.timestamp,
                status = EXCLUDED.status,
                commit_sha = EXCLUDED.commit_sha,
                branch = EXCLUDED.branch,
                duration_seconds = EXCLUDED.duration_seconds,
                services_count = EXCLUDED.services_count,
                passed_checks = EXCLUDED.passed_checks,
                failed_checks = EXCLUDED.failed_checks,
                rollback_performed = EXCLUDED.rollback_performed,
                notes = EXCLUDED.notes
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
            rollback_performed,
            notes
        ))

        conn.commit()
        conn.close()
        logger.info(f"Tracked deployment: {deployment_id} ({status})")

    def add_metric(self, deployment_id: str, metric_name: str, metric_value: float):
        """Add a metric for a deployment."""
        conn = self._get_conn()
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc)

        cursor.execute("""
            INSERT INTO core.deployment_metrics (deployment_id, metric_name, metric_value, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (deployment_id, metric_name, metric_value, timestamp))

        conn.commit()
        conn.close()
        logger.info(f"Added metric {metric_name}={metric_value} for deployment {deployment_id}")

    def list_deployments(self, limit: int = 10) -> List[Dict]:
        """List recent deployments."""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT * FROM core.deployments
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_metrics(self) -> Dict:
        """Get deployment metrics."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Total deployments
        cursor.execute("SELECT COUNT(*) FROM core.deployments")
        total_deployments = cursor.fetchone()[0]

        # Successful deployments
        cursor.execute("SELECT COUNT(*) FROM core.deployments WHERE status = 'success'")
        successful_deployments = cursor.fetchone()[0]

        # Failed deployments
        cursor.execute("SELECT COUNT(*) FROM core.deployments WHERE status = 'failure'")
        failed_deployments = cursor.fetchone()[0]

        # Rollbacks
        cursor.execute("SELECT COUNT(*) FROM core.deployments WHERE rollback_performed = true")
        rollbacks = cursor.fetchone()[0]

        # Average duration
        cursor.execute("""
            SELECT AVG(duration_seconds)
            FROM core.deployments
            WHERE duration_seconds IS NOT NULL
        """)
        avg_duration = cursor.fetchone()[0] or 0

        # Success rate
        success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0

        # Recent deployments (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM core.deployments
            WHERE timestamp > NOW() - INTERVAL '7 days'
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
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM core.deployments WHERE id = %s", (deployment_id,))
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
    parser.add_argument("--pg-url", help="PostgreSQL connection URL")

    args = parser.parse_args()

    pg_url = args.pg_url or POSTGRES_URL
    tracker = DeploymentTracker(pg_url)

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
