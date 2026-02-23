### Pytester Fixture Overview

The Pytester fixture provides an isolated directory for running pytest and testing its functionality. It includes methods to create files, configuration, and manage the test environment.

```APIDOC
## Pytester Fixture

### Description
Provides a `Pytester` instance that can be used to run and test pytest itself. It offers an empty directory for isolated pytest execution and includes facilities to write tests, configuration files, and match expected output. To use it, include `pytest_plugins = "pytester"` in your topmost `conftest.py` file.

### Class
`_Pytester`

### Key Attributes
- `plugins_` (list[str | object]): A list of plugins to use with `parseconfig()` and `runpytest()`. Initially empty, plugins can be added.
- `_path_` (Path): The temporary directory path used for creating files and running tests.

### Core Methods

#### `make_hook_recorder(_pluginmanager_)`
- **Description**: Creates a new `HookRecorder` for a `PytestPluginManager`.

#### `chdir()`
- **Description**: Changes the current working directory to the temporary directory. This is done automatically upon instantiation.

#### `makefile(_ext_, *args, **kwargs)`
- **Description**: Creates new text file(s) in the test directory.
- **Parameters**:
  - `ext` (str): The file extension (e.g., `.py`).
  - `*args` (str): Content strings to be joined by newlines.
  - `**kwargs` (str): Keyword arguments where keys are filenames and values are their contents.
- **Returns**: The first created file (Path).

#### `makeconftest(_source_)`
- **Description**: Writes a `conftest.py` file.
- **Parameters**:
  - `source` (str): The content of the file.
- **Returns**: The `conftest.py` file (Path).

#### `makeini(_source_)`
- **Description**: Writes a `tox.ini` file.
- **Parameters**:
  - `source` (str): The content of the file.
- **Returns**: The `tox.ini` file (Path).

#### `maketoml(_source_)`
- **Description**: Writes a `pytest.toml` file.
- **Parameters**:
  - `source` (str): The content of the file.
- **Returns**: The `pytest.toml` file (Path).

#### `makepyprojecttoml(_source_)`
- **Description**: Writes a `pyproject.toml` file.
- **Parameters**:
  - `source` (str): The content of the file.
- **Returns**: The `pyproject.toml` file (Path).

#### `getinicfg(_source_)`
- **Description**: Returns the pytest section from a `tox.ini` config file.
- **Parameters**:
  - `source` (str): The content of the `tox.ini` file.
- **Returns**: The pytest configuration section.

#### `makepyfile(*args, **kwargs)`
- **Description**: Shortcut for `makefile()` with a `.py` extension. Defaults to the test name with a `.py` extension.
- **Examples**:
  ```python
def test_something(pytester):
    pytester.makepyfile("foobar")
    pytester.makepyfile(custom="foobar")
```

#### `maketxtfile(*args, **kwargs)`
- **Description**: Shortcut for `makefile()` with a `.txt` extension. Defaults to the test name with a `.txt` extension.
- **Examples**:
  ```python
def test_something(pytester):
    pytester.maketxtfile("foobar")
    pytester.maketxtfile(custom="foobar")
```

#### `syspathinsert(_path=None_)`
- **Description**: Prepends a directory to `sys.path`. This is undone automatically at the end of each test.
- **Parameters**:
  - `path` (str | PathLike | None): The path to prepend.

#### `mkdir(_name_)`
- **Description**: Creates a new (sub)directory.
- **Parameters**:
  - `name` (str | PathLike): The name of the directory, relative to the pytester path.
- **Returns**: The created directory (Path).

#### `mkpydir(_name_)`
- **Description**: Creates a new Python package directory (a directory with an `__init__.py` file).
- **Parameters**:
  - `name` (str | PathLike): The name of the package directory.

#### `copy_example(_name=None_)`
- **Description**: Copies a file from the project's directory into the test directory.
- **Parameters**:
  - `name` (str | None): The name of the file to copy.
```

### Force Condensed Summary Output in Pytest

Forces a condensed summary output regardless of the verbosity level. This ensures a brief overview of test results even with high verbosity settings.

```bash
pytest --force-short-summary
```

### Nested Parametrize-Value Markers

Supports nested parametrize-value markers, allowing for more complex and combined parametrization scenarios. This enhances the expressiveness of test parametrization.

```python
import pytest

@pytest.mark.parametrize("a", [1, 2])
@pytest.mark.parametrize("b", [3, 4])
def test_nested_parametrize(a, b):
    assert isinstance(a, int)
    assert isinstance(b, int)

# This allows combining multiple parametrize markers on a single test function,
# creating a Cartesian product of the parameter values.
```

### Parametrizing with Repeated Values

Adds preliminary support for parametrizing tests with repeated same values. This is useful for testing scenarios where calling a function or method multiple times with the same input should yield consistent results.

```python
import pytest

@pytest.mark.parametrize("value", [1, 2, 1, 3, 2])
def test_with_repeated_values(value):
    assert isinstance(value, int)

# This allows testing the behavior of a test with the same parameter value multiple times,
# which can be useful for debugging or ensuring idempotency.
```

### Concise Traceback Printing in Pytest

Introduces the `--tb=line` option for Pytest, which prints a single-line summary for each failing test. This summary includes the filename, line number, and failure value, providing a quick overview of test failures.

