"""MAC OUI vendor lookup from IEEE database.

Resolves the first 3 octets of a MAC address to a manufacturer name
using a bundled dictionary of common IoT/networking vendors. Falls back
to "Unknown" for unrecognized OUIs.
"""

from __future__ import annotations

from homeiq_observability.logging_config import setup_logging

logger = setup_logging("zeek-oui-lookup")

# Common IoT and networking vendor OUI prefixes (uppercase, colon-separated).
# This is a curated subset covering the most common smart home devices.
# A full IEEE OUI database has ~30,000 entries; we keep the top ~200
# relevant to home automation and can extend as needed.
_OUI_DATABASE: dict[str, str] = {
    # --- Smart Home Platforms ---
    "DC:A6:32": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    "28:CD:C1": "Raspberry Pi",
    "D8:3A:DD": "Raspberry Pi",
    # --- Espressif (ESP32/ESP8266 — Tasmota, ESPHome) ---
    "24:6F:28": "Espressif",
    "30:AE:A4": "Espressif",
    "A4:CF:12": "Espressif",
    "AC:67:B2": "Espressif",
    "BC:DD:C2": "Espressif",
    "CC:50:E3": "Espressif",
    "EC:FA:BC": "Espressif",
    "10:52:1C": "Espressif",
    "24:0A:C4": "Espressif",
    "24:62:AB": "Espressif",
    "34:AB:95": "Espressif",
    "40:F5:20": "Espressif",
    "48:3F:DA": "Espressif",
    "4C:EB:D6": "Espressif",
    "58:BF:25": "Espressif",
    "7C:DF:A1": "Espressif",
    "84:CC:A8": "Espressif",
    "84:F3:EB": "Espressif",
    "8C:AA:B5": "Espressif",
    "94:B9:7E": "Espressif",
    "A0:20:A6": "Espressif",
    "B4:E6:2D": "Espressif",
    "C4:4F:33": "Espressif",
    "D8:A0:1D": "Espressif",
    "F0:08:D1": "Espressif",
    "F4:CF:A2": "Espressif",
    # --- Tuya (generic IoT) ---
    "D8:1F:12": "Tuya",
    "10:D5:61": "Tuya",
    "68:57:2D": "Tuya",
    "7C:F6:66": "Tuya",
    # --- Shelly ---
    "EC:FA:BC": "Shelly (Espressif)",
    "34:94:54": "Shelly",
    "C4:5B:BE": "Shelly",
    # --- Philips Hue (Signify) ---
    "00:17:88": "Philips Hue",
    "EC:B5:FA": "Philips Hue",
    # --- IKEA (Tradfri) ---
    "D0:FC:CC": "IKEA",
    "94:34:69": "IKEA",
    # --- Sonos ---
    "78:28:CA": "Sonos",
    "5C:AA:FD": "Sonos",
    "B8:E9:37": "Sonos",
    "48:A6:B8": "Sonos",
    # --- Google (Nest, Chromecast) ---
    "F4:F5:D8": "Google",
    "54:60:09": "Google",
    "A4:77:33": "Google",
    "30:FD:38": "Google",
    "6C:AD:F8": "Google",
    "F8:8F:CA": "Google",
    # --- Amazon (Echo, Ring) ---
    "FC:65:DE": "Amazon",
    "44:65:0D": "Amazon",
    "68:54:FD": "Amazon",
    "74:C2:46": "Amazon",
    "A0:02:DC": "Amazon",
    "B0:FC:0D": "Amazon",
    "F0:F0:A4": "Amazon",
    "38:F7:3D": "Amazon",
    "40:B4:CD": "Amazon",
    # --- Apple ---
    "3C:E0:72": "Apple",
    "AC:BC:32": "Apple",
    "F0:B4:79": "Apple",
    "A8:5C:2C": "Apple",
    "14:98:77": "Apple",
    "28:6A:BA": "Apple",
    "54:4E:90": "Apple",
    "70:56:81": "Apple",
    "8C:85:90": "Apple",
    "F8:FF:C2": "Apple",
    # --- Samsung (SmartThings, TVs) ---
    "8C:79:F5": "Samsung",
    "D0:03:DF": "Samsung",
    "F4:7B:09": "Samsung",
    "BC:72:B1": "Samsung",
    "CC:07:AB": "Samsung",
    # --- TP-Link (Kasa, Tapo) ---
    "50:C7:BF": "TP-Link",
    "60:32:B1": "TP-Link",
    "98:DA:C4": "TP-Link",
    "B0:4E:26": "TP-Link",
    "C0:06:C3": "TP-Link",
    "1C:3B:F3": "TP-Link",
    # --- Meross ---
    "48:E1:E9": "Meross",
    # --- Xiaomi / Aqara ---
    "04:CF:8C": "Xiaomi",
    "28:6C:07": "Xiaomi",
    "50:64:2B": "Xiaomi",
    "64:CC:2E": "Xiaomi",
    "78:11:DC": "Xiaomi",
    "7C:49:EB": "Xiaomi",
    # --- Ring / Blink ---
    "3C:24:F0": "Ring",
    "9C:76:1B": "Ring",
    # --- Wyze ---
    "2C:AA:8E": "Wyze",
    # --- Zigbee Coordinators ---
    "00:12:4B": "Texas Instruments (Zigbee)",
    "00:15:8D": "Silicon Labs (Zigbee)",
    # --- Z-Wave ---
    "00:1E:E1": "Silicon Labs (Z-Wave)",
    # --- Network Equipment ---
    "00:1A:2B": "Ubiquiti",
    "24:5A:4C": "Ubiquiti",
    "44:D9:E7": "Ubiquiti",
    "68:D7:9A": "Ubiquiti",
    "74:83:C2": "Ubiquiti",
    "80:2A:A8": "Ubiquiti",
    "FC:EC:DA": "Ubiquiti",
    "18:E8:29": "Ubiquiti",
    "E0:63:DA": "Ubiquiti",
    "B4:FB:E4": "Ubiquiti",
    "78:8A:20": "Ubiquiti",
    "00:1E:58": "D-Link",
    "1C:7E:E5": "D-Link",
    "28:10:7B": "D-Link",
    "F0:7D:68": "D-Link",
    "00:24:01": "Netgear",
    "20:E5:2A": "Netgear",
    "6C:B0:CE": "Netgear",
    "C4:04:15": "Netgear",
    "E4:F4:C6": "Netgear",
    "00:18:E7": "Asus",
    "04:D9:F5": "Asus",
    "50:46:5D": "Asus",
    "60:45:CB": "Asus",
    # --- Cameras ---
    "7C:DD:90": "Reolink",
    "EC:71:DB": "Reolink",
    "9C:8E:CD": "Amcrest",
    "B0:C5:54": "Hikvision",
    "28:57:BE": "Hikvision",
    "C0:56:E3": "Hikvision",
    # --- Power/Energy ---
    "00:0D:6F": "Sense Energy",
    "60:01:94": "Emporia Energy",
    # --- Other Smart Home ---
    "00:1D:C9": "Ecobee",
    "44:61:32": "Ecobee",
    "18:B4:30": "Honeywell",
    "88:E6:28": "Honeywell",
    "64:90:C1": "Lutron",
    "00:23:A7": "Redmond (Gardena)",
}


class OUILookup:
    """Look up device vendor from MAC address using OUI prefix."""

    def __init__(self) -> None:
        self._db = _OUI_DATABASE
        logger.info("OUI database loaded with %d entries", len(self._db))

    def lookup(self, mac_address: str) -> str:
        """Return vendor name for a MAC address, or 'Unknown'.

        Args:
            mac_address: MAC in any format (AA:BB:CC:DD:EE:FF or aa-bb-cc-dd-ee-ff).

        Returns:
            Vendor name string.
        """
        normalized = mac_address.upper().replace("-", ":")
        prefix = normalized[:8]  # First 3 octets: "AA:BB:CC"
        return self._db.get(prefix, "Unknown")
