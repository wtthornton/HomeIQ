"""The one verified rename path shared by every accept flow in this service.

``sync_name_to_ha`` lived in the accept endpoint's router, which left the batch
auto-accept path (``batch_processor``) to mark suggestions accepted without any
HA contact at all -- the TAP-6233 defect reproduced one endpoint over. Any code
that flips a suggestion to ``accepted`` must call this first and only proceed
on ``True``.
"""

import logging

from homeiq_ha.client import HAClient
from homeiq_ha.client.errors import HAClientError
from homeiq_ha.registry_writer import HARegistryWriter

from ...config import settings

logger = logging.getLogger(__name__)


async def sync_name_to_ha(device_id: str, new_name: str) -> bool:
    """Rename a device in the Home Assistant registry.

    ``device_id`` is the HA device registry id — ``Device.id`` is populated
    straight from ``config/device_registry/list``, so it can be passed through.

    Until TAP-6230 this posted to the ``homeassistant.update_entity`` service
    with a ``name`` field. That service only forces a state refresh: it has no
    ``name`` field, it cannot write the registry, and a device id is not an
    entity id. It answered 200 to every call, so the rename was logged as
    "Synced" and never happened. The gateway reads the value back, which is the
    only check that would have caught it.

    Returns:
        True if the registry now holds ``new_name``.
    """
    if settings.HA_TOKEN is None:
        logger.warning("Cannot sync name to HA: HA_TOKEN is not configured")
        return False

    try:
        async with HAClient(settings.HA_URL, settings.HA_TOKEN) as ha:
            writer = HARegistryWriter(ha.ws, caller="device-intelligence.name_enhancement")
            await writer.set_device_name(device_id, new_name)
    except HAClientError:
        logger.exception("Failed to rename device %s to '%s' in HA", device_id, new_name)
        return False
    logger.info("Renamed device %s to '%s' in HA", device_id, new_name)
    return True
