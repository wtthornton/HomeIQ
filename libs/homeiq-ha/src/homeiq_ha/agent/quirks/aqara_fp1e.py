"""ZHA quirk giving the Aqara FP1E (``lumi.sensor_occupy.agl8``) an occupancy entity.

Deployed to ``/config/custom_zha_quirks`` by
:class:`homeiq_ha.agent.zha_quirks.AqaraFP1EQuirkRecipe`; this file is the
source of truth and is never edited on the host.

Why it is needed
----------------
``zha-quirks`` 2.2.0 ships ``zhaquirks/xiaomi/aqara/motion_agl1.py``, whose own
docstring reads "Aqara manufacturer cluster for the presence sensor FP1E" — but
it registers the model string ``lumi.sensor_occupy.agl1``. The units on this
mesh report ``lumi.sensor_occupy.agl8``, so nothing matches them, ``zha`` leaves
``quirk_applied = False``, and the raw ``0xFCC0`` cluster is exposed with no
attribute definitions and therefore no entity.

Attribute mapping and its evidence
----------------------------------
``0xFCC0`` attribute ``0x0142`` is occupancy, ``enum8``, ``0x00`` unoccupied /
``0x01`` occupied. Two independent sources:

1. **Upstream source.** ``zha-quirks`` 2.2.0 —
   ``zhaquirks/xiaomi/aqara/motion_agl1.py``, ``OppleCluster.AttributeDefs``::

       occupancy = ZCLAttributeDef(id=0x0142, type=AqaraOccupancy,
                                   zcl_type=DataTypeId.uint8, access="rp", ...)
       class AqaraOccupancy(types.enum8): Unoccupied = 0x00; Occupied = 0x01

   That is the exact version Home Assistant 2026.8.2 pins
   (``homeassistant/components/zha/manifest.json``: ``zha-quirks==2.2.0``).

2. **Live wire evidence.** zigpy's own attribute cache on the target instance
   (``/config/zigbee.db``, ``attributes_cache_v15``) read 2026-08-18: of the
   ~30 ``0xFCC0`` attributes cached for these two units, every one carries the
   frozen timestamp of the 2026-08-12 interview *except* ``0x0142`` and
   ``0x014D`` — the only two the device pushes unsolicited. ``0x0142`` held
   ``0`` on the unit reporting no presence and ``1`` on the other, matching the
   enum above. ``0x014D`` is left unmapped: it also updates live but no source
   defines it for this model, and guessing it would be exactly the invention
   this quirk exists to avoid.

Only occupancy is mapped. ``motion`` (``0x0160``), ``motion_distance``
(``0x015F``) and ``approach_distance`` (``0x015B``) exist on the ``agl1``
variant but appear nowhere in this hardware's live cache, so they are not
claimed here.

Shape
-----
The mirror-into-a-standard-cluster shape is upstream's, not an invention: the
manufacturer cluster is ``replaces``-d so ``0x0142`` gains a definition, and
each report is copied into a local :class:`OccupancySensing` cluster. ``zha``
builds its native ``binary_sensor`` with ``device_class: occupancy`` from that
standard cluster — no custom entity platform is involved.

Should upstream ever register ``lumi.sensor_occupy.agl8`` itself, delete this
file and the recipe rather than carrying two registrations for one signature.
"""

from __future__ import annotations

from typing import Any

# QuirkBuilder comes from ``zhaquirks.builder``, the canonical v2 authoring
# import in zha-quirks 2.2.0. ``zigpy.quirks.v2`` still resolves, but its own
# docstring calls itself a backwards-compatibility shim that forwards here.
from zhaquirks import LocalDataCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster
from zigpy import types
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef


class AqaraOccupancy(types.enum8):
    """Values of ``0xFCC0`` attribute ``0x0142``."""

    Unoccupied = 0x00
    Occupied = 0x01


class OccupancySensingLocal(LocalDataCluster, OccupancySensing):
    """Standard occupancy cluster the device does not implement, fed locally.

    ``LocalDataCluster`` never touches the radio: it serves the cached value
    written by :meth:`FP1EManufacturerCluster._update_attribute`, which is what
    lets a device that only speaks ``0xFCC0`` present a standard entity.
    """

    _VALID_ATTRIBUTES = {OccupancySensing.AttributeDefs.occupancy.id}


class FP1EManufacturerCluster(XiaomiAqaraE1Cluster):
    """Aqara's ``0xFCC0`` cluster, with this model's occupancy attribute defined."""

    class AttributeDefs(BaseAttributeDefs):
        """Only the attribute this quirk has evidence for."""

        # access="rp": the device reports it unsolicited and it is readable.
        # manufacturer_code=None because XiaomiAqaraE1Cluster already carries
        # the 0x115F manufacturer code for the whole cluster.
        occupancy = ZCLAttributeDef(
            id=0x0142,
            type=AqaraOccupancy,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=None,
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Mirror every occupancy report into the standard cluster."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.occupancy.id:
            self.endpoint.occupancy.update_attribute(
                OccupancySensing.AttributeDefs.occupancy.id,
                OccupancySensing.Occupancy.Occupied
                if value == AqaraOccupancy.Occupied
                else OccupancySensing.Occupancy.Unoccupied,
            )


# Both spellings of the manufacturer string, because the registry matches it
# exactly: the live unit's Basic cluster (0x0000 attribute 0x0004) reads
# "Aqara", while upstream's agl1 entry for the same family is registered as
# "aqara". Verified locally against zha-quirks 2.2.0 — registering only one
# spelling leaves the other unmatched.
(
    QuirkBuilder("Aqara", "lumi.sensor_occupy.agl8")
    .applies_to("aqara", "lumi.sensor_occupy.agl8")
    .friendly_name(manufacturer="Aqara", model="Presence Sensor FP1E")
    .adds(OccupancySensingLocal)
    .replaces(FP1EManufacturerCluster)
    .add_to_registry()
)
