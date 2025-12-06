"""
Hue Device Handler

Handles Philips Hue devices, including:
- Room/Zone groups (Model: "Room" or "Zone")
- Individual lights (Model: specific bulb type)
"""

from typing import Any

from ..base import DeviceHandler, DeviceType


class HueHandler(DeviceHandler):
    """
    Handler for Philips Hue devices.
    
    Detects:
    - Hue Room/Zone groups (Model: "Room" or "Zone")
    - Individual Hue lights (Model: specific bulb type like "Hue go", "Hue color downlight")
    """
    
    def can_handle(self, device: dict[str, Any]) -> bool:
        """
        Check if this handler can process the given device.
        
        Args:
            device: Device dictionary from Device Registry
            
        Returns:
            True if device is a Philips Hue device, False otherwise
        """
        manufacturer = device.get("manufacturer", "").lower()
        return manufacturer in ["signify", "philips"]
    
    def identify_type(self, device: dict[str, Any], entity: dict[str, Any]) -> DeviceType:
        """
        Identify the device type (group or individual).
        
        Args:
            device: Device dictionary from Device Registry
            entity: Entity dictionary from Entity Registry or States
            
        Returns:
            DeviceType.GROUP for Room/Zone groups, DeviceType.INDIVIDUAL for individual lights
        """
        model = device.get("model", "").lower()
        
        # Hue Room/Zone groups have Model: "Room" or "Zone"
        if model in ["room", "zone"]:
            return DeviceType.GROUP
        
        # Individual Hue lights have specific bulb types (e.g., "Hue go", "Hue color downlight")
        return DeviceType.INDIVIDUAL
    
    def get_relationships(self, device: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Get device relationships (lights to room groups).
        
        Args:
            device: Device dictionary from Device Registry
            entities: List of related entities
            
        Returns:
            Dictionary with relationship information
        """
        device_type = self.identify_type(device, {})
        
        if device_type == DeviceType.GROUP:
            # Room/Zone group: find individual lights in the same area
            area_id = device.get("area_id")
            device_id = device.get("id")
            
            # Find individual lights in the same area
            individual_lights = []
            for entity in entities:
                entity_area_id = entity.get("area_id")
                entity_device_id = entity.get("device_id")
                
                # Individual lights in the same area (but different device)
                if entity_area_id == area_id and entity_device_id != device_id:
                    # Check if it's a Hue individual light
                    # This would require checking the entity's device, which we'd need to pass
                    # For now, we'll return basic relationship info
                    individual_lights.append({
                        "entity_id": entity.get("entity_id"),
                        "friendly_name": entity.get("friendly_name")
                    })
            
            return {
                "type": "room_group",
                "area_id": area_id,
                "individual_lights": individual_lights
            }
        
        # Individual lights: find their room group
        area_id = device.get("area_id")
        device_id = device.get("id")
        
        # Find Room group in the same area
        room_group = None
        for entity in entities:
            entity_area_id = entity.get("area_id")
            entity_device_id = entity.get("device_id")
            
            # Room group in the same area (but different device)
            if entity_area_id == area_id and entity_device_id != device_id:
                # Check if it's a Room group (would need device info)
                # For now, return basic relationship info
                room_group = {
                    "entity_id": entity.get("entity_id"),
                    "friendly_name": entity.get("friendly_name")
                }
                break
        
        return {
            "type": "individual_light",
            "area_id": area_id,
            "room_group": room_group
        }
    
    def enrich_context(self, device: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
        """
        Add device-specific context for AI agent.
        
        Args:
            device: Device dictionary from Device Registry
            entity: Entity dictionary from Entity Registry or States
            
        Returns:
            Dictionary with enriched context information
        """
        device_type = self.identify_type(device, entity)
        model = device.get("model", "")
        manufacturer = device.get("manufacturer", "")
        
        if device_type == DeviceType.GROUP:
            # Room/Zone group
            group_type = "Room" if model.lower() == "room" else "Zone"
            return {
                "description": f"Hue {group_type} - controls all lights in the area",
                "device_type": "hue_group",
                "group_type": group_type.lower(),
                "manufacturer": manufacturer,
                "model": model
            }
        
        # Individual light
        return {
            "description": f"Hue {model}",
            "device_type": "hue_individual",
            "manufacturer": manufacturer,
            "model": model,
            "bulb_type": model
        }

