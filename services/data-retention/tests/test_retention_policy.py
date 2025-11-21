"""Tests for retention policy management."""

from datetime import datetime

import pytest
from src.retention_policy import RetentionPeriod, RetentionPolicy, RetentionPolicyManager


class TestRetentionPolicy:
    """Test RetentionPolicy class."""

    def test_default_policy(self):
        """Test default policy creation."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        assert policy.name == "test"
        assert policy.description == "Test policy"
        assert policy.retention_period == 30
        assert policy.retention_unit == RetentionPeriod.DAYS
        assert policy.enabled is True
        assert policy.created_at is not None
        assert policy.updated_at is not None

    def test_get_expiration_date_days(self):
        """Test expiration date calculation for days."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=7,
            retention_unit=RetentionPeriod.DAYS,
        )

        base_date = datetime(2024, 1, 10)
        expiration = policy.get_expiration_date(base_date)
        expected = datetime(2024, 1, 3)

        assert expiration == expected

    def test_get_expiration_date_weeks(self):
        """Test expiration date calculation for weeks."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=2,
            retention_unit=RetentionPeriod.WEEKS,
        )

        base_date = datetime(2024, 1, 10)
        expiration = policy.get_expiration_date(base_date)
        expected = datetime(2023, 12, 27)

        assert expiration == expected

    def test_get_expiration_date_months(self):
        """Test expiration date calculation for months."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=6,
            retention_unit=RetentionPeriod.MONTHS,
        )

        base_date = datetime(2024, 7, 10)
        expiration = policy.get_expiration_date(base_date)
        expected = datetime(2024, 1, 12)  # 6 months * 30 days = 180 days before

        assert expiration == expected

    def test_get_expiration_date_years(self):
        """Test expiration date calculation for years."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=1,
            retention_unit=RetentionPeriod.YEARS,
        )

        base_date = datetime(2024, 1, 10)
        expiration = policy.get_expiration_date(base_date)
        expected = datetime(2023, 1, 10)

        assert expiration == expected

    def test_to_dict(self):
        """Test policy to dictionary conversion."""
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        policy_dict = policy.to_dict()

        assert policy_dict["name"] == "test"
        assert policy_dict["description"] == "Test policy"
        assert policy_dict["retention_period"] == 30
        assert policy_dict["retention_unit"] == "days"
        assert policy_dict["enabled"] is True
        assert "created_at" in policy_dict
        assert "updated_at" in policy_dict

    def test_from_dict(self):
        """Test policy creation from dictionary."""
        policy_data = {
            "name": "test",
            "description": "Test policy",
            "retention_period": 30,
            "retention_unit": "days",
            "enabled": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        policy = RetentionPolicy.from_dict(policy_data)

        assert policy.name == "test"
        assert policy.description == "Test policy"
        assert policy.retention_period == 30
        assert policy.retention_unit == RetentionPeriod.DAYS
        assert policy.enabled is True

class TestRetentionPolicyManager:
    """Test RetentionPolicyManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = RetentionPolicyManager()

        assert len(manager.policies) == 1
        assert "default" in manager.policies
        assert manager.policies["default"].name == "default"

    def test_add_policy(self):
        """Test adding a policy."""
        manager = RetentionPolicyManager()

        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        manager.add_policy(policy)

        assert "test" in manager.policies
        assert manager.policies["test"] == policy

    def test_add_duplicate_policy(self):
        """Test adding duplicate policy."""
        manager = RetentionPolicyManager()

        policy = RetentionPolicy(
            name="default",
            description="Duplicate policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        with pytest.raises(ValueError, match="Policy 'default' already exists"):
            manager.add_policy(policy)

    def test_update_policy(self):
        """Test updating a policy."""
        manager = RetentionPolicyManager()

        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        manager.add_policy(policy)

        # Update policy
        policy.description = "Updated policy"
        manager.update_policy(policy)

        assert manager.policies["test"].description == "Updated policy"
        assert manager.policies["test"].updated_at > policy.created_at

    def test_remove_policy(self):
        """Test removing a policy."""
        manager = RetentionPolicyManager()

        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        manager.add_policy(policy)
        manager.remove_policy("test")

        assert "test" not in manager.policies

    def test_remove_default_policy(self):
        """Test removing default policy."""
        manager = RetentionPolicyManager()

        with pytest.raises(ValueError, match="Cannot remove default policy"):
            manager.remove_policy("default")

    def test_get_policy(self):
        """Test getting a policy."""
        manager = RetentionPolicyManager()

        policy = manager.get_policy("default")
        assert policy is not None
        assert policy.name == "default"

        policy = manager.get_policy("nonexistent")
        assert policy is None

    def test_get_all_policies(self):
        """Test getting all policies."""
        manager = RetentionPolicyManager()

        policies = manager.get_all_policies()
        assert len(policies) == 1
        assert policies[0].name == "default"

    def test_get_enabled_policies(self):
        """Test getting enabled policies."""
        manager = RetentionPolicyManager()

        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
            enabled=False,
        )

        manager.add_policy(policy)

        enabled_policies = manager.get_enabled_policies()
        assert len(enabled_policies) == 1
        assert enabled_policies[0].name == "default"

    def test_validate_policy(self):
        """Test policy validation."""
        manager = RetentionPolicyManager()

        # Valid policy
        valid_policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        errors = manager.validate_policy(valid_policy)
        assert len(errors) == 0

        # Invalid policy - no name
        invalid_policy = RetentionPolicy(
            name="",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

        errors = manager.validate_policy(invalid_policy)
        assert len(errors) > 0
        assert "Policy name is required" in errors

    def test_export_import_policies(self):
        """Test policy export and import."""
        manager = RetentionPolicyManager()

        # Add a test policy
        policy = RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )
        manager.add_policy(policy)

        # Export policies
        exported = manager.export_policies()
        assert "default" in exported
        assert "test" in exported

        # Import policies
        manager.import_policies(exported)

        # Verify policies were imported
        assert "default" in manager.policies
        assert "test" in manager.policies

    def test_get_policy_statistics(self):
        """Test policy statistics."""
        manager = RetentionPolicyManager()

        stats = manager.get_policy_statistics()

        assert stats["total_policies"] == 1
        assert stats["enabled_policies"] == 1
        assert stats["disabled_policies"] == 0
        assert stats["average_retention_days"] > 0
        assert "default" in stats["policy_names"]
