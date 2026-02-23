### HTTP Exception Hierarchy Overview

Provides a visual representation of the exception hierarchy for aiohttp web exceptions. This helps understand the relationships between different HTTP status code exceptions.

```python
Exception
  HTTPException
    HTTPSuccessful
      * 200 - HTTPOk
      * 201 - HTTPCreated
      * 202 - HTTPAccepted
      * 203 - HTTPNonAuthoritativeInformation
      * 204 - HTTPNoContent
      * 205 - HTTPResetContent
      * 206 - HTTPPartialContent
    HTTPRedirection
      * 304 - HTTPNotModified
      HTTPMove
        * 300 - HTTPMultipleChoices
        * 301 - HTTPMovedPermanently
        * 302 - HTTPFound
        * 303 - HTTPSeeOther
        * 305 - HTTPUseProxy
        * 307 - HTTPTemporaryRedirect
        * 308 - HTTPPermanentRedirect
    HTTPError
      HTTPClientError
        * 400 - HTTPBadRequest
        * 401 - HTTPUnauthorized
        * 402 - HTTPPaymentRequired
        * 403 - HTTPForbidden
        * 404 - HTTPNotFound
        * 405 - HTTPMethodNotAllowed
        * 406 - HTTPNotAcceptable
        * 407 - HTTPProxyAuthenticationRequired
        * 408 - HTTPRequestTimeout
        * 409 - HTTPConflict
        * 410 - HTTPGone
        * 411 - HTTPLengthRequired
        * 412 - HTTPPreconditionFailed
        * 413 - HTTPRequestEntityTooLarge
        * 414 - HTTPRequestURITooLong
        * 415 - HTTPUnsupportedMediaType
        * 416 - HTTPRequestRangeNotSatisfiable
        * 417 - HTTPExpectationFailed
        * 421 - HTTPMisdirectedRequest
        * 422 - HTTPUnprocessableEntity
        * 424 - HTTPFailedDependency
        * 426 - HTTPUpgradeRequired
        * 428 - HTTPPreconditionRequired
        * 429 - HTTPTooManyRequests
        * 431 - HTTPRequestHeaderFieldsTooLarge
        * 451 - HTTPUnavailableForLegalReasons
      HTTPServerError
        * 500 - HTTPInternalServerError
        * 501 - HTTPNotImplemented
        * 502 - HTTPBadGateway
        * 503 - HTTPServiceUnavailable
        * 504 - HTTPGatewayTimeout
        * 505 - HTTPVersionNotSupported
        * 506 - HTTPVariantAlsoNegotiates
        * 507 - HTTPInsufficientStorage
        * 510 - HTTPNotExtended
        * 511 - HTTPNetworkAuthenticationRequired
```

### Web Server Exceptions Overview

Overview of aiohttp.web exceptions, which are subclasses of HTTPException and correspond to HTTP status codes.

```APIDOC
## Web Server Exceptions Overview

[`aiohttp.web`](web.md#module-aiohttp.web) provides a set of exceptions for each HTTP status code. These exceptions are subclasses of [`HTTPException`](#aiohttp.web.HTTPException).

**Usage Example:**
```python3
async def handler(request):
    raise aiohttp.web.HTTPFound('/redirect')
```

HTTP exceptions are categorized based on RFC 2068:
- 100-300: Not errors
- 400s: Client errors
- 500s: Server errors
```

### aiohttp.Connection Class Overview

The Connection class encapsulates a single connection within an aiohttp connector. It should not be instantiated directly by end-users but obtained via BaseConnector.connect(). It provides methods to close or release the connection.

```python
from aiohttp import Connection

# This class is typically managed internally by aiohttp connectors.
# Direct instantiation is not recommended for end-users.

# Example of accessing properties (conceptual):
# async def use_connection(connector):
#     conn: Connection = await connector.connect()
#     print(f"Is connection closed? {conn.closed}")
#     print(f"Event loop: {conn.loop}")
#     # conn.close() or conn.release()
```

### View and Static Routes

Defines routes for class-based views and serving static files.

```APIDOC
## ANY /view

### Description
Registers a route for handling any HTTP method against a class-based view.

### Method
ANY

### Endpoint
/view

### Parameters
#### Path Parameters
- **path** (str) - Required - The URL path for the route.
- **handler** (type) - Required - The class-based view.
- **name** (str, optional) - Name for the route.
- **expect_handler** (callable, optional) - Handler for expectations.

### Request Example
```python
from aiohttp import web

