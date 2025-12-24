# SQLAlchemy Async ORM with SQLite

**Library:** SQLAlchemy 2.1+  
**Topic:** Async ORM patterns with SQLite  
**Cached:** 2025-12-03  
**Source:** Context7 - /websites/sqlalchemy_en_21

## Overview

SQLAlchemy 2.1+ provides comprehensive async support for SQLite databases using aiosqlite. This document covers async ORM patterns, streaming results, and SQLite-specific features.

## Key Patterns

### Stream Query Results with AsyncIO

Stream query results using the async `stream` method. This method returns an awaitable that yields AsyncResult objects, allowing for efficient processing of large result sets.

```python
# Direct await
result = await conn.stream(stmt)
async for row in result:
    print(f"{row}")

# Context manager (automatic cleanup)
async with conn.stream(stmt) as result:
    async for row in result:
        print(f"{row}")
```

### Async Session Results with run_sync

Iterate over results obtained asynchronously from an `AsyncSession` by using the `run_sync` method. This is an alternative to directly awaiting the `awaitable_attrs` for collections.

```python
for b1 in await async_session.run_sync(lambda sess: a1.bs):
    print(b1)
```

### Fetching Rows as Mappings

Use mapping results for dictionary-like access to query results:

```python
# Fetch all rows as mappings
async_mapping_result._async_all()

# Fetch many rows as mappings
async_mapping_result._async_fetchmany(size=50)

# Iterate through partitions
async for partition in async_mapping_result._async_partitions(size=20):
    # Each partition is a sequence of RowMapping objects
    pass
```

## SQLite-Specific Features

### SQLite JSON Datatype Support

SQLAlchemy 2.1+ includes a `JSON` datatype for SQLite, implementing SQLite's JSON member access functions. It utilizes SQLite's `JSON_EXTRACT` and `JSON_QUOTE` functions for basic JSON support.

```python
from sqlalchemy import Table, Column, Integer, MetaData
from sqlalchemy.dialects.sqlite import JSON

metadata_obj = MetaData()

json_table = Table(
    "json_table",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("data", JSON)
)
```

### SQLite Data Types

Import SQLite-specific data types from `sqlalchemy.dialects.sqlite`:

```python
from sqlalchemy.dialects.sqlite import (
    BLOB,
    BOOLEAN,
    CHAR,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INTEGER,
    NUMERIC,
    JSON,
    SMALLINT,
    TEXT,
    TIME,
    TIMESTAMP,
    VARCHAR,
)
```

### SQLite Legacy Quoting Interception

SQLAlchemy 2.1+ enhances SQLite dialect to intercept legacy SQLite quoting characters (like brackets, backticks, single quotes) when reflecting foreign keys. This improves compatibility with older SQLite schemas.

## Best Practices

1. **Use Context Managers**: Always use async context managers for automatic resource cleanup
2. **Stream Large Results**: Use `stream()` for large result sets to avoid memory issues
3. **Mapping Results**: Use mapping results when you need dictionary-like access
4. **Partition Processing**: Use `_async_partitions()` for batch processing of large datasets
5. **SQLite JSON**: Leverage SQLite's native JSON support for structured data storage

## Related Documentation

- SQLAlchemy Async ORM: https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio
- SQLite Dialect: https://docs.sqlalchemy.org/en/21/dialects/sqlite

