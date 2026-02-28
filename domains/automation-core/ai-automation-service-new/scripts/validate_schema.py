#!/usr/bin/env python3
"""
Database Schema Validation Script

Validates that the database schema matches the SQLAlchemy model definitions.
Checks:
- All tables exist
- All columns exist with correct types
- Column nullability matches
- Primary keys match
- Foreign keys match

Usage:
    python scripts/validate_schema.py
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings
from src.database.models import AutomationVersion, Base, Suggestion

# PostgreSQL type mappings (SQLAlchemy types -> PostgreSQL types)
PG_TYPE_MAP = {
    "integer": ["Integer", "int"],
    "text": ["String", "Text", "JSON"],
    "character varying": ["String", "VARCHAR"],
    "timestamp without time zone": ["DateTime", "Date", "Time"],
    "double precision": ["Float"],
    "numeric": ["Numeric"],
    "boolean": ["Boolean"],
    "bytea": ["LargeBinary", "Binary"],
}


def sqlalchemy_to_pg_type(sqlalchemy_type: str) -> str:
    """Convert SQLAlchemy type to PostgreSQL type."""
    sqlalchemy_type_str = str(sqlalchemy_type).upper()

    for pg_type, sa_types in PG_TYPE_MAP.items():
        if any(t.upper() in sqlalchemy_type_str for t in sa_types):
            return pg_type

    return "text"


async def get_db_schema(db_url: str) -> dict[str, dict[str, Any]]:
    """Get actual database schema from PostgreSQL."""
    schema = {}

    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        # Get all tables in current schema
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = current_schema()
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        for table_name in tables:
            # Get column info
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            columns = result.fetchall()

            # Get primary keys
            result = await conn.execute(text("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = current_schema()
                AND tc.table_name = :table_name
                AND tc.constraint_type = 'PRIMARY KEY'
            """), {"table_name": table_name})
            primary_keys = [row[0] for row in result.fetchall()]

            # Get foreign keys
            result = await conn.execute(text("""
                SELECT kcu.column_name, ccu.table_name AS foreign_table,
                       ccu.column_name AS foreign_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = current_schema()
                AND tc.table_name = :table_name
                AND tc.constraint_type = 'FOREIGN KEY'
            """), {"table_name": table_name})
            foreign_keys = result.fetchall()

            schema[table_name] = {"columns": {}, "primary_keys": primary_keys, "foreign_keys": []}

            for col in columns:
                col_name, data_type, is_nullable, default_val = col
                schema[table_name]["columns"][col_name] = {
                    "type": data_type,
                    "nullable": is_nullable == "YES",
                    "default": default_val,
                    "primary_key": col_name in primary_keys,
                }

            for fk in foreign_keys:
                schema[table_name]["foreign_keys"].append(
                    {
                        "column": fk[0],
                        "referenced_table": fk[1],
                        "referenced_column": fk[2],
                    }
                )

    await engine.dispose()
    return schema


def get_model_schema() -> dict[str, dict[str, Any]]:
    """Get expected schema from SQLAlchemy models."""
    schema = {}

    for table_name in Base.metadata.tables:
        table = Base.metadata.tables[table_name]

        schema[table_name] = {
            "columns": {},
            "primary_keys": [col.name for col in table.primary_key.columns],
            "foreign_keys": [],
        }

        for column in table.columns:
            pg_type = sqlalchemy_to_pg_type(str(column.type))

            default_val = None
            if column.default is not None:
                if hasattr(column.default, "arg"):
                    default_val = str(column.default.arg)
                else:
                    default_val = str(column.default)

            schema[table_name]["columns"][column.name] = {
                "type": pg_type,
                "nullable": column.nullable,
                "default": default_val,
                "primary_key": column.primary_key,
            }

        for fk in table.foreign_keys:
            schema[table_name]["foreign_keys"].append(
                {
                    "column": fk.parent.name,
                    "referenced_table": fk.column.table.name,
                    "referenced_column": fk.column.name,
                }
            )

    return schema