class MyView(web.View):
    async def get(self):
        return web.Response(text="GET request")
    async def post(self):
        return web.Response(text="POST request")

app.router.add_view('/my_view', MyView)
```

### Response
#### Success Response (200)
- **RouteDef** - Represents the defined route.

## Static Files /prefix

### Description
Registers a route for serving static files from a specified directory.

### Method
GET, HEAD

### Endpoint
/prefix

### Parameters
#### Path Parameters
- **prefix** (str) - Required - The URL prefix for static files.
- **path** (str) - Required - The directory path containing static files.
- **name** (str, optional) - Name for the route.
- **expect_handler** (callable, optional) - Handler for expectations.
- **chunk_size** (int, optional) - Size of chunks for streaming files.
- **show_index** (bool, optional) - Whether to show directory index.
- **follow_symlinks** (bool, optional) - Whether to follow symbolic links.
- **append_version** (bool, optional) - Whether to append version to static file URLs.

### Request Example
```python
from aiohttp import web

app.router.add_static('/static', '/path/to/static/files')
```

### Response
#### Success Response (200)
- **StaticDef** - Represents the defined static route.
```

### Basic API Usage

An overview of the basic API for making simple HTTP requests in aiohttp, suitable for scenarios without keep-alive, cookies, or complex SSL configurations.

```APIDOC
## Basic API

### Description
Provides simple coroutines for making HTTP requests without the complexities of keep-alive, cookies, or advanced connection management.

### Usage
While `ClientSession` is recommended for most use cases, the basic API is convenient for straightforward HTTP requests where advanced features are not required.
```

### Request Body Stream and Existence

Properties to check if the request body exists and can be read, and to access the request body as a stream.

```APIDOC
## POST /upload

### Description
Handles requests with a body, allowing access to the stream and checking for body existence.

### Method
POST

### Endpoint
/upload

### Parameters
#### Request Body
- **file** (StreamReader) - The input stream for reading the request's BODY.

### Request Example
```json
{
  "file": "<stream data>"
}
```

### Response
#### Success Response (200)
- **body_exists** (bool) - `True` if the request has an HTTP BODY, `False` otherwise.
- **can_read_body** (bool) - `True` if the request's HTTP BODY can be read, `False` otherwise.
- **content** (StreamReader) - An instance of `StreamReader` for reading the request's BODY.

#### Response Example
```json
{
  "body_exists": true,
  "can_read_body": true,
  "content": "<stream object>"
}
```
```

### aiohttp.web.Application Class

The Application class serves as the core of an aiohttp web server. It manages routing, request handling, and application-wide data sharing. It is also a dictionary-like object for storing arbitrary properties accessible from request handlers.

```APIDOC
## aiohttp.web.Application

### Description
Represents a web server application in aiohttp. It holds the router, middlewares, and allows for global data sharing.

### Class Signature
`aiohttp.web.Application(*, logger=<default>, middlewares=(), handler_args=None, client_max_size=1024**2, debug=...)`

### Parameters
#### Constructor Parameters
- **logger** (`logging.Logger`) - Instance for storing application logs. Defaults to `logging.getLogger("aiohttp.web")`.
- **middlewares** (`list`) - A list of middleware factories. See [Middlewares](web_advanced.md#aiohttp-web-middlewares) for details.
- **handler_args** (`dict`) - Dictionary-like object to override keyword arguments of the `AppRunner` constructor.
- **client_max_size** (`int`) - The maximum size of a client's request in bytes. Defaults to 1MB. Raises `HTTPRequestEntityTooLarge` if exceeded.
- **debug** (`bool`) - Switches debug mode. Deprecated since version 3.5; use asyncio Debug Mode instead.

### Properties
#### router
Read-only property that returns the application's router instance.

#### logger
Read-only property returning the `logging.Logger` instance for the application.

#### debug
Boolean value indicating whether debug mode is enabled. Deprecated since version 3.5.

#### on_response_prepare
A `Signal` fired near the end of `StreamResponse.prepare()` with `request` and `response` parameters. Useful for modifying headers before sending them to the client.
Signal handler signature: `async def on_prepare(request, response): ...`

#### on_startup
A `Signal` fired on application start-up. Subscribers can use this to run background tasks.
Signal handler signature: `async def on_startup(app): ...`

#### on_shutdown
A `Signal` fired on application shutdown. Subscribers can use this for gracefully closing connections.
Signal handler signature: `async def on_shutdown(app): ...`

### Usage Example
```python
from aiohttp import web

