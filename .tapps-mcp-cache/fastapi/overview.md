### FastAPI Request Body Features Overview

Summary of FastAPI's capabilities for handling request bodies with Pydantic models, including automatic validation, data conversion, editor support, and schema documentation.

```APIDOC
## FastAPI Request Body Handling

### Overview
FastAPI provides maximum flexibility for request body handling through Pydantic models while maintaining simple, elegant code.

### Supported Body Types

#### 1. Pure Lists
```python
images: list[Image]
```
- Declare list type in function parameter
- Automatic conversion of incoming dictionaries to Pydantic models
- Full editor support for items within lists

#### 2. Typed Dictionaries
```python
weights: dict[int, float]
```
- Accept dictionaries with known key and value types
- Dynamic field names not known in advance
- Automatic type conversion (e.g., JSON string keys to integers)

#### 3. Pydantic Models
```python
class Item(BaseModel):
    name: str
    price: float
```
- Strongly typed request bodies
- Automatic validation
- Schema documentation

### Key Benefits

1. **Editor Support**
   - Autocompletion everywhere
   - Type hints and inline documentation
   - Intelligent suggestions for nested models

2. **Data Conversion**
   - Automatic parsing and serialization
   - Type coercion (e.g., string to int)
   - JSON to Python object conversion

3. **Data Validation**
   - Automatic validation of incoming data
   - Type checking
   - Custom validators support

4. **Schema Documentation**
   - Automatic OpenAPI schema generation
   - Interactive API documentation
   - Type information in docs

5. **Automatic Docs**
   - Swagger UI integration
   - ReDoc support
   - Request/response examples

### Important Notes
- JSON only supports string keys; Pydantic handles conversion
- Incoming dictionaries are automatically converted to specified types
- Output is automatically converted to JSON
- All benefits apply regardless of body type used
```

### Instantiate Pydantic Data Models in Python

This Python code illustrates how to create instances of a Pydantic `User` model, demonstrating two common methods. It shows direct instantiation with keyword arguments and dynamic instantiation using dictionary unpacking (`**`), highlighting Pydantic's flexibility in handling data assignment from various sources.

```python
my_user: User = User(id=3, name="John Doe", joined="2018-07-19")

second_user_data = {
    "id": 4,
    "name": "Mary",
    "joined": "2018-11-30"
}

my_second_user: User = User(**second_user_data)
```

### Define Python Types and Pydantic Models for Data Structures

This Python snippet demonstrates the use of standard Python type hints for function parameters and the definition of data models using Pydantic's `BaseModel`. It showcases how FastAPI leverages these type declarations for automatic data validation and serialization, making API development more robust and intuitive.

```python
from datetime import date

from pydantic import BaseModel

# Declare a variable as a str
# and get editor support inside the function
def main(user_id: str):
    return user_id


# A Pydantic model
class User(BaseModel):
    id: int
    name: str
    joined: date
```

### Python: Example Data with Explicitly Set Default Fields

Presents a Python dictionary representing data where fields that typically have default values (like `description` and `tax`) are explicitly provided. This demonstrates that `response_model_exclude_unset` only omits fields that were *not* set, not fields that *have* defaults but are provided in the data.

```python
{
    "name": "Bar",
    "description": "The bartenders",
    "price": 62,
    "tax": 20.2
}
```

### JSON: Example Response with Excluded Unset Fields

Provides a JSON example illustrating the output when `response_model_exclude_unset=True` is applied. Fields like `description`, `tax`, and `tags` are omitted because they were not explicitly set for the 'Foo' item, demonstrating the effect of excluding unset default values.

```json
{
    "name": "Foo",
    "price": 50.2
}
```

### Perform Partial Updates with PATCH in FastAPI using Pydantic

This Python snippet demonstrates how to implement partial updates using an HTTP `PATCH` request in FastAPI. It retrieves existing data, converts the incoming partial data into a dictionary excluding unset fields (`exclude_unset=True`), and then merges this partial data with the stored model using `model_copy(update=...)`. Finally, the updated model is encoded for storage and returned, ensuring only provided fields are modified.

