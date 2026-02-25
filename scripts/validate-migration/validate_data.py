"""
SQLite to PostgreSQL Migration Data Integrity Validator

Validates data integrity between SQLite source databases and PostgreSQL
target schemas after migration. Checks row counts, sample checksums,
table existence, primary key sequences, foreign keys, and indexes.

Usage:
    python scripts/validate-migration/validate_data.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq \
        --sqlite-dir ./data/

    # Dry run (show what would be validated without connecting)
    python scripts/validate-migration/validate_data.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq \
        --sqlite-dir ./data/ --dry-run

    # Validate a single schema
    python scripts/validate-migration/validate_data.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq \
        --sqlite-dir ./data/ --schemas core
"""

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import aiosqlite
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema-to-SQLite mapping (mirrors run_all.sh)
# ---------------------------------------------------------------------------
SCHEMA_MAP: dict[str, list[dict[str, str | list[str]]]] = {
    "core": [
        {
            "db": "metadata.db",
            "tables": [
                "devices",
                "entities",
                "automations",
                "automation_executions",
                "services",
                "statistics_meta",
                "user_team_preferences",
            ],
        },
    ],
    "automation": [
        {
            "db": "ai_automation.db",
            "tables": [
                "suggestions",
                "automation_versions",
                "plans",
                "compiled_artifacts",
                "deployments",
            ],
        },
    ],
    "agent": [
        {
            "db": "ha_ai_agent.db",
            "tables": [
                "context_cache",
                "conversations",
                "messages",
            ],
        },
    ],
    "blueprints": [
        {
            "db": "blueprint_index.db",
            "tables": ["indexed_blueprints"],
        },
        {
            "db": "blueprint_suggestions.db",
            "tables": ["blueprint_suggestions"],
        },
        {
            "db": "miner.db",
            "tables": ["community_automations", "miner_state"],
        },
    ],
    "energy": [
        {
            "db": "proactive_agent.db",
            "tables": ["suggestions", "invalid_suggestion_reports"],
        },
    ],
    "devices": [
        {
            "db": "device_intelligence.db",
            "tables": ["device_intelligence"],
        },
        {
            "db": "ha-setup.db",
            "tables": ["setup_sessions"],
        },
    ],
    "patterns": [
        {
            "db": "api-automation-edge.db",
            "tables": ["spec_versions"],
        },
    ],
    "rag": [
        {
            "db": "rag_service.db",
            "tables": ["rag_knowledge"],
        },
    ],
}

CHECKSUM_SAMPLE_SIZE = 100


# ---------------------------------------------------------------------------
# Data classes for structured results
# ---------------------------------------------------------------------------
@dataclass
class TableResult:
    """Validation result for a single table."""

    table: str
    schema: str
    sqlite_db: str
    checks: dict[str, dict] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.get("status") == "pass" for c in self.checks.values())


