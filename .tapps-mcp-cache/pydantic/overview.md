### Distinguish Pydantic Dataclasses from Stdlib Dataclasses

This example demonstrates how to determine if a dataclass is a standard Python `dataclasses.dataclass` or a Pydantic-specific dataclass. It shows that `dataclasses.is_dataclass()` returns `True` for both, while `pydantic.dataclasses.is_pydantic_dataclass()` specifically identifies Pydantic dataclasses.

```python
import dataclasses

import pydantic


@dataclasses.dataclass
class StdLibDataclass:
    id: int


PydanticDataclass = pydantic.dataclasses.dataclass(StdLibDataclass)

print(dataclasses.is_dataclass(StdLibDataclass))
#嶼 True
print(pydantic.dataclasses.is_pydantic_dataclass(StdLibDataclass))
#嶼 False

print(dataclasses.is_dataclass(PydanticDataclass))
#嶼 True
print(pydantic.dataclasses.is_pydantic_dataclass(PydanticDataclass))
#嶼 True
```

### Pydantic Dataclass with Field and dataclasses.field

This example illustrates combining `dataclasses.field` and `pydantic.Field` within a Pydantic dataclass for advanced field definitions. It shows how to use `default_factory` for mutable defaults with `dataclasses.field` and apply Pydantic-specific validation constraints like `ge` (greater than or equal) and `le` (less than or equal) with `pydantic.Field`. The `metadata` argument is also demonstrated for adding extra information to a field.

```python
import dataclasses
from typing import Optional

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str = 'John Doe'
    friends: list[int] = dataclasses.field(default_factory=lambda: [0])
    age: Optional[int] = dataclasses.field(
        default=None,
        metadata={'title': 'The age of the user', 'description': 'do not lie!'},
    )
    height: Optional[int] = Field(
        default=None, title='The height in cm', ge=50, le=300
    )


user = User(id='42', height='250')
print(user)
```

### Configure Pydantic Dataclass Validation

This code demonstrates two methods for configuring Pydantic dataclasses, similar to Pydantic models. Configuration, such as `validate_assignment=True`, can be applied either by passing a `ConfigDict` directly to the `@dataclass` decorator or by defining a `__pydantic_config__` attribute within the dataclass. This allows fine-grained control over validation behavior for dataclass instances.

```python
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


# Option 1 -- using the decorator argument:
@dataclass(config=ConfigDict(validate_assignment=True))  # (1)!
class MyDataclass1:
    a: int


# Option 2 -- using an attribute:
@dataclass
class MyDataclass2:
    a: int

    __pydantic_config__ = ConfigDict(validate_assignment=True)
```

### Apply Pydantic Dataclass Decorator to Stdlib Dataclass

This example illustrates how to apply the `pydantic.dataclasses.dataclass` decorator directly to an existing standard library dataclass. This action creates a new subclass that incorporates Pydantic's validation capabilities, as shown by type coercion during instantiation.

```python
import dataclasses

import pydantic


@dataclasses.dataclass
class A:
    a: int


PydanticA = pydantic.dataclasses.dataclass(A)
print(PydanticA(a='1'))
#嶼 A(a=1)
```

### Inherit Standard Library Dataclasses with Pydantic

This code demonstrates how Pydantic automatically validates fields when inheriting a Pydantic dataclass from standard library dataclasses. It shows validation and type conversion on instantiation, and raises `ValidationError` for invalid inputs.

```python
import dataclasses

import pydantic


@dataclasses.dataclass
class Z:
    z: int


@dataclasses.dataclass
class Y(Z):
    y: int = 0


@pydantic.dataclasses.dataclass
class X(Y):
    x: int = 0


foo = X(x=b'1', y='2', z='3')
print(foo)
#嶼 X(z=3, y=2, x=1)

try:
    X(z='pika')
except pydantic.ValidationError as e:
    print(e)
    """
    1 validation error for X
    z
      Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='pika', input_type=str]
    """
```

### Validate Stdlib Dataclasses within Pydantic Models

This code demonstrates how standard library dataclasses are validated when used as fields within a Pydantic `BaseModel`. It highlights the use of `revalidate_instances='always'` in `ConfigDict` to ensure attributes of nested dataclass instances are re-validated, catching type mismatches.

