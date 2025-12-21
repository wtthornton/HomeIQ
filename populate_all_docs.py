#!/usr/bin/env python3
"""
Populate Context7 KB cache with all documentation.

Fetches documentation via MCP tools and stores in cache.
"""

import sys
from pathlib import Path
from datetime import datetime, UTC

# Add TappsCodingAgents to path
project_root = Path(__file__).parent
tapps_path = project_root / "TappsCodingAgents"
if tapps_path.exists():
    sys.path.insert(0, str(tapps_path))

try:
    from tapps_agents.context7.cache_structure import CacheStructure
    from tapps_agents.context7.metadata import MetadataManager
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"Error importing tapps_agents: {e}")
    sys.exit(1)


def store_doc(library: str, topic: str, content: str, context7_id: str = None):
    """Store documentation in cache."""
    try:
        config = load_config()
        if not config.context7 or not config.context7.enabled:
            return False
        
        cache_root = project_root / config.context7.knowledge_base.location
        cache_structure = CacheStructure(cache_root)
        cache_structure.initialize()
        
        cache_structure.ensure_library_dir(library)
        doc_file = cache_structure.get_library_doc_file(library, topic)
        
        markdown_content = f"""<!--
library: {library}
topic: {topic}
context7_id: {context7_id or ''}
cached_at: {datetime.now(UTC).isoformat()}Z
cache_hits: 0
-->

{content}
"""
        
        doc_file.write_text(markdown_content, encoding="utf-8")
        
        metadata_manager = MetadataManager(cache_structure)
        metadata_manager.update_library_metadata(
            library, context7_id=context7_id, topic=topic
        )
        metadata_manager.update_cache_index(
            library, topic, context7_id=context7_id
        )
        
        return True
    except Exception as e:
        print(f"[X] Error storing {library}/{topic}: {e}")
        return False


# Documentation content from MCP fetches
# These are the actual fetched documentation contents

