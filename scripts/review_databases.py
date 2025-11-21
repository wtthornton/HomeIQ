"""
Database Review Script
Reviews both InfluxDB and SQLite databases for schema correctness and data integrity.

This script:
1. Connects to InfluxDB and checks:
   - Buckets and their schemas
   - Recent data points
   - Field and tag structure
   - Data freshness

2. Connects to SQLite and checks:
   - Table schemas
   - Column definitions
   - Data counts
   - Foreign key relationships
   - Data freshness
"""

import asyncio
import builtins
import contextlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("ERROR: influxdb-client not installed. Install with: pip install influxdb-client")
    sys.exit(1)

try:
    import aiosqlite
except ImportError:
    print("ERROR: aiosqlite not installed. Install with: pip install aiosqlite")
    sys.exit(1)


class DatabaseReviewer:
    """Review both InfluxDB and SQLite databases"""

    def __init__(self):
        # InfluxDB configuration (from docker-compose.yml)
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        # Try multiple token options - admin token should work
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN") or "homeiq-token"
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "ha-ingestor")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        # Try to get token from docker container if not set
        if not os.getenv("INFLUXDB_TOKEN"):
            import subprocess
            try:
                result = subprocess.run(
                    ["docker", "exec", "homeiq-influxdb", "influx", "auth", "list", "--json"],
                    check=False, capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    import json
                    auths = json.loads(result.stdout)
                    if auths and len(auths) > 0:
                        # Use the first admin token
                        for auth in auths:
                            if auth.get("userName") == "admin":
                                self.influxdb_token = auth.get("token", "homeiq-token")
                                print(f"[INFO] Using InfluxDB token from container: {self.influxdb_token[:10]}...")
                                break
            except Exception as e:
                print(f"[WARNING] Could not get token from container: {e}")

        # SQLite configuration (from docker-compose.yml)
        # SQLite is in the data-api container at /app/data/metadata.db
        # We'll need to access it via docker exec or volume mount
        self.sqlite_path = os.getenv("SQLITE_PATH", None)

        self.issues = []
        self.warnings = []

    async def review_all(self):
        """Review both databases"""
        print("=" * 80)
        print("DATABASE REVIEW - HomeIQ")
        print("=" * 80)
        print(f"Review started at: {datetime.now().isoformat()}\n")

        # Review InfluxDB
        print("\n" + "=" * 80)
        print("INFLUXDB REVIEW")
        print("=" * 80)
        await self.review_influxdb()

        # Review SQLite
        print("\n" + "=" * 80)
        print("SQLITE REVIEW")
        print("=" * 80)
        await self.review_sqlite()

        # Print summary
        print("\n" + "=" * 80)
        print("REVIEW SUMMARY")
        print("=" * 80)
        self.print_summary()

    async def review_influxdb(self):
        """Review InfluxDB database"""
        try:
            client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org,
                timeout=30000,
            )

            # Check connection
            health = client.health()
            if health.status != "pass":
                self.issues.append(f"InfluxDB health check failed: {health.status}")
                print(f"[ERROR] InfluxDB health check: {health.status}")
                return
            print("[OK] InfluxDB connection: OK")

            # Get buckets
            buckets_api = client.buckets_api()
            buckets = buckets_api.find_buckets()

            print(f"\n[BUCKETS] Buckets found: {len(buckets.buckets)}")
            for bucket in buckets.buckets:
                print(f"  - {bucket.name} (ID: {bucket.id})")
                if bucket.retention_rules:
                    for rule in bucket.retention_rules:
                        print(f"    Retention: {rule.every_seconds // 86400}d")

            # Check primary bucket
            primary_bucket = None
            for bucket in buckets.buckets:
                if bucket.name == self.influxdb_bucket:
                    primary_bucket = bucket
                    break

            if not primary_bucket:
                self.issues.append(f"Primary bucket '{self.influxdb_bucket}' not found")
                print(f"\n[ERROR] Primary bucket '{self.influxdb_bucket}' not found")
                return

            print(f"\n[REVIEW] Reviewing bucket: {self.influxdb_bucket}")

            # Query recent data to check schema
            query_api = client.query_api()

            # Get recent measurements
            flux_query = f"""
            from(bucket: "{self.influxdb_bucket}")
              |> range(start: -1h)
              |> limit(n: 100)
            """

            try:
                result = query_api.query(flux_query)

                if not result:
                    self.warnings.append(f"No data found in bucket '{self.influxdb_bucket}' in the last hour")
                    print("[WARNING] No data found in the last hour")
                else:
                    # Analyze schema from results
                    measurements = set()
                    fields = set()
                    tags = set()
                    record_count = 0
                    latest_time = None

                    for table in result:
                        for record in table.records:
                            record_count += 1
                            measurements.add(record.get_measurement())

                            # Get fields
                            field = record.get_field()
                            if field:
                                fields.add(field)

                            # Get tags
                            for tag_key, tag_value in record.values.items():
                                if tag_key.startswith("_"):
                                    continue  # Skip internal fields
                                if tag_value is not None:
                                    tags.add(tag_key)

                            # Track latest time
                            time = record.get_time()
                            if latest_time is None or time > latest_time:
                                latest_time = time

                    print("\n[STATS] Data Statistics:")
                    print(f"  - Records in last hour: {record_count}")
                    print(f"  - Measurements: {', '.join(sorted(measurements))}")
                    print(f"  - Latest data point: {latest_time}")

                    if latest_time:
                        age = datetime.now(latest_time.tzinfo) - latest_time
                        if age > timedelta(minutes=10):
                            self.warnings.append(f"Latest data point is {age} old - data may not be updating")
                            print(f"  [WARNING] Data age: {age} (may not be updating)")
                        else:
                            print(f"  [OK] Data age: {age} (fresh)")

                    # Check for expected fields and tags
                    print(f"\n[TAGS] Tags found: {len(tags)}")
                    expected_tags = ["entity_id", "domain", "device_id", "area_id"]
                    for tag in sorted(tags)[:20]:  # Show first 20
                        marker = "[OK]" if tag in expected_tags else "[INFO]"
                        print(f"  {marker} {tag}")

                    print(f"\n[FIELDS] Fields found: {len(fields)}")
                    expected_fields = ["state_value", "previous_state", "context_id", "duration_in_state_seconds"]
                    for field in sorted(fields)[:20]:  # Show first 20
                        marker = "[OK]" if field in expected_fields else "[INFO]"
                        print(f"  {marker} {field}")

                    # Check for missing expected fields
                    missing_tags = set(expected_tags) - tags
                    if missing_tags:
                        self.warnings.append(f"Expected tags not found in recent data: {missing_tags}")

                    # Get sample data point
                    print("\n[SAMPLE] Sample Data Point:")
                    sample_query = f"""
                    from(bucket: "{self.influxdb_bucket}")
                      |> range(start: -1h)
                      |> limit(n: 1)
                    """
                    sample_result = query_api.query(sample_query)
                    if sample_result:
                        for table in sample_result:
                            for record in table.records:
                                print(f"  Measurement: {record.get_measurement()}")
                                print(f"  Time: {record.get_time()}")
                                print(f"  Field: {record.get_field()}")
                                print(f"  Value: {record.get_value()}")
                                print(f"  Tags: { {k: v for k, v in record.values.items() if not k.startswith('_') and v is not None} }")
                                break

            except Exception as e:
                self.issues.append(f"Error querying InfluxDB: {e!s}")
                print(f"[ERROR] Error querying InfluxDB: {e}")

            client.close()

        except Exception as e:
            self.issues.append(f"Error connecting to InfluxDB: {e!s}")
            print(f"[ERROR] Error connecting to InfluxDB: {e}")
            import traceback
            traceback.print_exc()

    async def review_sqlite(self):
        """Review SQLite database"""
        # Try to access SQLite via docker exec first
        # If that fails, try local path

        sqlite_accessible = False

        # Try docker exec
        import subprocess
        try:
            result = subprocess.run(
                ["docker", "exec", "homeiq-data-api", "ls", "/app/data/metadata.db"],
                check=False, capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print("[OK] SQLite database found in container")
                sqlite_accessible = True
                # Copy database locally for inspection
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_db_path = os.path.join(temp_dir, "metadata.db")
                subprocess.run(
                    ["docker", "cp", "homeiq-data-api:/app/data/metadata.db", temp_db_path],
                    timeout=10,
                    check=False,
                )
                db_path = temp_db_path
            else:
                print("[WARNING] SQLite database not found in container")
        except Exception as e:
            print(f"[WARNING] Could not access SQLite via docker: {e}")

        # Try local path if docker failed
        if not sqlite_accessible:
            if self.sqlite_path and Path(self.sqlite_path).exists():
                db_path = self.sqlite_path
                sqlite_accessible = True
            else:
                # Try common locations
                import tempfile
                temp_dir = tempfile.gettempdir()
                possible_paths = [
                    "data/metadata.db",
                    "services/data-api/data/metadata.db",
                    os.path.join(temp_dir, "metadata.db"),
                ]
                for path in possible_paths:
                    if Path(path).exists():
                        db_path = path
                        sqlite_accessible = True
                        break

        if not sqlite_accessible:
            self.issues.append("SQLite database not accessible - cannot review")
            print("[ERROR] SQLite database not accessible")
            print("   Tried:")
            print("   - Docker container: homeiq-data-api:/app/data/metadata.db")
            if self.sqlite_path:
                print(f"   - Custom path: {self.sqlite_path}")
            print("   - Common local paths")
            return

        try:
            async with aiosqlite.connect(db_path) as db:
                # Get table list
                cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in await cursor.fetchall()]

                print(f"\n[TABLES] Tables found: {len(tables)}")
                for table in tables:
                    print(f"  - {table}")

                # Check expected tables
                expected_tables = ["devices", "entities"]
                missing_tables = set(expected_tables) - set(tables)
                if missing_tables:
                    self.issues.append(f"Missing expected tables: {missing_tables}")
                    print(f"\n[ERROR] Missing tables: {missing_tables}")
                else:
                    print("\n[OK] All expected tables present")

                # Review each table
                for table in expected_tables:
                    if table not in tables:
                        continue

                    print(f"\n[REVIEW] Reviewing table: {table}")

                    # Get schema
                    cursor = await db.execute(f"PRAGMA table_info({table})")
                    columns = await cursor.fetchall()

                    print(f"  Columns ({len(columns)}):")
                    for col in columns:
                        _col_id, name, col_type, not_null, _default, pk = col
                        pk_marker = "[PK]" if pk else "    "
                        null_marker = "NOT NULL" if not_null else "NULL"
                        print(f"    {pk_marker} {name:20} {col_type:15} {null_marker}")

                    # Get row count
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                    count = (await cursor.fetchone())[0]
                    print(f"  Row count: {count}")

                    if count == 0:
                        self.warnings.append(f"Table '{table}' is empty")
                        print("  [WARNING] Table is empty")
                    else:
                        # Get sample row
                        cursor = await db.execute(f"SELECT * FROM {table} LIMIT 1")
                        sample = await cursor.fetchone()
                        if sample:
                            print(f"  Sample row keys: {[col[1] for col in columns]}")

                    # Check for foreign keys
                    if table == "entities":
                        cursor = await db.execute("PRAGMA foreign_key_list(entities)")
                        fks = await cursor.fetchall()
                        if fks:
                            print("  Foreign keys:")
                            for fk in fks:
                                print(f"    - {fk[3]} -> {fk[2]}.{fk[4]}")

                        # Check for orphaned entities
                        cursor = await db.execute("""
                            SELECT COUNT(*) FROM entities e
                            LEFT JOIN devices d ON e.device_id = d.device_id
                            WHERE e.device_id IS NOT NULL AND d.device_id IS NULL
                        """)
                        orphaned = (await cursor.fetchone())[0]
                        if orphaned > 0:
                            self.issues.append(f"Found {orphaned} orphaned entities (device_id references non-existent device)")
                            print(f"  [ERROR] Orphaned entities: {orphaned}")
                        else:
                            print("  [OK] No orphaned entities")

                    # Check data freshness
                    # For devices table, check last_seen instead of created_at
                    # For other tables, check created_at
                    freshness_field = "last_seen" if table == "devices" else "created_at"

                    if freshness_field in [col[1] for col in columns]:
                        cursor = await db.execute(f"SELECT MAX({freshness_field}) FROM {table}")
                        latest = (await cursor.fetchone())[0]
                        if latest:
                            print(f"  Latest {freshness_field}: {latest}")
                            # Parse timestamp
                            try:
                                if isinstance(latest, str):
                                    latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                                else:
                                    latest_dt = latest
                                age = datetime.now(latest_dt.tzinfo if latest_dt.tzinfo else None) - latest_dt.replace(tzinfo=None)
                                if age > timedelta(days=1):
                                    self.warnings.append(f"Table '{table}' latest {freshness_field} is {age} old")
                                    print(f"  [WARNING] Data age: {age}")
                                else:
                                    print("  [OK] Data is fresh")
                            except Exception as e:
                                print(f"  [WARNING] Could not parse timestamp: {e}")

                    # Also show created_at for devices table for reference
                    if table == "devices" and "created_at" in [col[1] for col in columns]:
                        cursor = await db.execute(f"SELECT MAX(created_at) FROM {table}")
                        latest = (await cursor.fetchone())[0]
                        if latest:
                            print(f"  Latest created_at: {latest} (reference only - check last_seen for freshness)")

                # Check indexes
                print("\n[INDEXES] Indexes:")
                cursor = await db.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                indexes = await cursor.fetchall()
                for idx_name, tbl_name in indexes:
                    print(f"  - {idx_name} on {tbl_name}")

                # Check database integrity
                print("\n[INTEGRITY] Database Integrity:")
                cursor = await db.execute("PRAGMA integrity_check")
                integrity = await cursor.fetchone()
                if integrity[0] == "ok":
                    print("  [OK] Integrity check: OK")
                else:
                    self.issues.append(f"Database integrity check failed: {integrity[0]}")
                    print(f"  [ERROR] Integrity check: {integrity[0]}")

                # Check WAL mode
                cursor = await db.execute("PRAGMA journal_mode")
                journal_mode = (await cursor.fetchone())[0]
                if journal_mode == "wal":
                    print("  [OK] Journal mode: WAL (optimal)")
                else:
                    self.warnings.append(f"Journal mode is '{journal_mode}', should be 'wal' for better concurrency")
                    print(f"  [WARNING] Journal mode: {journal_mode} (should be 'wal')")

        except Exception as e:
            self.issues.append(f"Error reviewing SQLite: {e!s}")
            print(f"[ERROR] Error reviewing SQLite: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up temp file if we copied it
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_db_path = os.path.join(temp_dir, "metadata.db")
            if db_path == temp_db_path and Path(db_path).exists():
                with contextlib.suppress(builtins.BaseException):
                    Path(db_path).unlink()

    def print_summary(self):
        """Print review summary"""
        print(f"\nTotal Issues Found: {len(self.issues)}")
        print(f"Total Warnings: {len(self.warnings)}")

        if self.issues:
            print("\n[ISSUES] ISSUES (Require Attention):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

        if self.warnings:
            print("\n[WARNINGS] WARNINGS (Should Review):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        if not self.issues and not self.warnings:
            print("\n[OK] No issues or warnings found - databases look healthy!")


async def main():
    """Main entry point"""
    reviewer = DatabaseReviewer()
    await reviewer.review_all()

    # Exit with error code if issues found
    if reviewer.issues:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

