"""
Orchestration runner for quality checks.
Uses dispatch table pattern for check selection.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from influxdb_client import InfluxDBClient

from .config import SQLITE_CHECKS, INFLUXDB_CHECKS
from .db_common import find_database_path, get_database_config
from .influxdb_common import get_influxdb_config
from .sqlite_checks import (
    get_all_tables,
    check_table_basics,
    check_null_values,
    check_orphaned_records,
    check_table_specific,
)
from .influxdb_checks import (
    check_connection,
    check_buckets,
    check_data_volume,
    check_measurements,
    check_data_gaps,
    check_tag_cardinality,
    check_schema_consistency,
)


@dataclass
class CheckResult:
    """Result of a quality check."""
    check_name: str
    issues: List[str]
    warnings: List[str]
    info: List[str]
    success: bool = True


@dataclass
class DatabaseCheckResults:
    """Results for a database check."""
    db_name: str
    db_path: str
    checks: List[CheckResult]
    total_issues: int = 0
    total_warnings: int = 0
    error: Optional[str] = None


class SQLiteCheckRunner:
    """Runner for SQLite database quality checks."""
    
    def __init__(self, enabled_checks: Optional[Set[str]] = None):
        self.enabled_checks = enabled_checks or set(SQLITE_CHECKS)
        self.check_dispatch = {
            'tables': self._check_tables,
            'null_values': self._check_null_values,
            'foreign_keys': self._check_foreign_keys,
            'indexes': self._check_indexes,
            'vacuum': self._check_vacuum,
            'integrity': self._check_integrity,
            'orphaned': self._check_orphaned,
            'table_specific': self._check_table_specific,
        }
    
    async def run_checks(self, db_key: str, db_path: Path, db_name: str) -> DatabaseCheckResults:
        """Run all enabled checks on a database."""
        results = DatabaseCheckResults(
            db_name=db_name,
            db_path=str(db_path),
            checks=[]
        )
        
        abs_path = db_path.resolve()
        database_url = f"sqlite+aiosqlite:///{abs_path}"
        engine = create_async_engine(database_url, echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as db:
                for check_name in self.enabled_checks:
                    if check_name in self.check_dispatch:
                        check_func = self.check_dispatch[check_name]
                        check_result = await check_func(db, db_name)
                        results.checks.append(check_result)
                        results.total_issues += len(check_result.issues)
                        results.total_warnings += len(check_result.warnings)
            
            await engine.dispose()
        except Exception as e:
            results.error = str(e)
            results.checks.append(CheckResult(
                check_name='error',
                issues=[f"Error running checks: {e}"],
                warnings=[],
                info=[],
                success=False
            ))
        
        return results
    
    async def _check_tables(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check table basics."""
        issues = []
        warnings = []
        info = []
        
        tables = await get_all_tables(db)
        info.append(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        for table in tables:
            row_count, table_info = await check_table_basics(db, table)
            info.extend(table_info)
            if row_count == 0:
                warnings.append(f"{table}: Empty table")
        
        return CheckResult('tables', issues, warnings, info)
    
    async def _check_null_values(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check for NULL values in NOT NULL columns."""
        issues = []
        warnings = []
        info = []
        
        tables = await get_all_tables(db)
        for table in tables:
            table_issues, table_warnings = await check_null_values(db, table)
            issues.extend(table_issues)
            warnings.extend(table_warnings)
        
        return CheckResult('null_values', issues, warnings, info)
    
    async def _check_foreign_keys(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check foreign key integrity."""
        issues = []
        warnings = []
        info = []
        
        # SQLite doesn't enforce foreign keys by default
        info.append("Foreign key checks: SQLite doesn't enforce foreign keys by default")
        
        return CheckResult('foreign_keys', issues, warnings, info)
    
    async def _check_indexes(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check indexes."""
        issues = []
        warnings = []
        info = []
        
        # Placeholder for index checks
        info.append("Index checks: Not implemented yet")
        
        return CheckResult('indexes', issues, warnings, info)
    
    async def _check_vacuum(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check if vacuum is needed."""
        issues = []
        warnings = []
        info = []
        
        # Placeholder for vacuum checks
        info.append("Vacuum checks: Not implemented yet")
        
        return CheckResult('vacuum', issues, warnings, info)
    
    async def _check_integrity(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check database integrity."""
        issues = []
        warnings = []
        info = []
        
        try:
            result = await db.execute(text("PRAGMA integrity_check"))
            integrity_result = result.scalar()
            if integrity_result == "ok":
                info.append("Database integrity: OK")
            else:
                issues.append(f"Database integrity check failed: {integrity_result}")
        except Exception as e:
            warnings.append(f"Could not check integrity: {e}")
        
        return CheckResult('integrity', issues, warnings, info)
    
    async def _check_orphaned(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check for orphaned records."""
        issues = []
        warnings = []
        info = []
        
        tables = await get_all_tables(db)
        for table in tables:
            # Check common orphaned patterns
            if table == 'suggestions':
                orphaned = await check_orphaned_records(db, 'suggestions', 'pattern_id', 'patterns')
                issues.extend(orphaned)
        
        return CheckResult('orphaned', issues, warnings, info)
    
    async def _check_table_specific(self, db: AsyncSession, db_name: str) -> CheckResult:
        """Check table-specific issues."""
        issues = []
        warnings = []
        info = []
        
        tables = await get_all_tables(db)
        for table in tables:
            table_issues, table_warnings = await check_table_specific(db, table)
            issues.extend(table_issues)
            warnings.extend(table_warnings)
        
        return CheckResult('table_specific', issues, warnings, info)


class InfluxDBCheckRunner:
    """Runner for InfluxDB quality checks."""
    
    def __init__(self, enabled_checks: Optional[Set[str]] = None):
        self.enabled_checks = enabled_checks or set(INFLUXDB_CHECKS)
        self.check_dispatch = {
            'connection': self._check_connection,
            'buckets': self._check_buckets,
            'data_volume': self._check_data_volume,
            'measurements': self._check_measurements,
            'data_gaps': self._check_data_gaps,
            'shards': self._check_shards,
            'retention': self._check_retention,
            'schema': self._check_schema,
        }
    
    def run_checks(self) -> List[CheckResult]:
        """Run all enabled checks."""
        config = get_influxdb_config()
        client = InfluxDBClient(
            url=config['url'],
            token=config['token'],
            org=config['org'],
            timeout=30000
        )
        
        results = []
        
        try:
            for check_name in self.enabled_checks:
                if check_name in self.check_dispatch:
                    check_func = self.check_dispatch[check_name]
                    check_result = check_func(client, config['bucket'])
                    results.append(check_result)
        finally:
            client.close()
        
        return results
    
    def _check_connection(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check InfluxDB connection."""
        issues = []
        warnings = []
        info = []
        
        success, conn_issues = check_connection(client)
        issues.extend(conn_issues)
        if success:
            info.append("Connection: Healthy")
        
        return CheckResult('connection', issues, warnings, info, success)
    
    def _check_buckets(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check bucket configuration."""
        issues = []
        warnings = []
        info = []
        
        bucket_info, bucket_issues, bucket_warnings = check_buckets(client, bucket)
        issues.extend(bucket_issues)
        warnings.extend(bucket_warnings)
        info.append(f"Found {len(bucket_info)} bucket(s)")
        
        return CheckResult('buckets', issues, warnings, info)
    
    def _check_data_volume(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check data volume."""
        issues = []
        warnings = []
        info = []
        
        volumes, volume_issues, volume_warnings = check_data_volume(client, bucket)
        issues.extend(volume_issues)
        warnings.extend(volume_warnings)
        for period, count in volumes.items():
            info.append(f"Last {period}: {count:,} records")
        
        return CheckResult('data_volume', issues, warnings, info)
    
    def _check_measurements(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check measurements."""
        issues = []
        warnings = []
        info = []
        
        measurements, counts, meas_issues, meas_warnings = check_measurements(client, bucket)
        issues.extend(meas_issues)
        warnings.extend(meas_warnings)
        info.append(f"Found {len(measurements)} measurement(s)")
        
        return CheckResult('measurements', issues, warnings, info)
    
    def _check_data_gaps(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check for data gaps."""
        issues = []
        warnings = []
        info = []
        
        gap_count, gap_warnings = check_data_gaps(client, bucket)
        warnings.extend(gap_warnings)
        if gap_count == 0:
            info.append("No data gaps in last 24 hours")
        else:
            info.append(f"Found {gap_count} hour(s) with no data")
        
        return CheckResult('data_gaps', issues, warnings, info)
    
    def _check_shards(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check shard configuration."""
        issues = []
        warnings = []
        info = []
        
        # Placeholder for shard checks
        info.append("Shard checks: Not implemented yet")
        
        return CheckResult('shards', issues, warnings, info)
    
    def _check_retention(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check retention policies."""
        issues = []
        warnings = []
        info = []
        
        # Retention is checked in buckets check
        info.append("Retention policies: Checked in buckets check")
        
        return CheckResult('retention', issues, warnings, info)
    
    def _check_schema(self, client: InfluxDBClient, bucket: str) -> CheckResult:
        """Check schema consistency."""
        issues = []
        warnings = []
        info = []
        
        field_counts, tag_counts, schema_warnings = check_schema_consistency(client, bucket)
        warnings.extend(schema_warnings)
        
        for measurement in sorted(set(list(field_counts.keys()) + list(tag_counts.keys()))):
            fields = field_counts.get(measurement, set())
            tags = tag_counts.get(measurement, set())
            info.append(f"{measurement}: {len(fields)} fields, {len(tags)} tags")
        
        return CheckResult('schema', issues, warnings, info)

