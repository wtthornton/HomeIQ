<!--
library: fastapi
topic: routing
context7_id: /fastapi/fastapi
cached_at: 2025-12-21T00:41:07.004732+00:00Z
cache_hits: 0
-->

# FastAPI Routing

## Define Path Order for Specific and Generic Routes

The more specific path `/users/me` must be declared before the generic path `/users/{user_id}` to ensure the specific route is matched first.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/me")
async def read_user_me():
    return {"user_id": "the current user"}

@app.get("/users/{user_id}")
async def read_user(user_id: str):
    return {"user_id": user_id}
```

## Modularize FastAPI Applications with APIRouter

```python
from fastapi import APIRouter, FastAPI

items_router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}}
)

@items_router.get("/")
async def read_items():
    return [{"name": "Item 1"}, {"name": "Item 2"}]

app = FastAPI()
app.include_router(items_router)
```

