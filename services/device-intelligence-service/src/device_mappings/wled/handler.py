"""
WLED Device Handler

Handles WLED devices, including:
- Master controllers (control entire LED strip)
- Segments (control individual segments of LED strip)
"""

from typing import Any

from ..base import DeviceHandler, DeviceType


class WLEDHandler(DeviceHandler):
    """
    Handler for WLED devices.
    
    Detects:
    - WLED master controllers (entity_id contains "wled" but not "_segment_")
    - WLED segments (entity_id contains "_segment_")
    """
    
    def can_handle(self, device: dict[str, Any]) -> bool:
        """
        Check if this handler can process the given device.
        
        Args:
            device: Device dictionary from Device Registry
            
        Returns:
            True if device is a WLED device, False otherwise
        """
        manufacturer = (device.get("manufacturer") or "").lower()
        model = (device.get("model") or "").lower()
        name = (device.get("name") or "").lower()
        
        # Check manufacturer
        if "wled" in manufacturer or "aircoookie" in manufacturer:
            return True
        
        # Check model
        if "wled" in model:
            return True
        
        # Check name (WLED devices often have "wled" in name)
        if "wled" in name:
            return True
        
        # If no manufacturer/model but we have entities, check entity_id patterns
        # This will be handled in identify_type when entities are available
        return False
    
    def can_handle_entity(self, entity_id: str, device: dict[str, Any] | None = None) -> bool:
        """
        Check if this handler can handle an entity (by entity_id pattern).
        
        This is a helper method for entity-based detection when device data
        doesn't have manufacturer/model information.
        
        Args:
            entity_id: Entity ID
            device: Optional device dictionary
            
        Returns:
            True if entity appears to be WLED, False otherwise
        """
        entity_id_lower = entity_id.lower()
        
        # Check if entity_id contains "wled"
        if "wled" in entity_id_lower:
            return True
        
        # If device is provided, also check device data
        if device:
            return self.can_handle(device)
        
        return False
    
    def identify_type(
        self,
        device: dict[str, Any],
        entities: list[dict[str, Any]]
    ) -> DeviceType | None:
        """
        Identify device type (master or segment).
        
        Args:
            device: Device dictionary
            entities: List of entities associated with the device
            
        Returns:
            DeviceType.MASTER or DeviceType.SEGMENT, or None if cannot determine
        """
        # Check entities for segment pattern
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            if "_segment_" in entity_id.lower():
                return DeviceType.SEGMENT
        
        # Check device name/entity_id patterns
        device_name = (device.get("name") or "").lower()
        if "_segment_" in device_name:
            return DeviceType.SEGMENT
        
        # If we have entities, check if any are segments
        # If no segments found and device is WLED, assume master
        if self.can_handle(device) or any(
            self.can_handle_entity(entity.get("entity_id", ""), device)
            for entity in entities
        ):
            # Check if it's a segment by entity_id
            for entity in entities:
                entity_id = entity.get("entity_id", "")
                if "_segment_" in entity_id.lower():
                    return DeviceType.SEGMENT
            # Not a segment, so it's a master
            return DeviceType.MASTER
        
        return None
    
    def get_relationships(
        self,
        device: dict[str, Any],
        all_devices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Get device relationships.
        
        For WLED:
        - Segments link to their master (by base entity_id)
        - Masters contain all segments with same base name
        
        Args:
            device: Device dictionary
            all_devices: List of all devices for relationship discovery
            
        Returns:
            List of relationship dictionaries
        """
        relationships = []
        device_id = device.get("id", "")
        device_name = (device.get("name") or "").lower()
        
        # Check if this is a segment (by device name or entity_id pattern)
        is_segment = "_segment_" in device_name
        
        if is_segment:
            # This is a segment - find the master
            # Master typically has same base name without "_segment_N"
            base_name = device_name.split("_segment_")[0]
            
            # Look for master device with matching base name
            for other_device in all_devices:
                other_name = (other_device.get("name") or "").lower()
                other_id = other_device.get("id", "")
                
                # Master should have same base name and not be a segment
                if (
                    other_id != device_id and
                    other_name.startswith(base_name) and
                    "_segment_" not in other_name and
                    "wled" in other_name
                ):
                    relationships.append({
                        "type": "master",
                        "device_id": other_id,
                        "description": f"Master controller for this segment"
                    })
                    break
        else:
            # This is a master - find all segments
            base_name = device_name
            
            for other_device in all_devices:
                other_name = (other_device.get("name") or "").lower()
                other_id = other_device.get("id", "")
                
                # Segment should start with base name and contain "_segment_"
                if (
                    other_id != device_id and
                    other_name.startswith(base_name) and
                    "_segment_" in other_name
                ):
                    relationships.append({
                        "type": "segment",
                        "device_id": other_id,
                        "description": f"Segment controlled by this master"
                    })
        
        return relationships
    
    def enrich_context(
        self,
        device: dict[str, Any],
        entities: list[dict[str, Any]]
    ) -> str:
        """
        Enrich device context with device-specific information.
        
        Args:
            device: Device dictionary
            entities: List of entities associated with the device
            
        Returns:
            Enriched context string
        """
        device_name = device.get("name", device.get("id", "WLED Device"))
        device_type = self.identify_type(device, entities)
        
        if device_type == DeviceType.SEGMENT:
            # Find master for this segment
            base_name = (device.get("name") or "").lower().split("_segment_")[0]
            return f"{device_name} (WLED segment - part of {base_name} master)"
        elif device_type == DeviceType.MASTER:
            # Count segments
            segment_count = sum(
                1 for entity in entities
                if "_segment_" in entity.get("entity_id", "").lower()
            )
            if segment_count > 0:
                return f"{device_name} (WLED master - controls {segment_count} segments)"
            else:
                return f"{device_name} (WLED master - controls entire strip)"
        else:
            # Generic WLED device
            return f"{device_name} (WLED device)"

