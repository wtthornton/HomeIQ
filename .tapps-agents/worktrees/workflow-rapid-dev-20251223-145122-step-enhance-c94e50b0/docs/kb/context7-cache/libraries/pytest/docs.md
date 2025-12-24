# pytest Documentation Cache
# Version: 7.4.3+
# Last Updated: 2025-10-12
# Source: Context7 (/pytest-dev/pytest)

## Overview
pytest is a mature full-featured Python testing framework that helps you write better programs. This cache contains focused documentation on testing, fixtures, parametrization, and async handling for version 7.4.3+.

## Testing Framework Fundamentals

### Core Concepts
- **Test discovery**: Automatic test finding (`test_*.py` or `*_test.py`)
- **Assertion introspection**: Detailed failure reporting with context
- **Fixture system**: Dependency injection for test setup
- **Plugin architecture**: Extensible framework with hooks
- **Parametrization**: Data-driven testing with `pytest.mark.parametrize`
- **Parallel execution**: Concurrent test running with pytest-xdist

### Test Structure
```python
# test_example.py

def test_simple():
    """Simple test function"""
    assert 1 + 1 == 2

class TestClass:
    """Grouped test methods"""
    def test_method_one(self):
        assert True
    
    def test_method_two(self):
        assert not False
```

### Assertion System
- **Built-in assertions**: Python `assert` statements with introspection
- **Assertion rewriting**: Enhanced assert statements with detailed output
- **Custom assertions**: User-defined assertion functions
- **Failure reporting**: Comprehensive error display with context

## Fixture Management

### Fixture Basics
```python
import pytest

@pytest.fixture
def sample_data():
    """Basic fixture returning data"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

### Fixture Scopes
```python
# Function scope (default) - per test
@pytest.fixture(scope="function")
def function_fixture():
    return "new instance per test"

# Class scope - per test class
@pytest.fixture(scope="class")
def class_fixture():
    return "shared across class"

# Module scope - per module
@pytest.fixture(scope="module")
def module_fixture():
    return "shared across module"

# Session scope - entire test session
@pytest.fixture(scope="session")
def session_fixture():
    return "shared across all tests"
```

### Fixture Dependencies
```python
@pytest.fixture
def database():
    db = Database()
    yield db
    db.close()

@pytest.fixture
def user(database):
    """Fixture that depends on database fixture"""
    return database.create_user("test_user")

def test_user(user):
    assert user.name == "test_user"
```

### Fixture Cleanup
```python
@pytest.fixture
def resource():
    # Setup
    r = allocate_resource()
    
    # Provide to test
    yield r
    
    # Cleanup (always runs)
    r.cleanup()
```

### Autouse Fixtures
```python
@pytest.fixture(autouse=True)
def reset_database():
    """Automatically used by all tests in scope"""
    database.reset()
```

## Test Parametrization

### Basic Parametrization
```python
import pytest

@pytest.mark.parametrize("test_input,expected", [
    ("3+5", 8),
    ("2+4", 6),
    ("6*9", 42)
])
def test_eval(test_input, expected):
    assert eval(test_input) == expected
```

### Multiple Parameter Sets
```python
@pytest.mark.parametrize("x", [0, 1])
@pytest.mark.parametrize("y", [2, 3])
def test_foo(x, y):
    """Generates all combinations: (0,2), (0,3), (1,2), (1,3)"""
    pass
```

### Parametrizing with Marks
```python
@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("3+5", 8),
        ("2+4", 6),
        pytest.param("6*9", 42, marks=pytest.mark.xfail)
    ]
)
def test_eval(test_input, expected):
    assert eval(test_input) == expected
```

### Parametrize Entire Class
```python
@pytest.mark.parametrize("n,expected", [(1, 2), (3, 4)])
class TestClass:
    def test_simple_case(self, n, expected):
        assert n + 1 == expected
    
    def test_weird_simple_case(self, n, expected):
        assert (n * 1) + 1 == expected
```

### Parametrize All Tests in Module
```python
# Apply to all tests in module
pytestmark = pytest.mark.parametrize("n,expected", [(1, 2), (3, 4)])

class TestClass:
    def test_simple_case(self, n, expected):
        assert n + 1 == expected
```

### Fixture Parametrization
```python
@pytest.fixture(params=[0, 1, pytest.param(2, marks=pytest.mark.skip)])
def data_set(request):
    """Fixture parametrized with values and marks"""
    return request.param

def test_data(data_set):
    """Runs for each param: 0, 1, and skips 2"""
    pass
```

### Combined Fixture Parametrization
```python
@pytest.fixture(params=["mysql", "pg"])
def db(request):
    """Parametrized fixture for different databases"""
    if request.param == "mysql":
        db = MySQL()
    elif request.param == "pg":
        db = PG()
    request.addfinalizer(db.destroy)
    return db

def test_with_db(db):
    """Runs twice: once with mysql, once with pg"""
    assert db.is_connected()
