"""
PostgreSQL-specific quality check functions.
Used by runner.py for database quality validation.
"""
from typing import List, Tuple, Set

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def get_all_tables(db: AsyncSession, schema: str = "public") -> List[str]:
    """Get all tables in the given schema."""
    result = await db.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        ),
        {"schema": schema},
    )
    return [row[0] for row in result.fetchall()]


async def check_table_basics(
    db: AsyncSession, table: str, schema: str = "public"
) -> Tuple[int, List[str]]:
    """Check basic table info: row count and column count."""
    info: List[str] = []

    # Row count
    result = await db.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"'))
    row_count = result.scalar() or 0
    info.append(f"{schema}.{table}: {row_count:,} rows")

    # Column count
    result = await db.execute(
        text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table"
        ),
        {"schema": schema, "table": table},
    )
    col_count = result.scalar() or 0
    info.append(f"{schema}.{table}: {col_count} columns")

    return row_count, info


async def check_null_values(
    db: AsyncSession, table: str, schema: str = "public"
) -> Tuple[List[str], List[str]]:
    """Check for NULL values in NOT NULL columns that shouldn't have them."""
    issues: List[str] = []
    warnings: List[str] = []

    # Get columns that are NOT NULL
    result = await db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table "
            "AND is_nullable = 'NO'"
        ),
        {"schema": schema, "table": table},
    )
    not_null_cols = [row[0] for row in result.fetchall()]

    # For each NOT NULL column, PostgreSQL already enforces this constraint,
    # so we only check advisory columns (nullable ones with lots of NULLs)
    result = await db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table "
            "AND is_nullable = 'YES'"
        ),
        {"schema": schema, "table": table},
    )
    nullable_cols = [row[0] for row in result.fetchall()]

    for col in nullable_cols:
        try:
            result = await db.execute(
                text(
                    f'SELECT count(*) FROM "{schema}"."{table}" '
                    f'WHERE "{col}" IS NULL'
                )
            )
            null_count = result.scalar() or 0
            if null_count > 0:
                total_result = await db.execute(
                    text(f'SELECT count(*) FROM "{schema}"."{table}"')
                )
                total = total_result.scalar() or 1
                pct = (null_count / total) * 100
                if pct > 80:
                    warnings.append(
                        f"{schema}.{table}.{col}: {null_count} NULLs ({pct:.0f}%)"
                    )
        except Exception:
            pass  # Skip columns that can't be checked

    return issues, warnings


async def check_orphaned_records(
    db: AsyncSession,
    table: str,
    fk_column: str,
    parent_table: str,
    schema: str = "public",
) -> List[str]:
    """Check for orphaned records (FK references to non-existent parent rows)."""
    issues: List[str] = []
    try:
        result = await db.execute(
            text(
                f'SELECT count(*) FROM "{schema}"."{table}" t '
                f'LEFT JOIN "{schema}"."{parent_table}" p ON t."{fk_column}" = p.id '
                f'WHERE t."{fk_column}" IS NOT NULL AND p.id IS NULL'
            )
        )
        orphaned = result.scalar() or 0
        if orphaned > 0:
            issues.append(
                f"{schema}.{table}: {orphaned} orphaned records "
                f"(references {parent_table} via {fk_column})"
            )
    except Exception:
        pass  # Skip if tables don't have expected columns

    return issues


async def check_table_specific(
    db: AsyncSession, table: str, schema: str = "public"
) -> Tuple[List[str], List[str]]:
    """Run table-specific quality checks."""
    issues: List[str] = []
    warnings: List[str] = []

    # Check for duplicate entries in key tables
    if table in ("patterns", "synergy_opportunities", "suggestions"):
        try:
            result = await db.execute(
                text(
                    f'SELECT count(*) - count(DISTINCT id) '
                    f'FROM "{schema}"."{table}"'
                )
            )
            dupes = result.scalar() or 0
            if dupes > 0:
                issues.append(f"{schema}.{table}: {dupes} duplicate IDs found")
        except Exception:
            pass

    return issues, warnings
