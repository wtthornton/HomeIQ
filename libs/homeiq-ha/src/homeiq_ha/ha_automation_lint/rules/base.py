"""
Base class for all lint rules.
"""

from abc import ABC, abstractmethod
from typing import List
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AutomationIR, Finding


class Rule(ABC):
    """
    Base class for all lint rules.

    Each rule implements a single check that can be applied to an automation.
    Rules are versioned via RULESET_VERSION and must maintain stable IDs.
    """

    rule_id: str
    name: str
    severity: str
    category: str
    enabled: bool = True

    @abstractmethod
    def check(self, automation: AutomationIR) -> List[Finding]:
        """
        Check this rule against an automation and return findings.

        Args:
            automation: The automation IR to check

        Returns:
            List of findings (empty if no issues found)
        """
        pass

    def __repr__(self) -> str:
        """String representation of the rule."""
        return f"<Rule {self.rule_id}: {self.name} ({self.severity})>"
