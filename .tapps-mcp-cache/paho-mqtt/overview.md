### Paho MQTT Python Client Callback Functions Reference

Overview of the callback functions provided by the `paho.mqtt.client` class in the Paho MQTT Python library, detailing their purpose and when they are invoked. This section serves as an API reference for understanding the client's event-driven architecture.

```APIDOC
on_connect(): Called when the client connects to the broker.
  - Parameters: client, userdata, flags, reason_code, properties
  - Purpose: Handle connection success or failure, typically used for initial subscriptions.
on_disconnect(): Called when the connection is closed.
  - Purpose: Handle disconnections, useful for cleanup or retry logic.
on_message(): Called when an MQTT message is received from the broker.
  - Parameters: client, userdata, message
  - Purpose: Process incoming MQTT messages.
on_publish(): Called when an MQTT message was sent to the broker.
  - Parameters: client, userdata, mid, reason_code, properties
  - Invocation:
    - QoS 0: As soon as message is sent over network.
    - QoS 1: When PUBACK is received from broker.
    - QoS 2: When PUBCOMP is received from broker.
on_subscribe(): Called when the SUBACK is received from the broker.
  - Parameters: client, userdata, mid, reason_code_list, properties
  - Purpose: Confirm subscription success or failure.
on_unsubscribe(): Called when the UNSUBACK is received from the broker.
  - Parameters: client, userdata, mid, reason_code_list, properties
  - Purpose: Confirm unsubscription.
on_log(): Called when the library logs a message.
on_socket_open(): Callback for external loop support.
on_socket_close(): Callback for external loop support.
on_socket_register_write(): Callback for external loop support.
on_socket_unregister_write(): Callback for external loop support.
```

### Paho MQTT Python: One-Shot Publish Helper Functions

This section introduces helper functions for straightforward, one-shot message publishing. These functions are designed for scenarios where single or multiple messages need to be published to a broker, followed by a clean disconnect, without requiring a persistent client loop.

```APIDOC
One-Shot Publish Functions:
- single(): Publishes a single message to a broker, then disconnects cleanly.
- multiple(): Publishes multiple messages to a broker, then disconnects cleanly.

Note: Both functions support MQTT v5.0 but do not currently allow setting properties on connection or when sending messages.
```

### Publish Documentation to Project Website

Builds the latest documentation locally and outlines the process to copy the generated HTML files to the designated repository for publishing on the paho.mqtt.python project website.

```bash
make clean html
```

### Git Commit Sign-off Format Example

This snippet illustrates the required format for signing off Git commits. Contributors must include this line at the bottom of their commit messages to comply with the Eclipse Foundation IP policy, ensuring proper attribution and legal compliance for their contributions.

```Git
Signed-off-by: John Smith <johnsmith@nowhere.com>
```

### Fix 'protocol' Not Used in publish.single()

The `publish.single()` helper function now correctly utilizes the `protocol` argument when specified, ensuring the desired MQTT protocol version is used for single message publications.

```Python
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

publish.single("topic", "payload", hostname="localhost", protocol=mqtt.MQTTv311)
```

### Add SSLContext and SNI Support

The library now includes support for Python's `SSLContext` object, enabling advanced TLS configurations such as Server Name Indication (SNI).

```Python
import ssl
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
client.tls_set_context(context)
```

### Publish Multiple MQTT Messages with Paho Python

Shows how to publish multiple messages to an MQTT broker in a single operation using `paho.mqtt.publish.multiple`, then disconnect cleanly. This example also demonstrates specifying MQTT Protocol Version 5.

```python
from paho.mqtt.enums import MQTTProtocolVersion
import paho.mqtt.publish as publish

msgs = [{'topic':"paho/test/topic", 'payload':"multiple 1"},
    ("paho/test/topic", "multiple 2", 0, False)]
publish.multiple(msgs, hostname="mqtt.eclipseprojects.io", protocol=MQTTProtocolVersion.MQTTv5)
```

### Publish Single MQTT Message with Paho Python

Demonstrates how to publish a single message to an MQTT broker using the `paho.mqtt.publish.single` helper function. It connects, publishes the message, and then disconnects.

```python
import paho.mqtt.publish as publish

publish.single("paho/test/topic", "payload", hostname="mqtt.eclipseprojects.io")
```

### Upload Distribution Archives to PyPI

Uploads the final, built distribution archives (wheel and sdist) from the 'dist/' directory to the official Python Package Index (PyPI), making the new version publicly available.

```bash
python -m twine upload dist/*
```

### Introduce `paho.mqtt.subscribe` Module

A new `paho.mqtt.subscribe` module has been added, offering helper functions like `simple()` and `callback()` to simplify common MQTT subscription patterns.

```Python
import paho.mqtt.subscribe as subscribe
import paho.mqtt.client as mqtt

# Using simple helper
msg = subscribe.simple("test/topic", hostname="localhost")
print(f"Received: {msg.payload.decode()}")

# Using callback helper
def on_message_print(client, userdata, message):
    print(f"Topic: {message.topic}, Payload: {message.payload.decode()}")

subscribe.callback(on_message_print, "test/#", hostname="localhost")
```