```python
import dataclasses
from typing import Optional

from pydantic import BaseModel, ConfigDict, ValidationError


@dataclasses.dataclass(frozen=True)
class User:
    name: str


class Foo(BaseModel):
    # Required so that pydantic revalidates the model attributes:
    model_config = ConfigDict(revalidate_instances='always')

    user: Optional[User] = None


# nothing is validated as expected:
user = User(name=['not', 'a', 'string'])
print(user)
#嶼 User(name=['not', 'a', 'string'])


try:
    Foo(user=user)
except ValidationError as e:
    print(e)
    """
    1 validation error for Foo
    user.name
      Input should be a valid string [type=string_type, input_value=['not', 'a', 'string'], input_type=list]
    """

foo = Foo(user=User(name='pika'))
try:
    foo.user.name = 'bulbi'
except dataclasses.FrozenInstanceError as e:
    print(e)
    #嶼 cannot assign to field 'name'
```

### Define and Validate Pydantic Dataclass

This snippet demonstrates how to use Pydantic's `@dataclass` decorator to apply validation to standard Python dataclasses. It defines a `User` dataclass with `int`, `str`, and `Optional[datetime]` fields, showcasing type coercion and default values. An instance is created with string inputs for `id` and `signup_ts`, which Pydantic automatically validates and converts.

```python
from datetime import datetime
from typing import Optional

from pydantic.dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str = 'John Doe'
    signup_ts: Optional[datetime] = None


user = User(id='42', signup_ts='2032-06-21T12:00')
print(user)
```

### Pydantic Revalidation of Nested Generic Models

This example demonstrates Pydantic's revalidation mechanism for nested generic models when a field expects a `GenericModel[Any]` but receives a `GenericModel[int]`. It shows how Pydantic attempts to revalidate the contained data for intuitive results, even if the initial type check might fail, and the final representation reflects the `Any` type.

```python
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class GenericModel(BaseModel, Generic[T]):
    a: T


class Model(BaseModel):
    inner: GenericModel[Any]


print(repr(Model.model_validate(Model(inner=GenericModel[int](a=1)))))
```

### Google-Style Class Docstring with Attributes

Demonstrates proper formatting of a Python class docstring using Google-style conventions with documented class attributes. This example shows how to document a class and its attributes with descriptions and default values, following PEP 257 guidelines.

```python
class Foo:
    """A class docstring.

    Attributes:
        bar: A description of bar. Defaults to "bar".
    """

    bar: str = 'bar'
```

### Handle Custom Types in Dataclasses with Pydantic Validation

This snippet illustrates how Pydantic handles custom types within standard library dataclasses when they are part of a `BaseModel`. It shows that Pydantic will raise `PydanticSchemaGenerationError` for unknown custom types and how to resolve this by setting `arbitrary_types_allowed=True` in the `ConfigDict`.

```python
import dataclasses

from pydantic import BaseModel, ConfigDict
from pydantic.errors import PydanticSchemaGenerationError


class ArbitraryType:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'ArbitraryType(value={self.value!r})'


@dataclasses.dataclass
class DC:
    a: ArbitraryType
    b: str


# valid as it is a stdlib dataclass without validation:
my_dc = DC(a=ArbitraryType(value=3), b='qwe')

try:

    class Model(BaseModel):
        dc: DC
        other: str

    # invalid as dc is now validated with pydantic, and ArbitraryType is not a known type
    Model(dc=my_dc, other='other')

except PydanticSchemaGenerationError as e:
    print(e.message)
    """
    Unable to generate pydantic-core schema for <class '__main__.ArbitraryType'>. Set `arbitrary_types_allowed=True` in the model_config to ignore this error or implement `__get_pydantic_core_schema__` on your type to fully support it.

    If you got this error by calling handler(<some type>) within `__get_pydantic_core_schema__` then you likely need to call `handler.generate_schema(<some type>)` since we do not call `__get_pydantic_core_schema__` on `<some type>` otherwise to avoid infinite recursion.
    """


# valid as we set arbitrary_types_allowed=True, and that config pushes down to the nested vanilla dataclass
class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dc: DC
    other: str


m = Model(dc=my_dc, other='other')
print(repr(m))
#嶼 Model(dc=DC(a=ArbitraryType(value=3), b='qwe'), other='other')
```