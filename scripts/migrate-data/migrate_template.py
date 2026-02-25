"""
SQLite to PostgreSQL Data Migration Template

Usage:
    python migrate_template.py --source sqlite:///path/to/db.sqlite \
        --target postgresql+psycopg://user:pass@host:5432/homeiq \
        --schema core \
        --tables devices,entities,automations
"""

import argparse
import logging
import sys
from datetime import datetime

from sqlalchemy import MetaData, create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def migrate_table(source_engine, target_engine, table_name: str, schema: str) -> int:
    """Migrate a single table from SQLite to PostgreSQL."""
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine, only=[table_name])

    if table_name not in source_meta.tables:
        logger.warning("Table '%s' not found in source database", table_name)
        return 0

    source_table = source_meta.tables[table_name]

    with source_engine.connect() as src_conn:
        rows = src_conn.execute(source_table.select()).fetchall()
        columns = [c.name for c in source_table.columns]

    if not rows:
        logger.info("Table '%s': 0 rows (empty)", table_name)
        return 0

    with target_engine.connect() as tgt_conn:
        tgt_conn.execute(text(f"SET search_path TO {schema}, public"))

        # Batch insert
        batch_size = 1000
        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            data = [dict(zip(columns, row, strict=True)) for row in batch]
            tgt_conn.execute(source_table.insert(), data)
            total += len(batch)
            logger.info(
                "Table '%s': inserted %d/%d rows", table_name, total, len(rows)
            )

        tgt_conn.commit()

    return len(rows)


def validate_migration(
    source_engine, target_engine, table_name: str, schema: str
) -> bool:
    """Validate row counts match between source and target."""
    with source_engine.connect() as src_conn:
        src_count = src_conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar()

    with target_engine.connect() as tgt_conn:
        tgt_conn.execute(text(f"SET search_path TO {schema}, public"))
        tgt_count = tgt_conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        ).scalar()

    match = src_count == tgt_count
    status = "PASS" if match else "FAIL"
    logger.info(
        "Validation %s: %s - source=%d, target=%d",
        status,
        table_name,
        src_count,
        tgt_count,
    )
    return match


def validate_tables(source_engine, target_engine, tables: list[str], schema: str) -> bool:
    """Validate all tables have matching row counts between source and target."""
    all_valid = True
    for table in tables:
        if not validate_migration(source_engine, target_engine, table, schema):
            all_valid = False
    return all_valid


def run_migration(source_engine, target_engine, tables: list[str], schema: str) -> int:
    """Run migration for all tables and return exit code."""
    logger.info("Starting migration: %d tables -> schema '%s'", len(tables), schema)
    start = datetime.now()

    total_rows = 0
    for table in tables:
        count = migrate_table(source_engine, target_engine, table, schema)
        total_rows += count

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("Migration complete: %d total rows in %.1fs", total_rows, elapsed)

    logger.info("Running validation...")
    if validate_tables(source_engine, target_engine, tables, schema):
        logger.info("All validations PASSED")
        return 0
    logger.error("Some validations FAILED")
    return 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL")
    parser.add_argument("--source", required=True, help="Source SQLite URL")
    parser.add_argument("--target", required=True, help="Target PostgreSQL URL")
    parser.add_argument("--schema", required=True, help="Target PostgreSQL schema")
    parser.add_argument("--tables", required=True, help="Comma-separated table names")
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate, don't migrate"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    tables = [t.strip() for t in args.tables.split(",")]

    # Use sync engines for migration (simpler, no async complexity)
    source_url = args.source.replace("+aiosqlite", "")
    target_url = args.target.replace("+asyncpg", "+psycopg")

    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)

    if args.dry_run:
        logger.info(
            "DRY RUN: Would migrate %d tables from %s to %s schema=%s",
            len(tables), source_url, target_url, args.schema,
        )
        for table in tables:
            logger.info("  - %s", table)
        return 0

    if args.validate_only:
        return 0 if validate_tables(source_engine, target_engine, tables, args.schema) else 1

    return run_migration(source_engine, target_engine, tables, args.schema)


if __name__ == "__main__":
    sys.exit(main())
