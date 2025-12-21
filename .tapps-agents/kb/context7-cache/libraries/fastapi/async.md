<!--
library: fastapi
topic: async
context7_id: /fastapi/fastapi
cached_at: 2025-12-21T00:41:07.090348+00:00Z
cache_hits: 0
-->

# FastAPI Async

## Define Asynchronous Path Operation with `async def`

```python
@app.get('/')
async def read_results():
    results = await some_library()
    return results
```

## Create Async FastAPI Application

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
```

