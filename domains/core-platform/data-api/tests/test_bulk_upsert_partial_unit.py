"""Partial-patch semantics of /internal/entities/bulk_upsert (_apply_entity_patch).

Regression: a partial payload (e.g. only aliases) must not reset absent fields
to their defaults — labels were being wiped by alias-only patches.
"""

from src.devices_endpoints import _apply_entity_patch
from src.models import Entity


def make_entity() -> Entity:
    return Entity(
        entity_id="light.office",
        domain="light",
        platform="wled",
        friendly_name="Office",
        labels=["role:primary-light", "area:office"],
        aliases=["Office light"],
    )


def test_alias_only_patch_preserves_labels():
    entity = make_entity()
    _apply_entity_patch(entity, {"entity_id": "light.office", "aliases": ["Office LED strip"]}, set())
    assert entity.aliases == ["Office LED strip"]
    assert entity.labels == ["role:primary-light", "area:office"]
    assert entity.platform == "wled"


def test_label_only_patch_preserves_aliases():
    entity = make_entity()
    _apply_entity_patch(entity, {"entity_id": "light.office", "labels": ["role:presence"]}, set())
    assert entity.labels == ["role:presence"]
    assert entity.aliases == ["Office light"]


def test_device_id_validated_against_known_devices():
    entity = make_entity()
    _apply_entity_patch(entity, {"device_id": "unknown-device"}, {"known-device"})
    assert entity.device_id is None
    _apply_entity_patch(entity, {"device_id": "known-device"}, {"known-device"})
    assert entity.device_id == "known-device"


def test_name_patch_recomputes_friendly_name():
    entity = make_entity()
    _apply_entity_patch(entity, {"name_by_user": "Desk strip"}, set())
    assert entity.friendly_name == "Desk strip"


def test_disabled_by_maps_to_disabled_flag():
    entity = make_entity()
    _apply_entity_patch(entity, {"disabled_by": "user"}, set())
    assert entity.disabled is True
    _apply_entity_patch(entity, {"disabled_by": None}, set())
    assert entity.disabled is False