async def handle(request):
    return web.Response(text="Hello, world")

app = web.Application()
app.router.add_get('/', handle)

# To run the application:
# web.run_app(app)
```

### Data Sharing Example
```python
from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.util import AppKey

database = AppKey("database", AsyncEngine)

async def init_db():
    db_url = "sqlite+aiosqlite:///:memory:"
    engine = await create_async_engine(db_url)
    return engine

async def handler(request):
    engine = request.app[database]
    async with engine.begin() as conn:
        await conn.execute("SELECT 1")
    return web.Response(text="Database operation successful")

async def startup_handler(app):
    app[database] = await init_db()

async def shutdown_handler(app):
    await app[database].dispose()

app = web.Application()
app.on_startup.append(startup_handler)
app.on_shutdown.append(shutdown_handler)
app.router.add_get('/db_op', handler)

# web.run_app(app)
```
```

### aiohttp.web.AppKey Class

Provides a type-safe alternative to string keys for aiohttp.web.Application, preventing name clashes and improving type checking.

```APIDOC
## Class: aiohttp.web.AppKey

### Description
This class should be used for the keys in `aiohttp.web.Application`. They provide a type-safe alternative to str keys when checking your code with a type checker (e.g. mypy). They also avoid name clashes with keys from different libraries etc.

### Parameters
* **name** (str) - A name to help with debugging. This should be the same as the variable name (much like how `typing.TypeVar` is used).
* **t** (type) - The type that should be used for the value in the dict (e.g. str, Iterator[int] etc.)
```

### StreamReader Class Overview

The StreamReader class is used by aiohttp for reading data from incoming streams. Users should access stream content through `aiohttp.web.BaseRequest.content` or `aiohttp.ClientResponse.content` rather than instantiating StreamReader directly.

```APIDOC
## StreamReader Class

### Description
The reader from incoming stream. Users should never instantiate streams manually but use existing `aiohttp.web.BaseRequest.content` and `aiohttp.ClientResponse.content` properties for accessing raw BODY data.

### Methods

- **`read(n=-1)`**: Asynchronously reads up to `n` bytes. If `n` is -1, reads until EOF.
- **`readany()`**: Asynchronously reads the next available data portion from the stream.
- **`readexactly(n)`**: Asynchronously reads exactly `n` bytes, raising `asyncio.IncompleteReadError` if EOF is reached prematurely.
- **`readline()`**: Asynchronously reads a single line ending with `\n`.
- **`readuntil(separator='\n')`**: Asynchronously reads until the specified separator is found.
- **`readchunk()`**: Asynchronously reads a chunk of data as received by the server, returning a tuple of (data, end_of_HTTP_chunk).

### Properties

- **`total_raw_bytes`** (int): Readonly property indicating the total number of raw bytes downloaded.

### Asynchronous Iteration

StreamReader supports asynchronous iteration:
- **`iter_chunked(n)`**: Asynchronously iterates over data chunks with a maximum size limit `n`.
- **`iter_any()`**: Asynchronously iterates over data chunks in the order they are received by the stream.
```

### aiohttp Client API - Middleware Cookbook

Practical examples and best practices for implementing client middleware in aiohttp.

```APIDOC
## aiohttp Client Middleware Cookbook

### Description
This cookbook provides practical recipes and examples for creating and utilizing client middleware in aiohttp. It demonstrates common middleware patterns and offers guidance on best practices for effective middleware implementation.

### Key Topics

*   **Simple Retry Middleware**: Implementing middleware to automatically retry failed requests.
*   **Logging to an external service**: Creating middleware to log request/response details to an external logging system.
*   **Token Refresh Middleware**: Developing middleware to handle token expiration and refresh mechanisms.
*   **Server-side Request Forgery Protection**: Implementing middleware to mitigate SSRF vulnerabilities.
*   **Best Practices**: Guidelines for writing efficient and maintainable middleware.
*   **See Also**: Links to related documentation and resources.
```