@dataclass
class SchemaResult:
    """Validation result for an entire schema."""

    schema: str
    tables: list[TableResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and all(t.passed for t in self.tables)


@dataclass
class ValidationReport:
    """Top-level validation report."""

    schemas: list[SchemaResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.schemas)

    def to_dict(self) -> dict:
        result = {
            "overall": "pass" if self.passed else "FAIL",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "schemas": {},
        }
        for sr in self.schemas:
            schema_data: dict = {
                "status": "pass" if sr.passed else "FAIL",
                "errors": sr.errors,
                "tables": {},
            }
            for tr in sr.tables:
                schema_data["tables"][tr.table] = {
                    "sqlite_db": tr.sqlite_db,
                    "status": "pass" if tr.passed else "FAIL",
                    "checks": tr.checks,
                }
            result["schemas"][sr.schema] = schema_data
        return result


# ---------------------------------------------------------------------------
# Helper: parse asyncpg-compatible DSN from SQLAlchemy-style URL
# ---------------------------------------------------------------------------
def parse_pg_dsn(url: str) -> str:
    """Convert a SQLAlchemy-style postgresql+asyncpg:// URL to a plain DSN.

    asyncpg.connect() expects ``postgresql://`` or keyword args, not the
    ``+asyncpg`` dialect suffix used by SQLAlchemy.
    """
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------
async def _check_table_exists(
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Check if a table exists in the PostgreSQL schema.

    Args:
        pg_conn: Open asyncpg connection.
        schema: PostgreSQL schema name.
        table: Table name to check.

    Returns:
        Dict with 'status' ('pass'/'FAIL') and 'exists' boolean.
    """
    row = await pg_conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = $1
              AND table_name = $2
        )
        """,
        schema,
        table,
    )
    exists = bool(row)
    return {
        "status": "pass" if exists else "FAIL",
        "exists": exists,
    }


async def _check_row_counts(
    sqlite_conn: aiosqlite.Connection,
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Compare row counts between SQLite and PostgreSQL.

    Args:
        sqlite_conn: Open aiosqlite connection to source database.
        pg_conn: Open asyncpg connection to target database.
        schema: PostgreSQL schema name (from SCHEMA_MAP, not user input).
        table: Table name (from SCHEMA_MAP, not user input).

    Returns:
        Dict with status, counts, and difference.
    """
    # Schema/table names come from SCHEMA_MAP constants, not user input
    cursor = await sqlite_conn.execute(f"SELECT COUNT(*) FROM [{table}]")  # nosec B608
    sqlite_row = await cursor.fetchone()
    sqlite_count = sqlite_row[0] if sqlite_row else 0

    pg_count = await pg_conn.fetchval(
        f'SELECT COUNT(*) FROM "{schema}"."{table}"'  # nosec B608
    )

    match = sqlite_count == pg_count
    return {
        "status": "pass" if match else "FAIL",
        "sqlite_count": sqlite_count,
        "pg_count": pg_count,
        "difference": pg_count - sqlite_count,
    }


def _row_hash(rows: list) -> str:
    """Compute a SHA-256 hash over a list of row tuples."""
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(repr(row).encode("utf-8"))
    return hasher.hexdigest()


async def _get_sqlite_table_columns(
    sqlite_conn: aiosqlite.Connection,
    table: str,
) -> list[str]:
    """Get column names for a SQLite table."""
    cursor = await sqlite_conn.execute(f"PRAGMA table_info([{table}])")
    info_rows = await cursor.fetchall()
    return [r[1] for r in info_rows]


async def _check_sample_checksums(
    sqlite_conn: aiosqlite.Connection,
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Hash first N and last N rows from both databases and compare.

    The comparison orders rows by the first column (usually the PK) to
    ensure deterministic ordering on both sides.

    Args:
        sqlite_conn: Open aiosqlite connection to source database.
        pg_conn: Open asyncpg connection to target database.
        schema: PostgreSQL schema name (from SCHEMA_MAP constants).
        table: Table name (from SCHEMA_MAP constants).

    Returns:
        Dict with status, match booleans, and truncated hash values.
    """
    columns = await _get_sqlite_table_columns(sqlite_conn, table)
    if not columns:
        return {"status": "FAIL", "reason": "no_columns"}

    order_col = columns[0]
    col_list_sqlite = ", ".join(f"[{c}]" for c in columns)
    col_list_pg = ", ".join(f'"{c}"' for c in columns)
    n = CHECKSUM_SAMPLE_SIZE

    # All identifiers below come from SCHEMA_MAP constants / PRAGMA table_info,
    # never from user input, so string formatting is safe here.

    # --- SQLite first/last N ---
    cursor_first = await sqlite_conn.execute(  # nosec B608
        f"SELECT {col_list_sqlite} FROM [{table}] ORDER BY [{order_col}] ASC LIMIT {n}"
    )
    sqlite_first = await cursor_first.fetchall()

    cursor_last = await sqlite_conn.execute(  # nosec B608
        f"SELECT {col_list_sqlite} FROM [{table}] ORDER BY [{order_col}] DESC LIMIT {n}"
    )
    sqlite_last = await cursor_last.fetchall()

    # --- PostgreSQL first/last N ---
    pg_first_rows = await pg_conn.fetch(  # nosec B608
        f'SELECT {col_list_pg} FROM "{schema}"."{table}" ORDER BY "{order_col}" ASC LIMIT {n}'
    )
    pg_first = [tuple(r.values()) for r in pg_first_rows]

    pg_last_rows = await pg_conn.fetch(  # nosec B608
        f'SELECT {col_list_pg} FROM "{schema}"."{table}" ORDER BY "{order_col}" DESC LIMIT {n}'
    )
    pg_last = [tuple(r.values()) for r in pg_last_rows]

    hash_sqlite_first = _row_hash(sqlite_first)
    hash_sqlite_last = _row_hash(sqlite_last)
    hash_pg_first = _row_hash(pg_first)
    hash_pg_last = _row_hash(pg_last)

    first_match = hash_sqlite_first == hash_pg_first
    last_match = hash_sqlite_last == hash_pg_last

    ok = first_match and last_match
    return {
        "status": "pass" if ok else "FAIL",
        "first_n_match": first_match,
        "last_n_match": last_match,
        "sample_size": n,
        "sqlite_first_hash": hash_sqlite_first[:16],
        "pg_first_hash": hash_pg_first[:16],
        "sqlite_last_hash": hash_sqlite_last[:16],
        "pg_last_hash": hash_pg_last[:16],
    }


async def _check_pk_sequences(
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Verify auto-increment sequences start at max(pk) + 1.

    Only relevant for tables with a serial/identity integer PK.
    Reads the current sequence value and compares it to the maximum
    existing PK value to ensure new inserts will not collide.

    Args:
        pg_conn: Open asyncpg connection.
        schema: PostgreSQL schema name.
        table: Table name.

    Returns:
        Dict with status and per-column sequence details.
    """
    # Find integer PK columns that use a sequence
    pk_cols = await pg_conn.fetch(
        """
        SELECT a.attname, pg_get_serial_sequence($1 || '.' || $2, a.attname) AS seq
        FROM pg_attribute a
        JOIN pg_index i ON i.indrelid = a.attrelid AND a.attnum = ANY(i.indkey)
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = $1
          AND c.relname = $2
          AND i.indisprimary
          AND a.atttypid IN (
              'int2'::regtype, 'int4'::regtype, 'int8'::regtype
          )
        """,
        schema,
        table,
    )

    if not pk_cols:
        return {"status": "pass", "reason": "no_serial_pk"}

    results = {}
    all_ok = True
    for row in pk_cols:
        col = row["attname"]
        seq = row["seq"]
        if not seq:
            results[col] = "no_sequence"
            continue

        # Sequence/schema/table names from pg_catalog, not user input
        max_val = await pg_conn.fetchval(  # nosec B608
            f'SELECT COALESCE(MAX("{col}"), 0) FROM "{schema}"."{table}"'
        )
        next_val = await pg_conn.fetchval(f"SELECT nextval('{seq}')")  # nosec B608
        # Reset to keep sequence in a valid state
        await pg_conn.execute(f"SELECT setval('{seq}', {next_val})")  # nosec B608

        ok = next_val >= max_val + 1
        if not ok:
            all_ok = False
        results[col] = {
            "max_value": max_val,
            "next_sequence": next_val,
            "valid": ok,
        }

    return {
        "status": "pass" if all_ok else "FAIL",
        "columns": results,
    }


async def _check_foreign_keys(
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Verify that all FK references are satisfied (no orphan rows).

    Queries information_schema for foreign key constraints, then checks
    each one for rows that reference non-existent parent rows.

    Args:
        pg_conn: Open asyncpg connection.
        schema: PostgreSQL schema name.
        table: Table name.

    Returns:
        Dict with status, count of FKs checked, and violation details.
    """
    fk_rows = await pg_conn.fetch(
        """
        SELECT
            kcu.column_name,
            ccu.table_schema AS ref_schema,
            ccu.table_name   AS ref_table,
            ccu.column_name  AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = $1
          AND tc.table_name = $2
        """,
        schema,
        table,
    )

    if not fk_rows:
        return {"status": "pass", "foreign_keys": [], "reason": "no_fks"}

    violations: list[dict] = []
    for fk in fk_rows:
        col = fk["column_name"]
        ref_schema = fk["ref_schema"]
        ref_table = fk["ref_table"]
        ref_col = fk["ref_column"]

        # All identifiers from information_schema, not user input
        orphan_count = await pg_conn.fetchval(  # nosec B608
            f"""
            SELECT COUNT(*) FROM "{schema}"."{table}" t
            WHERE t."{col}" IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM "{ref_schema}"."{ref_table}" r
                WHERE r."{ref_col}" = t."{col}"
              )
            """
        )
        if orphan_count > 0:
            violations.append(
                {
                    "column": col,
                    "references": f"{ref_schema}.{ref_table}.{ref_col}",
                    "orphan_rows": orphan_count,
                }
            )

    ok = len(violations) == 0
    return {
        "status": "pass" if ok else "FAIL",
        "foreign_keys_checked": len(fk_rows),
        "violations": violations,
    }


async def _check_indexes(
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
) -> dict:
    """Verify that expected indexes exist on the PostgreSQL table.

    Args:
        pg_conn: Open asyncpg connection.
        schema: PostgreSQL schema name.
        table: Table name.

    Returns:
        Dict with status, index count, PK index presence, and index names.
    """
    rows = await pg_conn.fetch(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = $1
          AND tablename = $2
        """,
        schema,
        table,
    )

    index_names = [r["indexname"] for r in rows]
    has_pk_index = any("pkey" in n for n in index_names)

    return {
        "status": "pass" if rows else "FAIL",
        "index_count": len(rows),
        "has_primary_key_index": has_pk_index,
        "indexes": index_names,
    }


# ---------------------------------------------------------------------------
# Main per-table validation
# ---------------------------------------------------------------------------
async def validate_table(
    sqlite_conn: aiosqlite.Connection,
    pg_conn: asyncpg.Connection,
    schema: str,
    table: str,
    sqlite_db_name: str,
) -> TableResult:
    """Run all six validation checks on a single table.

    Checks performed: table existence, row counts, sample checksums,
    PK sequence correctness, foreign key integrity, and index existence.

    Args:
        sqlite_conn: Open aiosqlite connection to source database.
        pg_conn: Open asyncpg connection to target database.
        schema: PostgreSQL schema name.
        table: Table name.
        sqlite_db_name: Source SQLite filename (for reporting).

    Returns:
        TableResult with per-check pass/fail results.
    """
    result = TableResult(table=table, schema=schema, sqlite_db=sqlite_db_name)

    # 1. Table existence
    exist_check = await _check_table_exists(pg_conn, schema, table)
    result.checks["table_exists"] = exist_check
    if not exist_check.get("exists"):
        logger.error(
            "  FAIL: %s.%s does not exist in PostgreSQL", schema, table
        )
        return result

    # 2. Row counts
    try:
        result.checks["row_counts"] = await _check_row_counts(
            sqlite_conn, pg_conn, schema, table
        )
    except Exception as exc:
        result.checks["row_counts"] = {"status": "FAIL", "error": str(exc)}
        logger.warning("  Row count check failed for %s.%s: %s", schema, table, exc)

    # 3. Sample checksums (skip if no rows)
    row_data = result.checks.get("row_counts", {})
    if row_data.get("sqlite_count", 0) > 0:
        try:
            result.checks["sample_checksums"] = await _check_sample_checksums(
                sqlite_conn, pg_conn, schema, table
            )
        except Exception as exc:
            result.checks["sample_checksums"] = {
                "status": "FAIL",
                "error": str(exc),
            }
            logger.warning(
                "  Checksum check failed for %s.%s: %s", schema, table, exc
            )
    else:
        result.checks["sample_checksums"] = {
            "status": "pass",
            "reason": "empty_table",
        }

    # 4. PK sequence validation
    try:
        result.checks["pk_sequences"] = await _check_pk_sequences(
            pg_conn, schema, table
        )
    except Exception as exc:
        result.checks["pk_sequences"] = {"status": "FAIL", "error": str(exc)}
        logger.warning(
            "  PK sequence check failed for %s.%s: %s", schema, table, exc
        )

    # 5. Foreign key integrity
    try:
        result.checks["foreign_keys"] = await _check_foreign_keys(
            pg_conn, schema, table
        )
    except Exception as exc:
        result.checks["foreign_keys"] = {"status": "FAIL", "error": str(exc)}
        logger.warning("  FK check failed for %s.%s: %s", schema, table, exc)

    # 6. Index existence
    try:
        result.checks["indexes"] = await _check_indexes(
            pg_conn, schema, table
        )
    except Exception as exc:
        result.checks["indexes"] = {"status": "FAIL", "error": str(exc)}
        logger.warning(
            "  Index check failed for %s.%s: %s", schema, table, exc
        )

    status = "PASS" if result.passed else "FAIL"
    logger.info("  %s: %s.%s", status, schema, table)
    return result


# ---------------------------------------------------------------------------
# Schema-level orchestration
# ---------------------------------------------------------------------------
async def validate_schema(
    pg_dsn: str,
    sqlite_dir: Path,
    schema: str,
    db_entries: list[dict],
) -> SchemaResult:
    """Validate all tables within a single schema."""
    sr = SchemaResult(schema=schema)

    pg_conn = await asyncpg.connect(pg_dsn)
    try:
        for entry in db_entries:
            db_file = sqlite_dir / entry["db"]
            tables = entry["tables"]

            if not db_file.exists():
                msg = f"SQLite file not found: {db_file}"
                logger.warning("  SKIP: %s", msg)
                sr.errors.append(msg)
                continue

            sqlite_conn = await aiosqlite.connect(str(db_file))
            sqlite_conn.row_factory = None  # raw tuples
            try:
                for table in tables:
                    # Verify table exists in SQLite before comparing
                    cursor = await sqlite_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table,),
                    )
                    sqlite_table_row = await cursor.fetchone()
                    if not sqlite_table_row:
                        logger.warning(
                            "  SKIP: Table '%s' not in SQLite file %s",
                            table,
                            db_file.name,
                        )
                        sr.errors.append(
                            f"Table '{table}' not found in {db_file.name}"
                        )
                        continue

                    tr = await validate_table(
                        sqlite_conn, pg_conn, schema, table, str(db_file.name)
                    )
                    sr.tables.append(tr)
            finally:
                await sqlite_conn.close()
    finally:
        await pg_conn.close()

    return sr


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------
def dry_run_report(sqlite_dir: Path, schemas: list[str]) -> None:
    """Print what would be validated without connecting to databases."""
    logger.info("=== DRY RUN: Validation Plan ===")
    for schema in schemas:
        entries = SCHEMA_MAP.get(schema, [])
        logger.info("Schema: %s", schema)
        for entry in entries:
            db_path = sqlite_dir / entry["db"]
            exists = db_path.exists()
            status = "exists" if exists else "MISSING"
            logger.info("  SQLite: %s (%s)", entry["db"], status)
            for table in entry["tables"]:
                logger.info("    - %s", table)
    logger.info("=== End DRY RUN ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate data integrity between SQLite source databases "
            "and PostgreSQL target schemas after migration."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --postgres-url postgresql+asyncpg://u:p@host/homeiq --sqlite-dir ./data/\n"
            "  %(prog)s --postgres-url postgresql+asyncpg://u:p@host/homeiq --sqlite-dir ./data/ --schemas core agent\n"
            "  %(prog)s --postgres-url postgresql+asyncpg://u:p@host/homeiq --sqlite-dir ./data/ --dry-run\n"
        ),
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="PostgreSQL connection URL (e.g. postgresql+asyncpg://user:pass@host:5432/homeiq)",
    )
    parser.add_argument(
        "--sqlite-dir",
        required=True,
        help="Directory containing SQLite database files",
    )
    parser.add_argument(
        "--schemas",
        nargs="*",
        default=list(SCHEMA_MAP.keys()),
        choices=list(SCHEMA_MAP.keys()),
        help="Schemas to validate (default: all)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON report to file (default: stdout)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show validation plan without connecting to databases",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def _run_all_schemas(
    pg_dsn: str,
    sqlite_dir: Path,
    schemas: list[str],
) -> ValidationReport:
    """Validate all requested schemas and return a complete report.

    Args:
        pg_dsn: asyncpg-compatible PostgreSQL DSN.
        sqlite_dir: Directory containing SQLite database files.
        schemas: List of schema names to validate.

    Returns:
        Populated ValidationReport instance.
    """
    report = ValidationReport(started_at=datetime.utcnow().isoformat())

    for schema in schemas:
        entries = SCHEMA_MAP.get(schema)
        if not entries:
            logger.warning("Unknown schema: %s", schema)
            continue

        logger.info("--- Validating schema: %s ---", schema)
        sr = await validate_schema(pg_dsn, sqlite_dir, schema, entries)
        report.schemas.append(sr)

        status = "PASS" if sr.passed else "FAIL"
        logger.info("Schema %s: %s", schema, status)
        logger.info("")

    report.finished_at = datetime.utcnow().isoformat()
    return report


def _write_report(report: ValidationReport, output_path: str | None) -> dict:
    """Serialize the report to JSON and optionally write to file.

    Args:
        report: Completed validation report.
        output_path: File path to write JSON report, or None for stdout.

    Returns:
        The report as a dict.
    """
    report_dict = report.to_dict()
    report_json = json.dumps(report_dict, indent=2, default=str)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report_json, encoding="utf-8")
        logger.info("Report written to: %s", out)
    else:
        print(report_json)

    return report_dict


def _log_summary(report: ValidationReport, report_dict: dict) -> None:
    """Log a human-readable summary of validation results.

    Args:
        report: Completed validation report.
        report_dict: Serialized report dict (for the overall status string).
    """
    total_tables = sum(len(sr.tables) for sr in report.schemas)
    passed_tables = sum(
        sum(1 for t in sr.tables if t.passed) for sr in report.schemas
    )
    failed_tables = total_tables - passed_tables

    logger.info("=== Validation Summary ===")
    logger.info(
        "Overall: %s | Tables: %d/%d passed | Schemas: %d",
        report_dict["overall"],
        passed_tables,
        total_tables,
        len(report.schemas),
    )

    if failed_tables > 0:
        logger.error(
            "%d table(s) FAILED validation. See report for details.",
            failed_tables,
        )


async def async_main() -> int:
    """Async entry point -- parse args, run validation, output results."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    sqlite_dir = Path(args.sqlite_dir)
    if not sqlite_dir.is_dir():
        logger.error("SQLite directory does not exist: %s", sqlite_dir)
        return 1

    if args.dry_run:
        dry_run_report(sqlite_dir, args.schemas)
        return 0

    pg_dsn = parse_pg_dsn(args.postgres_url)

    logger.info("=== HomeIQ Migration Data Validation ===")
    logger.info("PostgreSQL: %s", args.postgres_url.split("@")[-1])
    logger.info("SQLite dir: %s", sqlite_dir)
    logger.info("Schemas: %s", ", ".join(args.schemas))
    logger.info("")

    report = await _run_all_schemas(pg_dsn, sqlite_dir, args.schemas)
    report_dict = _write_report(report, args.output)
    _log_summary(report, report_dict)

    return 0 if report.passed else 1


def main() -> int:
    """Sync entry point."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
