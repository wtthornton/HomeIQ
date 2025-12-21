<!--
library: fastapi
topic: dependency-injection
context7_id: /fastapi/fastapi
cached_at: 2025-12-21T00:41:07.047475+00:00Z
cache_hits: 0
-->

# FastAPI Dependency Injection

## Implement Dependency Injection in FastAPI Endpoints

Share common logic across endpoints using dependency injection with the Depends function.

```python
from typing import Annotated, Union
from fastapi import Depends, FastAPI

app = FastAPI()

async def common_parameters(
    q: Union[str, None] = None,
    skip: int = 0,
    limit: int = 100
):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return {"params": commons, "items": ["item1", "item2"]}

# Database dependency with cleanup
async def get_db():
    db = {"connection": "active"}
    try:
        yield db
    finally:
        db["connection"] = "closed"

@app.get("/query/")
async def query_data(db: Annotated[dict, Depends(get_db)]):
    return {"database": db, "data": "query results"}
```

