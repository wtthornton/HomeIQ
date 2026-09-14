"""Presence sensor-class taxonomy — the `SensorClass` vocabulary and priors.

Fusion needs to know what kind of evidence each entity produces before it can
weight it. Every class below declares a dominant failure mode, whether its
evidence arrives continuously or over a rate-limited transport, and whether
its sensor can detect a person who has stopped moving. Classification reads
only device and integration metadata (HA domain, device_class, the device
registry's manufacturer/model, the integration platform) — never an
entity_id or friendly name. See `.claude/rules/friendly-names.md`.

Every `ReliabilityPrior` here is an explicit provisional placeholder, marked
`PriorStatus.PROVISIONAL` and machine-checkable via `require_fitted`. Real
priors are seeded from recorded occupancy history (TAP-7586, blocked at the
time this module was written) and must never be guessed from intuition —
that is the exact failure TAP-7590 exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


class SensorClass(Enum):
    """Every declared presence-evidence class."""

    PIR = "pir"
    MMWAVE_PRESENCE = "mmwave_presence"
    MMWAVE_DOPPLER = "mmwave_doppler"
    CSI = "csi"
    OFFGRID_RADAR = "offgrid_radar"
    DEVICE_TRACKER = "device_tracker"
    DOOR_CONTACT = "door_contact"
    POWER_DRAW = "power_draw"
    MEDIA_STATE = "media_state"
    UNKNOWN = "unknown"


class Transport(Enum):
    """How a class's evidence reaches fusion."""

    CONTINUOUS = "continuous"
    RATE_LIMITED = "rate_limited"


class PriorStatus(Enum):
    """Whether a `ReliabilityPrior` was fit from data or is a placeholder."""

    PROVISIONAL = "provisional"
    FITTED = "fitted"


class UnfittedPriorError(RuntimeError):
    """A consumer tried to use a provisional prior as if it were fitted."""


#: Uninformative midpoint used for every provisional prior. It is not a
#: per-class reliability estimate — fitting one from intuition is the exact
#: failure this module exists to prevent — it is the same fixed placeholder
#: for every class, which is also why `unknown` legitimately ties for
#: weakest: nothing here yet outranks anything else.
PROVISIONAL_PRIOR_VALUE = 0.5

PROVISIONAL_PRIOR_SOURCE = (
    "TAP-7590 placeholder — blocked on TAP-7586 (room_occupancy history does "
    "not exist yet); not fitted to data, not fitted to intuition"
)


@dataclass(frozen=True)
class ReliabilityPrior:
    """A class's reliability weight for fusion, and whether it is trustworthy.

    `status` is the machine-readable half of the contract: a provisional
    prior must never be consumed as if it were fitted. Call `require_fitted`
    at the point of use rather than reading `.value` directly.
    """

    value: float
    status: PriorStatus
    source: str

    @property
    def is_fitted(self) -> bool:
        return self.status is PriorStatus.FITTED


def require_fitted(prior: ReliabilityPrior) -> ReliabilityPrior:
    """Return `prior` if fitted, else raise.

    Fusion arithmetic must call this before consuming a prior's `.value` as a
    calibrated weight. It exists so a provisional placeholder cannot silently
    pass for a fitted number.
    """
    if not prior.is_fitted:
        raise UnfittedPriorError(
            f"prior status is {prior.status.value!r}, not fitted (source: "
            f"{prior.source}); it may not be consumed as a calibrated weight"
        )
    return prior


def _provisional_prior() -> ReliabilityPrior:
    return ReliabilityPrior(
        value=PROVISIONAL_PRIOR_VALUE,
        status=PriorStatus.PROVISIONAL,
        source=PROVISIONAL_PRIOR_SOURCE,
    )


@dataclass(frozen=True)
class SensorClassProfile:
    """The declared physics of one `SensorClass`."""

    sensor_class: SensorClass
    dominant_failure_mode: str
    transport: Transport
    freshness_bound_seconds: int | None
    detects_stationary_person: bool
    prior: ReliabilityPrior

    def __post_init__(self) -> None:
        if self.transport is Transport.RATE_LIMITED:
            if not self.freshness_bound_seconds or self.freshness_bound_seconds <= 0:
                raise ValueError(
                    f"{self.sensor_class}: rate-limited transport requires its "
                    "own positive freshness_bound_seconds"
                )
        elif self.freshness_bound_seconds is not None:
            raise ValueError(
                f"{self.sensor_class}: continuous transport must not carry a "
                "freshness bound — that field is for rate-limited classes only, "
                "so a continuous class can never silently inherit one"
            )