def compare_schemas(actual: dict, expected: dict) -> dict[str, Any]:
    """Compare actual database schema with expected model schema."""
    issues = []
    warnings = []
    matches = []

    for table_name in expected:
        if table_name not in actual:
            issues.append(f"[ERROR] Table '{table_name}' does not exist in database")
            continue

        matches.append(f"[OK] Table '{table_name}' exists")
        actual_table = actual[table_name]
        expected_table = expected[table_name]

        for col_name, expected_col in expected_table["columns"].items():
            if col_name not in actual_table["columns"]:
                issues.append(
                    f"[ERROR] Column '{table_name}.{col_name}' does not exist in database"
                )
                continue

            actual_col = actual_table["columns"][col_name]

            expected_type = expected_col["type"]
            actual_type = actual_col["type"]

            type_compatible = (
                expected_type == actual_type
                or (expected_type == "text" and actual_type in ["text", "character varying"])
                or (expected_type in ["text", "character varying"] and actual_type == "text")
                or (expected_type == "integer" and actual_type == "integer")
            )

            if not type_compatible:
                warnings.append(
                    f"[WARN] Type mismatch: '{table_name}.{col_name}' - "
                    f"Expected {expected_type}, got {actual_type}"
                )

            if expected_col["nullable"] != actual_col["nullable"]:
                issues.append(
                    f"[ERROR] Nullability mismatch: '{table_name}.{col_name}' - "
                    f"Expected nullable={expected_col['nullable']}, got {actual_col['nullable']}"
                )

            if expected_col["primary_key"] != actual_col["primary_key"]:
                issues.append(
                    f"[ERROR] Primary key mismatch: '{table_name}.{col_name}' - "
                    f"Expected pk={expected_col['primary_key']}, got {actual_col['primary_key']}"
                )

            matches.append(f"[OK] Column '{table_name}.{col_name}' matches")

        for col_name in actual_table["columns"]:
            if col_name not in expected_table["columns"]:
                warnings.append(
                    f"[WARN] Extra column in database: '{table_name}.{col_name}' "
                    f"(not in model definition)"
                )

        expected_pks = set(expected_table["primary_keys"])
        actual_pks = set(actual_table["primary_keys"])
        if expected_pks != actual_pks:
            issues.append(
                f"[ERROR] Primary key mismatch for '{table_name}': "
                f"Expected {expected_pks}, got {actual_pks}"
            )

    for table_name in actual:
        if table_name not in expected:
            warnings.append(f"[WARN] Extra table in database: '{table_name}' (not in models)")

    return {"issues": issues, "warnings": warnings, "matches": matches}


async def main():
    """Main validation function."""
    print("=" * 80)
    print("Database Schema Validation")
    print("=" * 80)
    print(f"Database: {settings.effective_database_url}")
    print(f"Model: {Suggestion.__tablename__}, {AutomationVersion.__tablename__}")
    print("=" * 80)
    print()

    db_url = settings.effective_database_url
    if not db_url:
        print("[ERROR] No database URL configured")
        sys.exit(1)

    print(f"[INFO] Reading database schema from: {db_url}")
    actual_schema = await get_db_schema(db_url)

    print("[INFO] Reading model schema...")
    expected_schema = get_model_schema()

    print("\n[INFO] Comparing schemas...")
    print()

    results = compare_schemas(actual_schema, expected_schema)

    if results["matches"]:
        print("[OK] MATCHES:")
        for match in results["matches"]:
            print(f"  {match}")
        print()

    if results["warnings"]:
        print("[WARN] WARNINGS:")
        for warning in results["warnings"]:
            print(f"  {warning}")
        print()

    if results["issues"]:
        print("[ERROR] ISSUES FOUND:")
        for issue in results["issues"]:
            print(f"  {issue}")
        print()
        print("=" * 80)
        print("ACTION REQUIRED:")
        print("  Run migrations to fix schema:")
        print("    alembic upgrade head")
        print("=" * 80)
        sys.exit(1)
    else:
        print("=" * 80)
        print("[OK] Schema validation PASSED - Database matches model definitions")
        print("=" * 80)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
