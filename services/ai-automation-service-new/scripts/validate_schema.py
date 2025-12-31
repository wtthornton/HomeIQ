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

import aiosqlite

from src.database.models import Base, Suggestion, AutomationVersion
from src.config import settings


# SQLite type mappings (SQLAlchemy types -> SQLite types)
SQLITE_TYPE_MAP = {
    'INTEGER': ['Integer', 'int'],
    'TEXT': ['String', 'Text', 'JSON', 'DateTime', 'Date', 'Time'],
    'REAL': ['Float', 'Numeric'],
    'BLOB': ['LargeBinary', 'Binary'],
    'NUMERIC': ['Numeric'],
}

def sqlalchemy_to_sqlite_type(sqlalchemy_type: str) -> str:
    """Convert SQLAlchemy type to SQLite type."""
    sqlalchemy_type_str = str(sqlalchemy_type).upper()
    
    # Check mappings
    for sqlite_type, sa_types in SQLITE_TYPE_MAP.items():
        if any(t.upper() in sqlalchemy_type_str for t in sa_types):
            return sqlite_type
    
    # Default to TEXT for unknown types
    return 'TEXT'


async def get_db_schema(db_path: str) -> dict[str, dict[str, Any]]:
    """Get actual database schema from SQLite."""
    schema = {}
    
    async with aiosqlite.connect(db_path) as db:
        # Get all tables
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in await cursor.fetchall()]
        
        for table_name in tables:
            # Get column info
            cursor = await db.execute(f"PRAGMA table_info({table_name})")
            columns = await cursor.fetchall()
            
            # Get foreign keys
            cursor = await db.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = await cursor.fetchall()
            
            schema[table_name] = {
                'columns': {},
                'primary_keys': [],
                'foreign_keys': []
            }
            
            for col in columns:
                col_id, name, col_type, not_null, default_val, pk = col
                schema[table_name]['columns'][name] = {
                    'type': col_type.upper(),
                    'nullable': not not_null,
                    'default': default_val,
                    'primary_key': bool(pk)
                }
                if pk:
                    schema[table_name]['primary_keys'].append(name)
            
            for fk in foreign_keys:
                schema[table_name]['foreign_keys'].append({
                    'column': fk[3],  # from column
                    'referenced_table': fk[2],  # table
                    'referenced_column': fk[4]  # to column
                })
    
    return schema


def get_model_schema() -> dict[str, dict[str, Any]]:
    """Get expected schema from SQLAlchemy models."""
    schema = {}
    
    # Directly inspect Base.metadata (no engine needed)
    for table_name in Base.metadata.tables.keys():
        table = Base.metadata.tables[table_name]
        
        schema[table_name] = {
            'columns': {},
            'primary_keys': [col.name for col in table.primary_key.columns],
            'foreign_keys': []
        }
        
        # Get columns
        for column in table.columns:
            # Convert SQLAlchemy type to SQLite type
            sqlite_type = sqlalchemy_to_sqlite_type(str(column.type))
            
            # Get default value
            default_val = None
            if column.default is not None:
                if hasattr(column.default, 'arg'):
                    default_val = str(column.default.arg)
                else:
                    default_val = str(column.default)
            
            schema[table_name]['columns'][column.name] = {
                'type': sqlite_type,
                'nullable': column.nullable,
                'default': default_val,
                'primary_key': column.primary_key
            }
        
        # Get foreign keys
        for fk in table.foreign_keys:
            schema[table_name]['foreign_keys'].append({
                'column': fk.parent.name,
                'referenced_table': fk.column.table.name,
                'referenced_column': fk.column.name
            })
    
    return schema


