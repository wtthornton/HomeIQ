<!--
library: sqlalchemy
topic: async
context7_id: /sqlalchemy/sqlalchemy
cached_at: 2025-12-21T00:41:07.197232+00:00Z
cache_hits: 0
-->

# SQLAlchemy Async

## Initialize and Use SQLAlchemy Async Engine and Sessions

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

engine = create_async_engine(
    "postgresql+asyncpg://scott:tiger@localhost/test",
    echo=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async with async_session() as session:
    # Insert with transaction
    async with session.begin():
        session.add_all([
            User(name="Alice"),
            User(name="Bob")
        ])

    # Query
    stmt = select(User)
    result = await session.scalars(stmt)
    for user in result:
        print(user.name)
```