```bash
py.test --tb=line
```

### Handle Unserialization Failure for Reports (Python)

A utility function to handle and report errors that occur during the deserialization of report objects. It raises a `RuntimeError` with detailed information about the failure, including the unexpected type name and the report dictionary.

```python
def _report_unserialization_failure(
    type_name: str, report_class: type[BaseReport], reportdict
) -> NoReturn:
    url = "https://github.com/pytest-dev/pytest/issues"
    stream = StringIO()
    pprint("-" * 100, stream=stream)
    pprint(f"INTERNALERROR: Unknown entry type returned: {type_name}", stream=stream)
    pprint(f"report_name: {report_class}", stream=stream)
    pprint(reportdict, stream=stream)
    pprint(f"Please report this bug at {url}", stream=stream)
    pprint("-" * 100, stream=stream)
    raise RuntimeError(stream.getvalue())
```

### List All Tox Environments and Descriptions

This command lists all available tox environments along with their descriptions. It is useful for contributors to understand the purpose of each tox environment in the development setup. The `-a` flag shows all environments, and `-v` displays their descriptions.

```bash
tox -av
```

### Base Report Class for Pytest Test Results

Defines the fundamental structure for test reports in pytest. It holds information about the test outcome, location, long representation of failures or errors, and captured sections. It provides methods to access specific report details like captured output and log.

```python
class BaseReport:
    when: str | None
    location: tuple[str, int | None, str] | None
    longrepr: (
        None | ExceptionInfo[BaseException] | tuple[str, int, str] | str | TerminalRepr
    )
    sections: list[tuple[str, str]]
    nodeid: str
    outcome: Literal["passed", "failed", "skipped"]

    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)

    if TYPE_CHECKING:
        # Can have arbitrary fields given to __init__().
        def __getattr__(self, key: str) -> Any: ...

    def toterminal(self, out: TerminalWriter) -> None:
        if hasattr(self, "node"):
            worker_info = getworkerinfoline(self.node)
            if worker_info:
                out.line(worker_info)

        longrepr = self.longrepr
        if longrepr is None:
            return

        if hasattr(longrepr, "toterminal"):
            longrepr_terminal = cast(TerminalRepr, longrepr)
            longrepr_terminal.toterminal(out)
        else:
            try:
                s = str(longrepr)
            except UnicodeEncodeError:
                s = "<unprintable longrepr>"
            out.line(s)

    def get_sections(self, prefix: str) -> Iterator[tuple[str, str]]:
        for name, content in self.sections:
            if name.startswith(prefix):
                yield prefix, content

    @property
    def longreprtext(self) -> str:
        """Read-only property that returns the full string representation of
        ``longrepr``.

        .. versionadded:: 3.0
        """
        file = StringIO()
        tw = TerminalWriter(file)
        tw.hasmarkup = False
        self.toterminal(tw)
        exc = file.getvalue()
        return exc.strip()

    @property
    def caplog(self) -> str:
        """Return captured log lines, if log capturing is enabled.

        .. versionadded:: 3.5
        """
        return "\n".join(
            content for (prefix, content) in self.get_sections("Captured log")
        )

    @property
    def capstdout(self) -> str:
        """Return captured text from stdout, if capturing is enabled.

        .. versionadded:: 3.0
        """
        return "".join(
            content for (prefix, content) in self.get_sections("Captured stdout")
        )

    @property
    def capstderr(self) -> str:
        """Return captured text from stderr, if capturing is enabled.

        .. versionadded:: 3.0
        """
        return "".join(
            content for (prefix, content) in self.get_sections("Captured stderr")
        )

    @property
    def passed(self) -> bool:
        """Whether the outcome is passed."""
        return self.outcome == "passed"

    @property
    def failed(self) -> bool:
        """Whether the outcome is failed."""
        return self.outcome == "failed"

    @property
    def skipped(self) -> bool:
        """Whether the outcome is skipped."""
        return self.outcome == "skipped"

    @property
    def fspath(self) -> str:
        """The path portion of the reported node, as a string."""
        return self.nodeid.split("::")[0]

    @property
    def count_towards_summary(self) -> bool:
        """**Experimental** Whether this report should be counted towards the
        totals shown at the end of the test session: "1 passed, 1 failure, etc".

        .. note::
```

### Test Layout Example: Tests Outside Application Code (Directory Structure)

Illustrates a common project structure where test files are placed in a separate 'tests/' directory, distinct from the application source code in 'src/'. This separation is often recommended for clarity and maintainability.

```directory
pyproject.toml
src/
    mypkg/
        __init__.py
        app.py
        view.py
tests/
    test_app.py
    test_view.py
    ...
```

### Prevent Remote Operations with Global Patch

Provides an example of how to globally prevent the 'requests' library from making actual HTTP requests across all tests. This is typically achieved by defining a patch in a conftest.py file, often with the 'autouse=True' option for automatic application.

```python
# Example for conftest.py
import requests
from unittest.mock import MagicMock


def pytest_configure(config):
    # Mock requests.get to do nothing or return a dummy response
    # This prevents actual network calls during testing.
    mock_get = MagicMock()
    mock_get.return_value.json.return_value = {"status": "success"} # Example dummy response
    requests.get = mock_get
```