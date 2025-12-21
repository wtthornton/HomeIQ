<!--
library: pytest
topic: fixtures
context7_id: /pytest-dev/pytest
cached_at: 2025-12-21T00:41:07.257088+00:00Z
cache_hits: 0
-->

# Pytest Fixtures

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