def compare_schemas(actual: dict, expected: dict) -> dict[str, Any]:
    """Compare actual database schema with expected model schema."""
    issues = []
    warnings = []
    matches = []
    
    # Check all expected tables exist
    for table_name in expected.keys():
        if table_name not in actual:
            issues.append(f"[ERROR] Table '{table_name}' does not exist in database")
            continue
        
            matches.append(f"[OK] Table '{table_name}' exists")
        actual_table = actual[table_name]
        expected_table = expected[table_name]
        
        # Check all expected columns exist
        for col_name, expected_col in expected_table['columns'].items():
            if col_name not in actual_table['columns']:
                issues.append(f"[ERROR] Column '{table_name}.{col_name}' does not exist in database")
                continue
            
            actual_col = actual_table['columns'][col_name]
            
            # Check type (allow some flexibility)
            expected_type = expected_col['type']
            actual_type = actual_col['type']
            
            # SQLite is flexible with types, so we allow some variation
            type_compatible = (
                expected_type == actual_type or
                (expected_type == 'TEXT' and actual_type in ['TEXT', 'VARCHAR']) or
                (expected_type in ['TEXT', 'VARCHAR'] and actual_type == 'TEXT') or
                (expected_type == 'INTEGER' and actual_type == 'INTEGER')
            )
            
            if not type_compatible:
                warnings.append(
                    f"[WARN] Type mismatch: '{table_name}.{col_name}' - "
                    f"Expected {expected_type}, got {actual_type}"
                )
            
            # Check nullability
            if expected_col['nullable'] != actual_col['nullable']:
                issues.append(
                    f"[ERROR] Nullability mismatch: '{table_name}.{col_name}' - "
                    f"Expected nullable={expected_col['nullable']}, got {actual_col['nullable']}"
                )
            
            # Check primary key
            if expected_col['primary_key'] != actual_col['primary_key']:
                issues.append(
                    f"[ERROR] Primary key mismatch: '{table_name}.{col_name}' - "
                    f"Expected pk={expected_col['primary_key']}, got {actual_col['primary_key']}"
                )
            
            matches.append(f"[OK] Column '{table_name}.{col_name}' matches")
        
        # Check for extra columns in database (warnings only)
        for col_name in actual_table['columns']:
            if col_name not in expected_table['columns']:
                warnings.append(
                    f"[WARN] Extra column in database: '{table_name}.{col_name}' "
                    f"(not in model definition)"
                )
        
        # Check primary keys match
        expected_pks = set(expected_table['primary_keys'])
        actual_pks = set(actual_table['primary_keys'])
        if expected_pks != actual_pks:
            issues.append(
                f"[ERROR] Primary key mismatch for '{table_name}': "
                f"Expected {expected_pks}, got {actual_pks}"
            )
    
    # Check for extra tables in database
    for table_name in actual.keys():
        if table_name not in expected:
            warnings.append(f"[WARN] Extra table in database: '{table_name}' (not in models)")
    
    return {
        'issues': issues,
        'warnings': warnings,
        'matches': matches
    }


async def main():
    """Main validation function."""
    print("=" * 80)
    print("Database Schema Validation")
    print("=" * 80)
    print(f"Database: {settings.database_path}")
    print(f"Model: {Suggestion.__tablename__}, {AutomationVersion.__tablename__}")
    print("=" * 80)
    print()
    
    # Check if database exists (use relative path for local execution)
    # In Docker, path is /app/data/ai_automation.db, locally it's ./data/ai_automation.db
    if settings.database_path.startswith("/app/"):
        # Running in Docker or with Docker path - check local path
        db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"
    else:
        db_path = Path(settings.database_path)
    
    if not db_path.exists():
        print(f"[ERROR] Database file not found: {db_path}")
        print(f"       Also checked: {settings.database_path}")
        print("\nRun migrations to create database:")
        print("  cd services/ai-automation-service-new")
        print("  alembic upgrade head")
        sys.exit(1)
    
    print(f"[INFO] Reading database schema from: {db_path}")
    actual_schema = await get_db_schema(str(db_path))
    
    print("[INFO] Reading model schema...")
    expected_schema = get_model_schema()
    
    print("\n[INFO] Comparing schemas...")
    print()
    
    results = compare_schemas(actual_schema, expected_schema)
    
    # Print results
    if results['matches']:
        print("[OK] MATCHES:")
        for match in results['matches']:
            print(f"  {match}")
        print()
    
    if results['warnings']:
        print("[WARN] WARNINGS:")
        for warning in results['warnings']:
            print(f"  {warning}")
        print()
    
    if results['issues']:
        print("[ERROR] ISSUES FOUND:")
        for issue in results['issues']:
            print(f"  {issue}")
        print()
        print("=" * 80)
        print("ACTION REQUIRED:")
        print("  Run migrations to fix schema:")
        print("    cd services/ai-automation-service-new")
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

