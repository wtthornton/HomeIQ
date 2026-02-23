### Pytest Monkeypatch Fixture for Test Patches

The monkeypatch fixture provides a convenient way to modify objects, dictionaries, and os.environ during tests. It offers methods like setattr, delattr, setitem, delitem, setenv, delenv, syspath_prepend, and chdir. All modifications are automatically undone after the test function or fixture completes. The 'raising' parameter controls whether errors are raised for non-existent targets.

```python
@fixture
def monkeypatch() -> Generator[MonkeyPatch]:
    """A convenient fixture for monkey-patching.

    The fixture provides these methods to modify objects, dictionaries, or
    :data:`os.environ`:

    * :meth:`monkeypatch.setattr(obj, name, value, raising=True) <pytest.MonkeyPatch.setattr>`
    * :meth:`monkeypatch.delattr(obj, name, raising=True) <pytest.MonkeyPatch.delattr>`
    * :meth:`monkeypatch.setitem(mapping, name, value) <pytest.MonkeyPatch.setitem>`
    * :meth:`monkeypatch.delitem(obj, name, raising=True) <pytest.MonkeyPatch.delitem>`
    * :meth:`monkeypatch.setenv(name, value, prepend=None) <pytest.MonkeyPatch.setenv>`
    * :meth:`monkeypatch.delenv(name, raising=True) <pytest.MonkeyPatch.delenv>`
    * :meth:`monkeypatch.syspath_prepend(path) <pytest.MonkeyPatch.syspath_prepend>`
    * :meth:`monkeypatch.chdir(path) <pytest.MonkeyPatch.chdir>`
    * :meth:`monkeypatch.context() <pytest.MonkeyPatch.context>`

    All modifications will be undone after the requesting test function or
    fixture has finished. The ``raising`` parameter determines if a :class:`KeyError`
    or :class:`AttributeError` will be raised if the set/deletion operation does not have the
    specified target.

    To undo modifications done by the fixture in a contained scope,
    use :meth:`context() <pytest.MonkeyPatch.context>`.
    """
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()
```

### Setting an Environment Variable with MonkeyPatch in Python

Illustrates how to set environment variables using monkeypatch.setenv. It also covers the 'prepend' option for adding values to existing environment variables.

```python
monkeypatch.setenv("MY_VAR", "my_value")
monkeypatch.setenv("PATH", "/usr/bin", prepend="|")
```

### MonkeyPatch Context Manager for Localized Patches

The context manager allows for localized monkeypatching within a 'with' block. It returns a new MonkeyPatch object, and any modifications made using this object are automatically undone upon exiting the block. This is useful for scenarios where specific patches need to be temporary and cleaned up before the test function completes.

```python
@classmethod
@contextmanager
def context(cls) -> Generator[MonkeyPatch]:
    """Context manager that returns a new :class:`MonkeyPatch` object
    which undoes any patching done inside the ``with`` block upon exit.

    Example:

    .. code-block:: python

        import functools


        def test_partial(monkeypatch):
            with monkeypatch.context() as m:
                m.setattr(functools, "partial", 3)

    Useful in situations where it is desired to undo some patches before the test ends,
```

### Unicode Handling with monkeypatch.setattr

Fixes unicode handling with the `monkeypatch.setattr(import_path, value)` API. This ensures that unicode strings can be correctly set as attributes using monkeypatch, especially when dealing with import paths.

```python
import pytest

def test_unicode_monkeypatch(monkeypatch):
    module_name = "my_module"
    attribute_name = "unicode_attr"
    unicode_value = "你好"

    # Simulate creating a module if it doesn't exist
    import sys
    if module_name not in sys.modules:
        import types
        sys.modules[module_name] = types.ModuleType(module_name)

    monkeypatch.setattr(f"{module_name}.{attribute_name}", unicode_value)

    import my_module
    assert my_module.unicode_attr == unicode_value

# This fix ensures correct handling of unicode strings when using monkeypatch.setattr,
# preventing potential encoding issues.
```

### Using MonkeyPatch Context Manager in Python

Demonstrates how to use the monkeypatch context manager to temporarily modify attributes within a specific scope. This is useful for isolating patches and ensuring they are undone automatically upon exiting the 'with' block.

```python
import functools

def test_partial(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(functools, "partial", 3)
```

### Pytest: Monkeypatching Attributes with setattr

Provides a new variant of `monkeypatch.setattr()` for a more concise way to patch out classes or functions from modules. This simplifies mocking by allowing direct specification of the module and attribute name.

```python
def my_mock_function(*args, **kwargs):
    pass

monkeypatch.setattr("requests.get", my_mock_function)
# Now, any call to requests.get will actually call my_mock_function
```

### Access Monkeypatch Instance

Provides access to the MonkeyPatch instance for modifying behavior during test execution.

```python
monkeypatch_instance = testdir.monkeypatch
```

### Pytest Unicode Handling with Monkeypatch

Fixes unicode handling issues with the `monkeypatch.setattr(import_path, value)` API. This ensures that unicode strings are correctly manipulated and set when using monkeypatch for modifications.

```python
import pytest

def test_monkeypatch_unicode(monkeypatch):
    unicode_string = "你好"
    # Correctly patch an attribute with a unicode string
    monkeypatch.setattr('module.attribute', unicode_string)

    # Now, when accessing module.attribute, it will hold the unicode string value.
    # This fix addresses issues where unicode might have been mishandled.
    assert module.attribute == unicode_string
```

### Undo MonkeyPatch Changes

Reverts all modifications made by the MonkeyPatch fixture. It iterates through the recorded changes in reverse order and applies the original values or removes modified items. This is automatically called during tear-down.

```python
def undo(self) -> None:
    """Undo previous changes.

    This call consumes the undo stack. Calling it a second time has no
    effect unless you do more monkeypatching after the undo call.

    There is generally no need to call `undo()`, since it is
    called automatically during tear-down.

    .. note::
        The same `monkeypatch` fixture is used across a
        single test function invocation. If `monkeypatch` is used both by
        the test function itself and one of the test fixtures,
        calling `undo()` will undo all of the changes made in
        both functions.

        Prefer to use :meth:`context() <pytest.MonkeyPatch.context>` instead.
    """
    for obj, name, value in reversed(self._setattr):
        if value is not notset:
            setattr(obj, name, value)
        else:
            delattr(obj, name)
    self._setattr[:] = []
    for dictionary, key, value in reversed(self._setitem):
        if value is notset:
            try:
```

### Set Environment Variable with Pytest MonkeyPatch

Sets an environment variable to a specified value. It can optionally prepend the existing value with a separator if a `prepend` character is provided. Handles type conversion to string and issues a warning for non-string values.

```python
def setenv(self, name: str, value: str, prepend: str | None = None) -> None:
    """Set environment variable ``name`` to ``value``.

    If ``prepend`` is a character, read the current environment variable
    value and prepend the ``value`` adjoined with the ``prepend``
    character.
    """
    if not isinstance(value, str):
        warnings.warn(
            PytestWarning(
                f"Value of environment variable {name} type should be str, but got "
                f"{value!r} (type: {type(value).__name__}); converted to str implicitly"
            ),
            stacklevel=2,
        )
        value = str(value)
    if prepend and name in os.environ:
        value = value + prepend + os.environ[name]
    self.setitem(os.environ, name, value)
```