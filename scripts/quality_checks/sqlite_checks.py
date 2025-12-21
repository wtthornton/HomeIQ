"""
SQLite database quality checks.
Extracted from check_database_quality.py for modularity.
"""
from pathlib import Path
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def check_table_basics(db: AsyncSession, table: str) -> Tuple[int, List[str]]:
    """Check basic table statistics."""
    info = []
    
    # Get row count
    result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
    row_count = result.scalar()
    info.append(f"{table}: {row_count} rows")
    
    return row_count, info


async def check_null_values(db: AsyncSession, table: str) -> Tuple[List[str], List[str]]:
    """Check for NULL values in NOT NULL columns."""
    issues = []
    warnings = []
    
    # Get table schema
    result = await db.execute(text(f"PRAGMA table_info({table})"))
    columns = result.fetchall()
    nullable_cols = [col[1] for col in columns if col[3] == 0]  # NOT NULL columns
    
    # Check for NULL values in NOT NULL columns
    for col in nullable_cols:
        result = await db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"))
        null_count = result.scalar()
        if null_count > 0:
            issues.append(f"{table}.{col}: {null_count} NULL values in NOT NULL column")
    
    return issues, warnings


async def check_orphaned_records(db: AsyncSession, table: str, foreign_key: str, referenced_table: str) -> List[str]:
    """Check for orphaned records (foreign key references that don't exist)."""
    issues = []
    
    try:
        result = await db.execute(text(f"""
            SELECT COUNT(*) FROM {table} t
            LEFT JOIN {referenced_table} r ON t.{foreign_key} = r.id
            WHERE t.{foreign_key} IS NOT NULL AND r.id IS NULL
        """))
        orphaned = result.scalar()
        if orphaned > 0:
            issues.append(f"{table}: {orphaned} orphaned records ({foreign_key} doesn't exist in {referenced_table})")
    except Exception:
        pass  # Table or column might not exist
    
    return issues


async def check_table_specific(db: AsyncSession, table: str) -> Tuple[List[str], List[str]]:
    """Check table-specific quality issues."""
    issues = []
    warnings = []
    
    if table == 'suggestions':
        # Check for suggestions without required fields
        result = await db.execute(text("""
            SELECT COUNT(*) FROM suggestions 
            WHERE description_only IS NULL OR description_only = ''
        """))
        empty_desc = result.scalar()
        if empty_desc > 0:
            issues.append(f"suggestions: {empty_desc} with empty description_only")
        
        result = await db.execute(text("""
            SELECT COUNT(*) FROM suggestions 
            WHERE title IS NULL OR title = ''
        """))
        empty_title = result.scalar()
        if empty_title > 0:
            issues.append(f"suggestions: {empty_title} with empty title")
        
        # Check for orphaned suggestions
        orphaned_issues = await check_orphaned_records(db, 'suggestions', 'pattern_id', 'patterns')
        issues.extend(orphaned_issues)
    
    elif table == 'patterns':
        # Check for patterns with invalid confidence
        try:
            result = await db.execute(text("""
                SELECT COUNT(*) FROM patterns 
                WHERE confidence < 0 OR confidence > 1
            """))
            invalid_conf = result.scalar()
            if invalid_conf > 0:
                issues.append(f"patterns: {invalid_conf} with invalid confidence (not 0-1)")
        except Exception:
            pass  # Column might not exist
        
        # Check pattern_metadata
        try:
            result = await db.execute(text("""
                SELECT COUNT(*) FROM patterns 
                WHERE pattern_metadata IS NULL
            """))
            empty_metadata = result.scalar()
            if empty_metadata > 0:
                warnings.append(f"patterns: {empty_metadata} with NULL pattern_metadata")
        except Exception:
            pass
    
    elif table == 'ask_ai_queries':
        # Check for queries without suggestions
        result = await db.execute(text("""
            SELECT COUNT(*) FROM ask_ai_queries 
            WHERE suggestions IS NULL OR suggestions = '[]' OR suggestions = ''
        """))
        empty_suggestions = result.scalar()
        if empty_suggestions > 0:
            warnings.append(f"ask_ai_queries: {empty_suggestions} queries without suggestions")
    
    return issues, warnings


async def get_all_tables(db: AsyncSession) -> List[str]:
    """Get all user tables from the database."""
    result = await db.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """))
    return [row[0] for row in result.fetchall()]