DOCUMENTATION = {
    ("fastapi", "routing"): {
        "content": """# FastAPI Routing

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
""",
        "context7_id": "/fastapi/fastapi"
    },
    ("fastapi", "dependency-injection"): {
        "content": """# FastAPI Dependency Injection

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
""",
        "context7_id": "/fastapi/fastapi"
    },
    ("fastapi", "async"): {
        "content": """# FastAPI Async

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
""",
        "context7_id": "/fastapi/fastapi"
    },
    ("pydantic", "validation"): {
        "content": """# Pydantic Validation

## Define and Validate Data Model with Pydantic

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None
    friends: list[int] = []

external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
user = User(**external_data)
print(user)
# User id=123 name='John Doe' signup_ts=datetime.datetime(2017, 6, 1, 12, 22) friends=[1, 2, 3]
```

## Field Validators

```python
from pydantic import BaseModel, ValidationInfo, field_validator

class UserModel(BaseModel):
    password: str
    password_repeat: str

    @field_validator('password_repeat', mode='after')
    @classmethod
    def check_passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data['password']:
            raise ValueError('Passwords do not match')
        return value
```
""",
        "context7_id": "/pydantic/pydantic"
    },
    ("pydantic", "settings"): {
        "content": """# Pydantic Settings

## Configure Pydantic Model with `model_config`

```python
from pydantic import BaseModel

class Knight(BaseModel):
    model_config = dict(frozen=True)
    title: str
    age: int
    color: str = 'blue'
```

## Apply Global Pydantic Configuration via Inherited Base Model

```python
from pydantic import BaseModel, ConfigDict

class Parent(BaseModel):
    model_config = ConfigDict(extra='allow')

class Model(Parent):
    x: str

m = Model(x='foo', y='bar')
print(m.model_dump())
# {'x': 'foo', 'y': 'bar'}
```
""",
        "context7_id": "/pydantic/pydantic"
    },
    ("sqlalchemy", "async"): {
        "content": """# SQLAlchemy Async

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
""",
        "context7_id": "/sqlalchemy/sqlalchemy"
    },
    ("pytest", "async"): {
        "content": """# Pytest Async

## Recommended Async Fixture Wrapper

```python
import asyncio
import pytest

@pytest.fixture
def unawaited_fixture():
    async def inner_fixture():
        return 1
    return inner_fixture()

def test_foo(unawaited_fixture):
    assert 1 == asyncio.run(unawaited_fixture)
```
""",
        "context7_id": "/pytest-dev/pytest"
    },
    ("pytest", "fixtures"): {
        "content": """# Pytest Fixtures

## Define and use pytest fixtures

```python
import pytest

class Fruit:
    def __init__(self, name):
        self.name = name

@pytest.fixture
def my_fruit():
    return Fruit("apple")

@pytest.fixture
def fruit_basket(my_fruit):
    return [Fruit("banana"), my_fruit]

def test_my_fruit_in_basket(my_fruit, fruit_basket):
    assert my_fruit in fruit_basket
```

## Fixture requesting other fixtures

```python
@pytest.fixture
def first_entry():
    return "a"

@pytest.fixture
def order(first_entry):
    return [first_entry]

def test_string(order):
    order.append("b")
    assert order == ["a", "b"]
```
""",
        "context7_id": "/pytest-dev/pytest"
    },
    ("aiosqlite", "async"): {
        "content": """# aiosqlite Async

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
""",
        "context7_id": "/omnilib/aiosqlite"
    },
    ("homeassistant", "websocket"): {
        "content": """# Home Assistant WebSocket API

## Real-time Communication with Home Assistant WebSocket API

```python
import asyncio
import websockets
import json

async def connect_to_homeassistant():
    uri = "ws://localhost:8123/api/websocket"
    async with websockets.connect(uri) as websocket:
        # Receive auth_required
        await websocket.recv()
        # Send auth
        await websocket.send(json.dumps({
            "type": "auth",
            "access_token": "YOUR_TOKEN"
        }))
        # Receive auth result
        auth_result = json.loads(await websocket.recv())
        if auth_result["type"] != "auth_ok":
            return
        
        # Subscribe to state changes
        await websocket.send(json.dumps({
            "id": 1,
            "type": "subscribe_events",
            "event_type": "state_changed"
        }))
        
        # Get all states
        await websocket.send(json.dumps({
            "id": 2,
            "type": "get_states"
        }))
        
        # Call a service
        await websocket.send(json.dumps({
            "id": 3,
            "type": "call_service",
            "domain": "light",
            "service": "turn_on",
            "service_data": {
                "entity_id": "light.bedroom",
                "brightness": 200
            }
        }))
```

## Event Bus - Publishing and Subscribing to Events

```python
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import EVENT_STATE_CHANGED

@callback
def state_changed_listener(event: Event) -> None:
    entity_id = event.data.get("entity_id")
    old_state = event.data.get("old_state")
    new_state = event.data.get("new_state")
    if new_state and old_state:
        print(f"{entity_id} changed from {old_state.state} to {new_state.state}")

remove_listener = hass.bus.async_listen(EVENT_STATE_CHANGED, state_changed_listener)
```
""",
        "context7_id": "/home-assistant/core"
    },
    ("influxdb", "write"): {
        "content": """# InfluxDB Write

## Write Time-Series Data with Point Object

```python
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    point = Point("my_measurement") \\
        .tag("location", "Prague") \\
        .tag("sensor_id", "TLM01") \\
        .field("temperature", 25.3) \\
        .field("humidity", 65.0) \\
        .time(datetime.now(tz=timezone.utc), WritePrecision.NS)

    write_api.write(bucket="my-bucket", org="my-org", record=point)
```

## Write Time-Series Data with Line Protocol

```python
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

with InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org") as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

    line = "h2o_feet,location=coyote_creek water_level=8.12 1568020800000000000"
    write_api.write("my-bucket", "my-org", line)

    # Multiple measurements
    lines = [
        "h2o_feet,location=coyote_creek water_level=8.12 1568020800000000000",
        "h2o_feet,location=santa_monica water_level=2.064 1568020800000000000"
    ]
    write_api.write("my-bucket", "my-org", lines)
```
""",
        "context7_id": "/influxdata/influxdb-client-python"
    },
}


if __name__ == "__main__":
    print("=" * 70)
    print("  Populating Context7 KB Cache")
    print("=" * 70)
    print()
    
    success_count = 0
    error_count = 0
    
    for (library, topic), doc_info in DOCUMENTATION.items():
        print(f"[*] Storing: {library}/{topic}...", end=" ", flush=True)
        
        result = store_doc(
            library=library,
            topic=topic,
            content=doc_info["content"],
            context7_id=doc_info.get("context7_id")
        )
        
        if result:
            print("[OK]")
            success_count += 1
        else:
            print("[X]")
            error_count += 1
    
    print()
    print("=" * 70)
    print("  Population Summary")
    print("=" * 70)
    print(f"[OK] Successfully stored: {success_count}")
    print(f"[X] Errors: {error_count}")
    print(f"[i] Total: {len(DOCUMENTATION)}")
    print()
    print("[i] Run 'python verify_context7.py' to verify cache status")

