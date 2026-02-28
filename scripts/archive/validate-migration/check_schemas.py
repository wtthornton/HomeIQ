"""
PostgreSQL Schema Structure Validator

Validates that all expected schemas, tables, columns, indexes, and foreign
keys exist in the PostgreSQL database after migration.  Does NOT compare
data -- use validate_data.py for that.

Usage:
    python scripts/validate-migration/check_schemas.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq

    # Check specific schemas only
    python scripts/validate-migration/check_schemas.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq \
        --schemas core agent

    # Dry run
    python scripts/validate-migration/check_schemas.py \
        --postgres-url postgresql+asyncpg://user:pass@host:5432/homeiq \
        --dry-run
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected schema structure
# Each schema maps to a dict of table -> list of (column_name, expected_type)
# Types use PostgreSQL names (mapped from SQLAlchemy types).
# We validate column existence and that the PG type is "compatible"
# rather than requiring exact string matches.
# ---------------------------------------------------------------------------

# Type families for flexible matching -- SQLAlchemy -> PostgreSQL mapping
# can vary (e.g., String -> character varying, Text -> text, etc.)
TYPE_FAMILIES: dict[str, set[str]] = {
    "string": {"character varying", "varchar", "text"},
    "text": {"text", "character varying", "varchar"},
    "integer": {"integer", "bigint", "smallint", "int4", "int8", "int2"},
    "float": {"double precision", "real", "numeric", "float4", "float8"},
    "boolean": {"boolean", "bool"},
    "datetime": {
        "timestamp without time zone",
        "timestamp with time zone",
        "timestamp",
        "timestamptz",
    },
    "json": {"json", "jsonb"},
}


def _type_matches(expected_family: str, actual_pg_type: str) -> bool:
    """Check whether actual_pg_type is in the expected type family."""
    family = TYPE_FAMILIES.get(expected_family, set())
    return actual_pg_type.lower() in family


# ---------------------------------------------------------------------------
# Expected table definitions per schema
# Format: { schema: { table: [ (column, type_family), ... ] } }
# Only critical columns are listed; extra columns are allowed.
# ---------------------------------------------------------------------------
EXPECTED: dict[str, dict[str, list[tuple[str, str]]]] = {
    "core": {
        "devices": [
            ("device_id", "string"),
            ("name", "string"),
            ("manufacturer", "string"),
            ("model", "string"),
            ("area_id", "string"),
            ("integration", "string"),
            ("device_type", "string"),
            ("device_category", "string"),
            ("last_seen", "datetime"),
            ("created_at", "datetime"),
        ],
        "entities": [
            ("entity_id", "string"),
            ("device_id", "string"),
            ("domain", "string"),
            ("friendly_name", "string"),
            ("area_id", "string"),
            ("disabled", "boolean"),
            ("created_at", "datetime"),
            ("updated_at", "datetime"),
        ],
        "automations": [
            ("automation_id", "string"),
            ("alias", "string"),
            ("mode", "string"),
            ("enabled", "boolean"),
            ("total_executions", "integer"),
            ("created_at", "datetime"),
        ],
        "automation_executions": [
            ("id", "integer"),
            ("automation_id", "string"),
            ("run_id", "string"),
            ("started_at", "datetime"),
            ("duration_seconds", "float"),
            ("execution_result", "string"),
        ],
        "services": [
            ("domain", "string"),
            ("service_name", "string"),
            ("name", "string"),
            ("fields", "json"),
        ],
        "statistics_meta": [
            ("statistic_id", "string"),
            ("source", "string"),
            ("unit_of_measurement", "string"),
            ("state_class", "string"),
            ("has_mean", "boolean"),
            ("has_sum", "boolean"),
        ],
        "user_team_preferences": [
            ("user_id", "string"),
            ("nfl_teams", "json"),
            ("nhl_teams", "json"),
            ("created_at", "datetime"),
        ],
    },
    "automation": {
        "suggestions": [
            ("id", "integer"),
            ("title", "string"),
            ("status", "string"),
            ("created_at", "datetime"),
        ],
        "automation_versions": [
            ("id", "integer"),
            ("suggestion_id", "integer"),
            ("automation_id", "string"),
            ("version_number", "integer"),
            ("automation_yaml", "text"),
        ],
        "plans": [
            ("plan_id", "string"),
            ("template_id", "string"),
            ("parameters", "json"),
            ("confidence", "float"),
            ("safety_class", "string"),
        ],
        "compiled_artifacts": [
            ("compiled_id", "string"),
            ("plan_id", "string"),
            ("yaml", "text"),
            ("human_summary", "text"),
        ],
        "deployments": [
            ("deployment_id", "string"),
            ("compiled_id", "string"),
            ("ha_automation_id", "string"),
            ("status", "string"),
            ("deployed_at", "datetime"),
        ],
    },
    "agent": {
        "context_cache": [
            ("id", "integer"),
            ("cache_key", "string"),
            ("cache_value", "text"),
            ("expires_at", "datetime"),
        ],
        "conversations": [
            ("conversation_id", "string"),
            ("state", "string"),
            ("created_at", "datetime"),
            ("updated_at", "datetime"),
        ],
        "messages": [
            ("message_id", "string"),
            ("conversation_id", "string"),
            ("role", "string"),
            ("content", "text"),
            ("created_at", "datetime"),
        ],
    },
    "blueprints": {
        "indexed_blueprints": [
            ("id", "string"),
        ],
        "blueprint_suggestions": [
            ("id", "integer"),
        ],
        "community_automations": [
            ("id", "integer"),
        ],
        "miner_state": [
            ("id", "integer"),
        ],
    },
    "energy": {
        "suggestions": [
            ("id", "integer"),
        ],
        "invalid_suggestion_reports": [
            ("id", "integer"),
        ],
    },
    "devices": {
        "device_intelligence": [
            ("id", "integer"),
        ],
        "setup_sessions": [
            ("id", "integer"),
        ],
    },
    "patterns": {
        "spec_versions": [
            ("id", "integer"),
        ],
    },
    "rag": {
        "rag_knowledge": [
            ("id", "integer"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Result structures
# ---------------------------------------------------------------------------
@dataclass
class TableCheck:
    """Result of checking a single table."""

    table: str
    exists: bool = False
    missing_columns: list[str] = field(default_factory=list)
    type_mismatches: list[dict] = field(default_factory=list)
    index_count: int = 0
    fk_count: int = 0
    column_count: int = 0

    @property
    def passed(self) -> bool:
        return self.exists and not self.missing_columns and not self.type_mismatches


@dataclass
class SchemaCheck:
    """Result of checking a single schema."""

    schema: str
    exists: bool = False
    tables: list[TableCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.exists and all(t.passed for t in self.tables)


# ---------------------------------------------------------------------------
# Helper: parse asyncpg-compatible DSN
# ---------------------------------------------------------------------------
def parse_pg_dsn(url: str) -> str:
    """Convert SQLAlchemy-style URL to asyncpg-compatible DSN."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------
