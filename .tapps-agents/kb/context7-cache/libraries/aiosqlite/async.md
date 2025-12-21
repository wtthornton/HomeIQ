<!--
library: aiosqlite
topic: async
context7_id: /omnilib/aiosqlite
cached_at: 2025-12-21T00:41:07.305259+00:00Z
cache_hits: 0
-->

# aiosqlite Async

## Using aiosqlite with Async Context Managers

```python
import aiosqlite

async with aiosqlite.connect("database.db") as db:
    await db.execute("INSERT INTO some_table ...")
    await db.commit()

    async with db.execute("SELECT * FROM some_table") as cursor:
        async for row in cursor:
            print(row)
```

## Advanced Features with Row Factory

```python
async with aiosqlite.connect("database.db") as db:
    db.row_factory = aiosqlite.Row
    async with db.execute('SELECT * FROM some_table') as cursor:
        async for row in cursor:
            value = row['column']
```