```python
from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.encoders import jsonable_encoder

class Item(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    tax: float = 10.5
    tags: list[str] = []

app = FastAPI()

items = {
    "foo": {"name": "Foo", "price": 50.2, "tags": ["bar", "baz"]},
    "bar": {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2, "tags": ["cat"]},
    "baz": {"name": "Baz", "description": "Loads of stuff", "price": 50.2, "tax": 10.5, "tags": []}
}

@app.patch("/items/{item_id}", response_model=Item)
async def update_item(item_id: str, item: Item):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    stored_item_data = items[item_id]
    stored_item_model = Item(**stored_item_data)
    update_data = item.model_dump(exclude_unset=True)
    updated_item = stored_item_model.model_copy(update=update_data)
    items[item_id] = jsonable_encoder(updated_item)
    return updated_item
```

### PATCH /heroes/{hero_id}

Update a hero with partial data using the HeroUpdate model. This endpoint accepts only the fields sent by the client, excluding default values, and applies them to the existing hero record using SQLModel's sqlmodel_update method.

```APIDOC
## PATCH /heroes/{hero_id}

### Description
Update an existing hero with partial data. Only the fields provided by the client are updated, excluding any default values.

### Method
PATCH

### Endpoint
/heroes/{hero_id}

### Parameters
#### Path Parameters
- **hero_id** (integer) - Required - The unique identifier of the hero to update

### Request Body
- **name** (string) - Optional - The hero's name
- **secret_name** (string) - Optional - The hero's secret identity
- **age** (integer) - Optional - The hero's age

### Request Example
{
  "name": "Updated Hero Name",
  "age": 30
}

### Response
#### Success Response (200)
- **id** (integer) - The hero's unique identifier
- **name** (string) - The updated hero's name
- **secret_name** (string) - The hero's secret identity
- **age** (integer) - The updated hero's age

#### Response Example
{
  "id": 1,
  "name": "Updated Hero Name",
  "secret_name": "Secret Identity",
  "age": 30
}

### Implementation Notes
Use `exclude_unset=True` when converting the request data to a dictionary to ensure only client-provided fields are included. Then use `hero_db.sqlmodel_update(hero_data)` to apply the updates to the database record.
```

### Define HeroUpdate data model for partial updates

Creates a Pydantic model with all fields from HeroCreate but made optional with None defaults. Allows clients to send only the fields they want to update without requiring all fields. All fields are re-declared to include None in their type union.

```python
class HeroUpdate(HeroBase):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None
```

### POST /items/ (Body with Single Example)

This endpoint demonstrates how to provide a single request body example directly within the `Body()` dependency, which is then used in the generated API documentation.

```APIDOC
## POST /items/

### Description
This endpoint accepts an Item object as a request body. A single example for the request body is provided using the `examples` parameter of the `Body()` dependency.

### Method
POST

### Endpoint
/items/

### Parameters
#### Request Body
- **item** (Item) - Required - The item to be created.
    - **name** (string) - The name of the item.
    - **description** (string, optional) - A description of the item.
    - **price** (number) - The price of the item.
    - **tax** (number, optional) - The tax applied to the item.

### Request Example
```json
{
  "name": "Foo",
  "description": "A very nice Item",
  "price": 35.4,
  "tax": 3.2
}
```

### Response
#### Success Response (200)
- **name** (string) - The name of the item.
- **description** (string, optional) - A description of the item.
- **price** (number) - The price of the item.
- **tax** (number, optional) - The tax applied to the item.

#### Response Example
```json
{
  "name": "Foo",
  "description": "A very nice Item",
  "price": 35.4,
  "tax": 3.2
}
```
```

### PATCH /heroes/{hero_id}

Updates an existing hero's details. The `HeroUpdate` data model allows for partial updates, where only the fields provided in the request body will be modified. The API returns the updated public details of the hero.

```APIDOC
## PATCH /heroes/{hero_id}

### Description
Updates an existing hero's details. Fields provided in the request body will be updated, others will remain unchanged. Uses the `HeroUpdate` data model.

### Method
PATCH

### Endpoint
/heroes/{hero_id}

### Parameters
#### Path Parameters
- **hero_id** (integer) - Required - The unique identifier of the hero to update.

#### Query Parameters
(None)

#### Request Body
- **name** (string) - Optional - The hero's new name.
- **age** (integer) - Optional - The hero's new age.
- **secret_name** (string) - Optional - The hero's new secret identity.

### Request Example
{
  "age": 29
}

### Response
#### Success Response (200)
- **id** (integer) - The unique identifier of the hero.
- **name** (string) - The hero's name.
- **age** (integer) - The hero's age.

#### Response Example
{
  "id": 1,
  "name": "Deadpond",
  "age": 29
}
```