async def check_schema_exists(
    conn: asyncpg.Connection,
    schema: str,
) -> bool:
    """Check if a schema exists in PostgreSQL."""
    return bool(
        await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
            schema,
        )
    )


async def check_table(
    conn: asyncpg.Connection,
    schema: str,
    table: str,
    expected_columns: list[tuple[str, str]],
) -> TableCheck:
    """Validate a table's structure against expectations."""
    tc = TableCheck(table=table)

    # Check existence
    tc.exists = bool(
        await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = $1 AND table_name = $2
            )
            """,
            schema,
            table,
        )
    )
    if not tc.exists:
        return tc

    # Get actual columns
    actual_cols = await conn.fetch(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
        """,
        schema,
        table,
    )
    actual_map = {r["column_name"]: r["data_type"] for r in actual_cols}
    tc.column_count = len(actual_map)

    # Validate expected columns
    for col_name, expected_type in expected_columns:
        if col_name not in actual_map:
            tc.missing_columns.append(col_name)
        elif not _type_matches(expected_type, actual_map[col_name]):
            tc.type_mismatches.append(
                {
                    "column": col_name,
                    "expected_family": expected_type,
                    "actual": actual_map[col_name],
                }
            )

    # Count indexes
    idx_row = await conn.fetchval(
        """
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname = $1 AND tablename = $2
        """,
        schema,
        table,
    )
    tc.index_count = idx_row or 0

    # Count foreign keys
    fk_row = await conn.fetchval(
        """
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema = $1
          AND table_name = $2
          AND constraint_type = 'FOREIGN KEY'
        """,
        schema,
        table,
    )
    tc.fk_count = fk_row or 0

    return tc


