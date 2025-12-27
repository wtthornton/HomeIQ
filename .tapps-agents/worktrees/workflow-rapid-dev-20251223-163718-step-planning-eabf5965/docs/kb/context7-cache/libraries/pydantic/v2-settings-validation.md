# Pydantic V2 Settings and Validation

**Library:** Pydantic  
**Topic:** V2 settings, validation, and migration patterns  
**Cached:** 2025-12-03  
**Source:** Context7 - /pydantic/pydantic

## Overview

Pydantic V2 provides enhanced validation, settings management, and improved type handling. This document covers V2-specific patterns, settings configuration, and validation best practices.

## Key Patterns

### ConfigDict for Model Configuration

Use `ConfigDict` for fine-grained control over model behavior including strict type validation, immutability, validation on assignment, and extra field handling.

```python
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,  # No type coercion
        frozen=True,  # Immutable instances
        validate_assignment=True,  # Validate on attribute assignment
        extra='forbid',  # Reject extra fields
        str_strip_whitespace=True,
        str_min_length=1
    )

    id: int
    name: str

class FlexibleModel(BaseModel):
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields
        populate_by_name=True,  # Accept both alias and field name
        validate_default=True,  # Validate default values
        use_enum_values=True,  # Serialize enums as values
        arbitrary_types_allowed=True  # Allow custom types
    )

    user_id: int = Field(alias='id')
    data: dict = {}
```

### Field Validators with ValidationInfo

Pydantic V2's `@field_validator` uses `ValidationInfo` to provide access to configuration and field metadata.

```python
from pydantic import BaseModel, ValidationInfo, field_validator

class Model(BaseModel):
    x: int

    @field_validator('x')
    def val_x(cls, v: int, info: ValidationInfo) -> int:
        assert info.config is not None
        print(info.config.get('title'))
        print(cls.model_fields[info.field_name].is_required())
        return v
```

### Validate Default Values

Enable validation for default values by setting `validate_default=True` in `Field`.

```python
from pydantic import BaseModel, Field, ValidationError

class User(BaseModel):
    age: int = Field(default='twelve', validate_default=True)

try:
    user = User()
except ValidationError as e:
    print(e)
```

### TypeAdapter for Non-Model Types

Use `TypeAdapter` to validate non-`BaseModel` types, replacing older utility functions like `parse_obj_as`.

```python
from pydantic import TypeAdapter

adapter = TypeAdapter(list[int])
assert adapter.validate_python(['1', '2', '3']) == [1, 2, 3]
print(adapter.json_schema())
# {'items': {'type': 'integer'}, 'type': 'array'}
```

### Context-Based Validation

Pass validation context when instantiating models using `ContextVar` and custom `__init__`.

```python
from contextvars import ContextVar
from pydantic import BaseModel, ValidationInfo, field_validator

_init_context_var = ContextVar('_init_context_var', default=None)

class Model(BaseModel):
    my_number: int

    @field_validator('my_number')
    @classmethod
    def multiply_with_context(cls, value: int, info: ValidationInfo) -> int:
        if isinstance(info.context, dict):
            multiplier = info.context.get('multiplier', 1)
            value = value * multiplier
        return value
```

### Literal Validation

Use `typing.Literal` within Pydantic `BaseModel` to restrict field values to predefined options.

```python
from typing import Literal
from pydantic import BaseModel, ValidationError

class Pie(BaseModel):
    flavor: Literal['apple', 'pumpkin']
    quantity: Literal[1, 2] = 1
```

## Migration from V1

### @validator → @field_validator

- V1: `@validator('field', always=True)`
- V2: Use `validate_default=True` in `Field` instead of `always=True`

### Union Validation

V2 preserves input type even if other union choices would also validate. Use `Field(union_mode='left_to_right')` to revert to V1 behavior.

## Best Practices

1. **Use ConfigDict**: Replace old `Config` class with `ConfigDict`
2. **Validate Defaults**: Set `validate_default=True` when defaults need validation
3. **TypeAdapter**: Use for non-model type validation
4. **Context Validation**: Use `ValidationInfo.context` for context-aware validation
5. **Strict Mode**: Enable `strict=True` for production code to prevent type coercion

## Related Documentation

- Pydantic V2 Migration: https://github.com/pydantic/pydantic/blob/main/docs/migration.md
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

