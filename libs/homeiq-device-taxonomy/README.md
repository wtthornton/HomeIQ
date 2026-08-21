# homeiq-device-taxonomy

The single source of HomeIQ's `device_type` vocabulary and the matcher that
assigns one from entity domains.

## Why it is a library

`data-api` used to reach into `device-context-classifier/src/` with a
`sys.path.append`. The relative path resolved to a directory that does not
exist, and the `ImportError` was caught and replaced with a stub returning
`None`. Every device with entities therefore classified as `None`, and the only
path that ever assigned a `device_type` was a keyword scan over the device's
friendly name — which the project forbids, because a rename changes the answer.

A declared dependency breaks the build when it goes missing. A filesystem
reach-around does not.

## Contract

- `match_device_pattern(entity_domains, attribute_keys) -> tuple[str | None, float]`
  returns `(device_type, confidence)`. **It returns a tuple** — assigning its
  result straight to a `device_type` variable is the bug that TAP-6392 fixed.
- `get_device_category(device_type) -> str | None`.
- `device_type_vocabulary() -> frozenset[str]` — every legal `device_type`.
  Use it to validate before writing the column.

No function here reads a device name, an `entity_id` slug, or an area label.
