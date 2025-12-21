<!--
library: pydantic
topic: settings
context7_id: /pydantic/pydantic
cached_at: 2025-12-21T00:41:07.156809+00:00Z
cache_hits: 0
-->

# Pydantic Settings

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

