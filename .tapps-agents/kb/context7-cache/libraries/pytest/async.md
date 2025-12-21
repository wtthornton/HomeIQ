<!--
library: pytest
topic: async
context7_id: /pytest-dev/pytest
cached_at: 2025-12-21T00:41:07.224572+00:00Z
cache_hits: 0
-->

# Pytest Async

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