SENSOR_CLASS_PROFILES: dict[SensorClass, SensorClassProfile] = {
    SensorClass.PIR: SensorClassProfile(
        sensor_class=SensorClass.PIR,
        dominant_failure_mode="false_clear_on_stillness",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.MMWAVE_PRESENCE: SensorClassProfile(
        sensor_class=SensorClass.MMWAVE_PRESENCE,
        dominant_failure_mode="false_hold_from_ambient_motion",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=True,
        prior=_provisional_prior(),
    ),
    SensorClass.MMWAVE_DOPPLER: SensorClassProfile(
        sensor_class=SensorClass.MMWAVE_DOPPLER,
        dominant_failure_mode="false_clear_on_stillness",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.CSI: SensorClassProfile(
        sensor_class=SensorClass.CSI,
        dominant_failure_mode="motion_only_no_count_or_identity",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.OFFGRID_RADAR: SensorClassProfile(
        sensor_class=SensorClass.OFFGRID_RADAR,
        dominant_failure_mode="silent_link_failure_between_wakes",
        transport=Transport.RATE_LIMITED,
        freshness_bound_seconds=900,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.DEVICE_TRACKER: SensorClassProfile(
        sensor_class=SensorClass.DEVICE_TRACKER,
        dominant_failure_mode="building_not_room_granularity",
        transport=Transport.RATE_LIMITED,
        freshness_bound_seconds=120,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.DOOR_CONTACT: SensorClassProfile(
        sensor_class=SensorClass.DOOR_CONTACT,
        dominant_failure_mode="event_only_no_continuous_occupancy_signal",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.POWER_DRAW: SensorClassProfile(
        sensor_class=SensorClass.POWER_DRAW,
        dominant_failure_mode="device_active_without_person_present",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.MEDIA_STATE: SensorClassProfile(
        sensor_class=SensorClass.MEDIA_STATE,
        dominant_failure_mode="playback_state_not_presence",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
    SensorClass.UNKNOWN: SensorClassProfile(
        sensor_class=SensorClass.UNKNOWN,
        dominant_failure_mode="unclassified_no_declared_failure_mode",
        transport=Transport.CONTINUOUS,
        freshness_bound_seconds=None,
        detects_stationary_person=False,
        prior=_provisional_prior(),
    ),
}


#: Classes whose entities are candidate presence evidence — used by callers
#: (e.g. the automation agent's binary-sensor context) that previously
#: decided this with a keyword list.
PRESENCE_RELEVANT_SENSOR_CLASSES: frozenset[SensorClass] = frozenset(
    {
        SensorClass.PIR,
        SensorClass.MMWAVE_PRESENCE,
        SensorClass.MMWAVE_DOPPLER,
        SensorClass.CSI,
        SensorClass.OFFGRID_RADAR,
    }
)


def fails_on_stillness(sensor_class: SensorClass) -> bool:
    """Whether this class's sensor cannot detect a stationary person.

    Downstream decay logic must call this rather than compare class names —
    the flag is the contract, not the label.
    """
    return not SENSOR_CLASS_PROFILES[sensor_class].detects_stationary_person


# Manufacturer/model signatures for modules that plain domain + device_class
# cannot disambiguate. Keyed on (manufacturer, model-substring); an empty
# manufacturer means "match on model regardless of manufacturer" — Doppler-only
# radar modules such as the RD-03D are resold under many house brands, so
# manufacturer is not a reliable discriminator for that family.
_MMWAVE_MODULE_SIGNATURES: tuple[tuple[str, str, SensorClass], ...] = (
    # "lumi.sensor_occupy.agl8" is the Aqara FP1E's raw Zigbee model string.
    # See libs/homeiq-ha/src/homeiq_ha/agent/quirks/aqara_fp1e.py.
    ("aqara", "agl8", SensorClass.MMWAVE_PRESENCE),
    # The ZHA quirk's friendly_name rewrite reports `model` as
    # "Presence Sensor FP1E" instead, once applied.
    ("aqara", "fp1e", SensorClass.MMWAVE_PRESENCE),
    ("", "rd-03d", SensorClass.MMWAVE_DOPPLER),
)


def classify_sensor(
    *,
    domain: str,
    device_class: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    platform: str | None = None,
) -> SensorClass:
    """Classify a `SensorClass` from device and integration metadata.

    Every argument is platform-assigned (HA domain, device_class, the device
    registry's manufacturer/model, the integration platform) and survives a
    rename. There is deliberately no `entity_id` or friendly-name parameter,
    so a caller cannot pass one by accident. See
    `.claude/rules/friendly-names.md`.
    """
    manufacturer_l = (manufacturer or "").strip().lower()
    model_l = (model or "").strip().lower()
    device_class_l = (device_class or "").strip().lower()
    platform_l = (platform or "").strip().lower()
    domain_l = (domain or "").strip().lower()

    for known_manufacturer, model_needle, sensor_class in _MMWAVE_MODULE_SIGNATURES:
        if model_needle in model_l and (
            not known_manufacturer or known_manufacturer == manufacturer_l
        ):
            return sensor_class

    if platform_l == "offgrid_radar" or device_class_l == "offgrid_motion":
        return SensorClass.OFFGRID_RADAR
    if platform_l == "wifi_csi" or device_class_l == "csi_motion":
        return SensorClass.CSI
    if domain_l == "device_tracker":
        return SensorClass.DEVICE_TRACKER
    if device_class_l in ("door", "window", "garage_door", "opening"):
        return SensorClass.DOOR_CONTACT
    if device_class_l in ("power", "current", "energy"):
        return SensorClass.POWER_DRAW
    if domain_l == "media_player":
        return SensorClass.MEDIA_STATE
    if device_class_l in ("motion", "occupancy", "presence") and domain_l == "binary_sensor":
        return SensorClass.PIR

    return SensorClass.UNKNOWN


def classify_from_records(
    entity: Mapping[str, Any], device: Mapping[str, Any] | None = None
) -> SensorClass:
    """Classify from an HA/data-api entity record plus its device record.

    Deliberately never reads `entity_id`, `friendly_name` or `name` — those
    are renameable presentation fields, not identity.
    """
    device = device or {}
    attributes = entity.get("attributes") or {}
    device_class = entity.get("device_class") or attributes.get("device_class")
    return classify_sensor(
        domain=entity.get("domain") or "",
        device_class=device_class,
        manufacturer=device.get("manufacturer"),
        model=device.get("model"),
        platform=entity.get("platform") or device.get("platform"),
    )