```

### Session Scope with Parametrization
```python
@pytest.fixture(scope="session", params=["mysql", "pg"])
def db(request):
    """Created once per session for each parameter"""
    if request.param == "mysql":
        db = MySQL()
    elif request.param == "pg":
        db = PG()
    request.addfinalizer(db.destroy)
    return db
```

## Dynamic Test Generation

### pytest_generate_tests Hook
```python
# conftest.py

def pytest_addoption(parser):
    """Add custom command-line option"""
    parser.addoption(
        "--stringinput",
        action="append",
        default=[],
        help="list of stringinputs to pass to test functions",
    )

def pytest_generate_tests(metafunc):
    """Dynamically parametrize tests based on CLI options"""
    if "stringinput" in metafunc.fixturenames:
        metafunc.parametrize(
            "stringinput", 
            metafunc.config.getoption("stringinput")
        )
```

```python
# test_strings.py

def test_valid_string(stringinput):
    """Test dynamically parametrized from CLI"""
    assert stringinput.isalpha()
```

### Fixture Request Pattern (Advanced)
```python
@pytest.fixture(
    params=[
        pytest.fixture_request("default_context"),
        pytest.fixture_request("extra_context"),
    ]
)
def context(request):
    """Returns values from multiple fixtures sequentially"""
    return request.param
```

## Async Testing (pytest-asyncio)

### Async Fixture Handling (7.4+)

**DEPRECATED Pattern (causes warnings in 8.4+):**
```python
import asyncio
import pytest

@pytest.fixture
async def unawaited_fixture():
    return 1

def test_foo(unawaited_fixture):
    # ⚠️ Deprecated - causes 'unawaited coroutine' warning
    assert 1 == asyncio.run(unawaited_fixture)
```

**RECOMMENDED Pattern:**
```python
import asyncio
import pytest

@pytest.fixture
async def async_fixture():
    return 1

@pytest.fixture
def sync_fixture(async_fixture):
    """Wrap async fixture in sync fixture"""
    return asyncio.run(async_fixture)

def test_foo(sync_fixture):
    assert sync_fixture == 1
```

## Test Configuration

### pytest.ini Configuration
```ini
[pytest]
# Test discovery patterns
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Minimum version
minversion = 7.4

# Test paths
testpaths = tests

# Markers
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    
# Coverage
addopts = --cov=src --cov-report=html

# Disable test ID escaping (use with caution)
# disable_test_id_escaping_and_forfeit_all_rights_to_community_support = True
```

## Best Practices

### Test Organization
```python
# Organize by functionality
tests/
    unit/
        test_module_a.py
        test_module_b.py
    integration/
        test_api.py
        test_database.py
    conftest.py  # Shared fixtures
```

### Fixture Strategy
1. Use appropriate scopes to minimize setup/teardown
2. Keep fixtures focused and single-purpose
3. Use fixture dependencies for complex setups
4. Clean up resources with `yield` pattern
5. Use `autouse` sparingly

### Parametrization Strategy
1. Use `pytest.mark.parametrize` for simple data-driven tests
2. Use fixture parametrization for setup variations
3. Combine parametrization for combinatorial testing
4. Use marks to skip/xfail specific parameter sets
5. Use `pytest_generate_tests` for dynamic parametrization

### Assertion Best Practices
1. Use plain `assert` statements
2. Let pytest's introspection show context
3. Add custom messages when needed: `assert x == y, "x should equal y"`
4. Use pytest's built-in helpers when available

## Common Patterns

### Setup/Teardown with Fixtures
```python
@pytest.fixture
def setup_teardown():
    # Setup
    print("Setting up")
    resource = create_resource()
    
    yield resource
    
    # Teardown
    print("Tearing down")
    resource.cleanup()
```

### Interdependent Fixtures
```python
@pytest.fixture(params=["smtp.gmail.com", "mail.python.org"])
def smtp_connection(request):
    return SMTPConnection(request.param)

@pytest.fixture
def app(smtp_connection):
    """App depends on smtp_connection"""
    return App(smtp_connection)

def test_smtp_connection_exists(app):
    """Runs twice, once for each smtp_connection param"""
    assert app.smtp is not None
```

### Empty Parameter Handling
When no parameters provided, test is skipped:
```
SKIPPED [1] test_strings.py: got empty parameter set for (stringinput)
```

## Migration Notes

### pytest 8.4+ Async Changes
- Direct use of async fixtures by sync tests is deprecated
- Wrap async fixtures in sync fixtures for sync tests
- Use pytest-asyncio for proper async test support

### pytest 7.4+ Features
- Enhanced parametrization support
- Improved fixture request handling
- Better async/await support with pytest-asyncio

## Performance Tips

1. Use appropriate fixture scopes (session > module > class > function)
2. Enable parallel execution with pytest-xdist
3. Use markers to selectively run tests
4. Cache expensive fixture results
5. Profile tests with `pytest --durations=10`

## Plugins Ecosystem

Common pytest plugins:
- **pytest-xdist**: Parallel test execution
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **pytest-mock**: Enhanced mocking
- **pytest-django**: Django integration
- **pytest-flask**: Flask integration
