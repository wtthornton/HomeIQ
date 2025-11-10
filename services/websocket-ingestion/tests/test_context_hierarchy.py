"""
Tests for Context Hierarchy Tracking (Epic 23.1)
"""

import pytest
from datetime import datetime
from src.event_processor import EventProcessor


class TestContextHierarchy:
    """Test suite for context.parent_id extraction"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = EventProcessor()
    
    def test_extract_context_with_parent_id(self):
        """Test extraction of context with parent_id"""
        event_data = {
            "event_type": "state_changed",
            "context": {
                "id": "context123",
                "parent_id": "parent_context456",
                "user_id": "user789"
            },
            "data": {
                "entity_id": "sensor.test",
                "new_state": {
                    "state": "on",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                },
                "old_state": {
                    "state": "off",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        result = self.processor.process_event(event_data)
        
        assert result is not None
        assert result.get("context_id") == "context123"
        assert result.get("context_parent_id") == "parent_context456"
        assert result.get("context_user_id") == "user789"
    
    def test_extract_context_without_parent_id(self):
        """Test extraction of context without parent_id (user-initiated event)"""
        event_data = {
            "event_type": "state_changed",
            "context": {
                "id": "context123",
                "parent_id": None,
                "user_id": "user789"
            },
            "data": {
                "entity_id": "sensor.test",
                "new_state": {
                    "state": "on",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        result = self.processor.process_event(event_data)
        
        assert result is not None
        assert result.get("context_id") == "context123"
        assert result.get("context_parent_id") is None
        assert result.get("context_user_id") == "user789"
    
    def test_extract_context_missing(self):
        """Test extraction when context is missing"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "sensor.test",
                "new_state": {
                    "state": "on",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        result = self.processor.process_event(event_data)
        
        assert result is not None
        assert result.get("context_id") is None
        assert result.get("context_parent_id") is None
        assert result.get("context_user_id") is None
    
    def test_validation_statistics(self):
        """Test that validation statistics are tracked"""
        # Process valid event
        valid_event = {
            "event_type": "state_changed",
            "context": {
                "id": "context123",
                "parent_id": "parent456"
            },
            "data": {
                "entity_id": "sensor.test",
                "new_state": {
                    "state": "on",
                    "attributes": {},
                    "last_changed": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        self.processor.process_event(valid_event)
        
        stats = self.processor.get_processing_statistics()
        assert stats["processed_events"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