async def validate_all_schemas(
    pg_dsn: str,
    schemas: list[str],
) -> list[SchemaCheck]:
    """Validate all specified schemas."""
    results: list[SchemaCheck] = []
    conn = await asyncpg.connect(pg_dsn)
    try:
        for schema in schemas:
            sc = SchemaCheck(schema=schema)
            sc.exists = await check_schema_exists(conn, schema)

            if not sc.exists:
                logger.error("Schema '%s' does NOT exist", schema)
                results.append(sc)
                continue

            expected_tables = EXPECTED.get(schema, {})
            for table_name, expected_cols in expected_tables.items():
                tc = await check_table(conn, schema, table_name, expected_cols)
                sc.tables.append(tc)

            results.append(sc)
    finally:
        await conn.close()

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
def _format_missing_columns(missing: list[str]) -> str:
    """Format a list of missing column names for display.

    Shows up to 3 column names, plus a count of remaining columns if
    there are more than 3.

    Args:
        missing: List of missing column name strings.

    Returns:
        Formatted string for the report table cell.
    """
    if not missing:
        return "-"
    result = ", ".join(missing[:3])
    if len(missing) > 3:
        result += f" +{len(missing) - 3}"
    return result


def _print_schema_row(sc: SchemaCheck) -> None:
    """Print table rows for a single schema check result.

    Args:
        sc: SchemaCheck instance to render.
    """
    if not sc.exists:
        print(
            f"{sc.schema:<14} {'(schema missing)':<30} {'NO':<8} "
            f"{'-':<6} {'-':<5} {'-':<5} {'-':<20} {'FAIL':<8}"
        )
        return

    for tc in sc.tables:
        exists_str = "YES" if tc.exists else "NO"
        missing_str = _format_missing_columns(tc.missing_columns)
        status = "PASS" if tc.passed else "FAIL"
        print(
            f"{sc.schema:<14} {tc.table:<30} {exists_str:<8} "
            f"{tc.column_count:<6} {tc.index_count:<5} {tc.fk_count:<5} "
            f"{missing_str:<20} {status:<8}"
        )

        for mm in tc.type_mismatches:
            print(
                f"{'':>14} {'':>30}   TYPE MISMATCH: {mm['column']} "
                f"(expected {mm['expected_family']}, got {mm['actual']})"
            )


def _print_summary(results: list[SchemaCheck]) -> None:
    """Print the summary line showing overall pass/fail counts.

    Args:
        results: List of SchemaCheck results to summarize.
    """
    total_schemas = len(results)
    passed_schemas = sum(1 for s in results if s.passed)
    total_tables = sum(len(s.tables) for s in results)
    passed_tables = sum(
        sum(1 for t in s.tables if t.passed) for s in results
    )

    overall = "PASS" if all(s.passed for s in results) else "FAIL"
    print(
        f"\nOverall: {overall} | "
        f"Schemas: {passed_schemas}/{total_schemas} | "
        f"Tables: {passed_tables}/{total_tables}"
    )
    print()


def print_report(results: list[SchemaCheck]) -> None:
    """Print a formatted table of schema health.

    Args:
        results: List of SchemaCheck results to display.
    """
    header = (
        f"{'Schema':<14} {'Table':<30} {'Exists':<8} {'Cols':<6} "
        f"{'Idx':<5} {'FKs':<5} {'Missing':<20} {'Status':<8}"
    )
    separator = "-" * len(header)

    print()
    print("=== PostgreSQL Schema Health Report ===")
    print()
    print(header)
    print(separator)

    for sc in results:
        _print_schema_row(sc)

    print(separator)
    _print_summary(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate PostgreSQL schema structure for HomeIQ migration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --postgres-url postgresql+asyncpg://u:p@host/homeiq\n"
            "  %(prog)s --postgres-url postgresql+asyncpg://u:p@host/homeiq --schemas core agent\n"
        ),
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--schemas",
        nargs="*",
        default=list(EXPECTED.keys()),
        choices=list(EXPECTED.keys()),
        help="Schemas to check (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be checked without connecting",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def dry_run(schemas: list[str]) -> None:
    """Print what would be checked."""
    logger.info("=== DRY RUN: Schema Check Plan ===")
    for schema in schemas:
        tables = EXPECTED.get(schema, {})
        logger.info("Schema: %s (%d tables)", schema, len(tables))
        for table, cols in tables.items():
            logger.info("  %s: %d expected columns", table, len(cols))
    logger.info("=== End DRY RUN ===")


async def async_main() -> int:
    """Async entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        dry_run(args.schemas)
        return 0

    pg_dsn = parse_pg_dsn(args.postgres_url)
    results = await validate_all_schemas(pg_dsn, args.schemas)
    print_report(results)

    return 0 if all(s.passed for s in results) else 1


def main() -> int:
    """Sync entry point."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
