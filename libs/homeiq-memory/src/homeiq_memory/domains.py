"""Domain taxonomy for Home Assistant entity classification.

Maps entity_id prefixes to semantic domains for trust score calculation
and domain-filtered queries.
"""

# Canonical domain names — these are the HA entity prefixes that map to semantic domains
DOMAIN_TAXONOMY: dict[str, str] = {
    "light": "lighting",
    "switch": "lighting",  # switches often control lights
    "climate": "climate",
    "fan": "climate",
    "humidifier": "climate",
    "lock": "security",
    "alarm_control_panel": "security",
    "binary_sensor": "security",  # many are door/window/motion
    "cover": "covers",
    "media_player": "media",
    "remote": "media",
    "water_heater": "water",
    "sensor": "energy",  # many sensors are energy-related
    "automation": "automation",
    "script": "automation",
    "scene": "automation",
    "input_boolean": "automation",
    "input_number": "automation",
    "input_select": "automation",
    "camera": "security",
    "vacuum": "cleaning",
    "device_tracker": "presence",
    "person": "presence",
}

# All valid domain categories
VALID_DOMAINS = sorted(set(DOMAIN_TAXONOMY.values()))


def classify_domain(entity_ids: list[str] | None) -> str | None:
    """Classify domain from entity IDs by prefix parsing.

    Extracts the HA entity prefix (e.g., 'light' from 'light.living_room')
    and maps to a semantic domain.

    Args:
        entity_ids: List of Home Assistant entity IDs.

    Returns:
        Primary domain string, or None if no entity_ids or no match.
    """
    if not entity_ids:
        return None

    domain_counts: dict[str, int] = {}
    for entity_id in entity_ids:
        prefix = entity_id.split(".", 1)[0] if "." in entity_id else ""
        domain = DOMAIN_TAXONOMY.get(prefix)
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

    if not domain_counts:
        return None

    # Return most frequent domain
    return max(domain_counts, key=domain_counts.get)  # type: ignore[arg-type]


def classify_domains(entity_ids: list[str] | None) -> list[str]:
    """Classify all domains from entity IDs (for multi-domain memories).

    Args:
        entity_ids: List of Home Assistant entity IDs.

    Returns:
        Sorted list of unique domain strings found.
    """
    if not entity_ids:
        return []

    domains = set()
    for entity_id in entity_ids:
        prefix = entity_id.split(".", 1)[0] if "." in entity_id else ""
        domain = DOMAIN_TAXONOMY.get(prefix)
        if domain:
            domains.add(domain)

    return sorted(domains)
