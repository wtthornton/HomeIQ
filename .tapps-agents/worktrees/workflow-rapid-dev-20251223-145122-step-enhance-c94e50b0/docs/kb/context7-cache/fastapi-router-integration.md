# FastAPI Router Integration Pattern
**Context7 KB - Router Modularization**

**Source:** Context7 /fastapi/fastapi  
**Topic:** APIRouter, include_router, modular routing  
**Retrieved:** October 11, 2025

---

## Pattern: Modular API Router

### Creating a Router Module
```python
# services/admin-api/src/integration_endpoints.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/integrations")
def list_integrations():
    return {"integrations": []}

@router.get("/integrations/{service}/config")
def get_config(service: str):
    return {"service": service, "config": {}}
```

### Including Router in Main App
```python
# services/admin-api/src/simple_main.py
from fastapi import FastAPI
from integration_endpoints import router as integration_router

app = FastAPI()

# Include router with prefix and tags
app.include_router(
    integration_router,
    prefix="/api/v1",
    tags=["Integration Management"]
)
```

### Router Configuration Options
```python
router = APIRouter(
    prefix="/items",           # Path prefix for all routes
    tags=["items"],           # OpenAPI tags
    dependencies=[],          # Router-level dependencies
    responses={404: {...}}    # Default responses
)
```

---

## Best Practices

1. **One Router Per Module** - Group related endpoints
2. **Use Prefix** - Avoid repeating path prefixes
3. **Apply Tags** - For OpenAPI documentation grouping
4. **Router Dependencies** - Share auth across endpoints
5. **Import at Module Level** - `from module import router as module_router`

---

**Saved to KB:** 2025-10-11  
**Use Case:** Modular FastAPI application structure  
**Complexity:** Low (simple pattern)

