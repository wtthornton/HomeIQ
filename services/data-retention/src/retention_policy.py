"""Data retention policy management."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class RetentionPeriod(Enum):
    """Retention period types."""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"

@dataclass
class RetentionPolicy:
    """Data retention policy configuration."""

    name: str
    description: str
    retention_period: int
    retention_unit: RetentionPeriod
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def get_expiration_date(self, from_date: datetime | None = None) -> datetime:
        """
        Calculate expiration date based on retention policy.
        
        Args:
            from_date: Base date for calculation (defaults to now)
            
        Returns:
            datetime: Expiration date
        """
        if from_date is None:
            from_date = datetime.now(timezone.utc)

        if self.retention_unit == RetentionPeriod.DAYS:
            return from_date - timedelta(days=self.retention_period)
        elif self.retention_unit == RetentionPeriod.WEEKS:
            return from_date - timedelta(weeks=self.retention_period)
        elif self.retention_unit == RetentionPeriod.MONTHS:
            # Approximate months as 30 days
            return from_date - timedelta(days=self.retention_period * 30)
        elif self.retention_unit == RetentionPeriod.YEARS:
            # Approximate years as 365 days
            return from_date - timedelta(days=self.retention_period * 365)
        else:
            raise ValueError(f"Unknown retention unit: {self.retention_unit}")

    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "retention_period": self.retention_period,
            "retention_unit": self.retention_unit.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'RetentionPolicy':
        """Create policy from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            retention_period=data["retention_period"],
            retention_unit=RetentionPeriod(data["retention_unit"]),
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

class RetentionPolicyManager:
    """Manages data retention policies."""

    def __init__(self):
        """Initialize retention policy manager."""
        self.policies: dict[str, RetentionPolicy] = {}
        self.default_policy = RetentionPolicy(
            name="default",
            description="Default 1-year retention policy",
            retention_period=1,
            retention_unit=RetentionPeriod.YEARS
        )
        self.policies["default"] = self.default_policy

        logger.info("Retention policy manager initialized")

    def add_policy(self, policy: RetentionPolicy) -> None:
        """
        Add a new retention policy.

        Args:
            policy: Retention policy to add
        """
        errors = self.validate_policy(policy)
        if errors:
            raise ValueError(f"Invalid policy: {'; '.join(errors)}")

        if policy.name in self.policies:
            raise ValueError(f"Policy '{policy.name}' already exists")

        self.policies[policy.name] = policy
        logger.info(f"Added retention policy: {policy.name}")

    def update_policy(self, policy: RetentionPolicy) -> None:
        """
        Update an existing retention policy.

        Args:
            policy: Updated retention policy
        """
        errors = self.validate_policy(policy)
        if errors:
            raise ValueError(f"Invalid policy: {'; '.join(errors)}")

        if policy.name not in self.policies:
            raise ValueError(f"Policy '{policy.name}' does not exist")

        policy.updated_at = datetime.now(timezone.utc)
        self.policies[policy.name] = policy
        logger.info(f"Updated retention policy: {policy.name}")

    def remove_policy(self, policy_name: str) -> None:
        """
        Remove a retention policy.
        
        Args:
            policy_name: Name of policy to remove
        """
        if policy_name == "default":
            raise ValueError("Cannot remove default policy")

        if policy_name not in self.policies:
            raise ValueError(f"Policy '{policy_name}' does not exist")

        del self.policies[policy_name]
        logger.info(f"Removed retention policy: {policy_name}")

    def get_policy(self, policy_name: str) -> RetentionPolicy | None:
        """
        Get a retention policy by name.
        
        Args:
            policy_name: Name of policy to get
            
        Returns:
            RetentionPolicy or None if not found
        """
        return self.policies.get(policy_name)

    def get_all_policies(self) -> list[RetentionPolicy]:
        """
        Get all retention policies.
        
        Returns:
            List of all retention policies
        """
        return list(self.policies.values())

    def get_enabled_policies(self) -> list[RetentionPolicy]:
        """
        Get all enabled retention policies.
        
        Returns:
            List of enabled retention policies
        """
        return [policy for policy in self.policies.values() if policy.enabled]

    def validate_policy(self, policy: RetentionPolicy) -> list[str]:
        """
        Validate a retention policy.
        
        Args:
            policy: Policy to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not policy.name:
            errors.append("Policy name is required")

        if not policy.description:
            errors.append("Policy description is required")

        if policy.retention_period <= 0:
            errors.append("Retention period must be positive")

        if policy.retention_period > 100:
            errors.append("Retention period seems too long (>100 years)")

        return errors

    def export_policies(self) -> str:
        """
        Export all policies to JSON string.
        
        Returns:
            JSON string containing all policies
        """
        policies_data = {
            "policies": [policy.to_dict() for policy in self.policies.values()],
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        return json.dumps(policies_data, indent=2)

    def import_policies(self, policies_json: str) -> None:
        """
        Import policies from JSON string.
        
        Args:
            policies_json: JSON string containing policies
        """
        try:
            data = json.loads(policies_json)
            policies_data = data.get("policies", [])

            # Clear existing policies (except default)
            self.policies = {"default": self.default_policy}

            for policy_data in policies_data:
                if policy_data["name"] != "default":
                    policy = RetentionPolicy.from_dict(policy_data)
                    self.policies[policy.name] = policy

            logger.info(f"Imported {len(policies_data)} retention policies")

        except Exception as e:
            logger.error(f"Failed to import policies: {e}")
            raise ValueError(f"Invalid policies JSON: {e}")

    def get_policy_statistics(self) -> dict[str, Any]:
        """
        Get statistics about retention policies.
        
        Returns:
            Dictionary containing policy statistics
        """
        total_policies = len(self.policies)
        enabled_policies = len(self.get_enabled_policies())

        # Calculate average retention period
        total_days = 0
        for policy in self.policies.values():
            if policy.retention_unit == RetentionPeriod.DAYS:
                total_days += policy.retention_period
            elif policy.retention_unit == RetentionPeriod.WEEKS:
                total_days += policy.retention_period * 7
            elif policy.retention_unit == RetentionPeriod.MONTHS:
                total_days += policy.retention_period * 30
            elif policy.retention_unit == RetentionPeriod.YEARS:
                total_days += policy.retention_period * 365

        avg_retention_days = total_days / total_policies if total_policies > 0 else 0

        return {
            "total_policies": total_policies,
            "enabled_policies": enabled_policies,
            "disabled_policies": total_policies - enabled_policies,
            "average_retention_days": avg_retention_days,
            "policy_names": list(self.policies.keys())
        }
