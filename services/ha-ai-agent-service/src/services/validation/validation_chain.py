"""
Validation Chain - Chain of Responsibility pattern for validation strategies.

Tries validation strategies in order until one succeeds or all fail.
"""

import logging
from typing import Optional

from ...models.automation_models import ValidationResult
from .validation_strategy import ValidationStrategy

logger = logging.getLogger(__name__)


class ValidationChain:
    """
    Chain of validation strategies.

    Tries each strategy in order until one succeeds (returns valid=True)
    or all strategies are exhausted.
    """

    def __init__(self, strategies: list[ValidationStrategy]):
        """
        Initialize validation chain.

        Args:
            strategies: List of validation strategies to try in order
        """
        self.strategies = strategies

    async def validate(self, automation_yaml: str) -> ValidationResult:
        """
        Validate automation YAML using chain of strategies.

        Tries each strategy in order until one succeeds or all fail.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            ValidationResult from first successful strategy, or combined
            result from all strategies if all fail
        """
        all_errors: list[str] = []
        all_warnings: list[str] = []
        last_result: Optional[ValidationResult] = None

        services_unavailable = []
        
        for strategy in self.strategies:
            try:
                logger.debug(f"Trying validation strategy: {strategy.name}")
                result = await strategy.validate(automation_yaml)

                # If validation passed, return immediately
                if result.valid:
                    logger.info(f"✅ Validation succeeded using {strategy.name}")
                    # Add strategy name to result for tracking
                    result.strategy_name = strategy.name
                    return result

                # Collect errors and warnings for fallback
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                last_result = result

                logger.debug(
                    f"Validation strategy {strategy.name} failed: "
                    f"{len(result.errors)} errors, {len(result.warnings)} warnings"
                )

            except Exception as e:
                logger.warning(
                    f"Validation strategy {strategy.name} failed with exception: {e}. "
                    "Trying next strategy..."
                )
                # Track unavailable services
                services_unavailable.append(strategy.name)
                # Continue to next strategy
                continue

        # All strategies failed - return combined result
        if last_result:
            # Use the last result but combine all errors/warnings
            warnings = list(set(all_warnings))  # Remove duplicates
            if services_unavailable:
                warnings.append(
                    f"Validation services unavailable: {', '.join(services_unavailable)}. "
                    "Using basic validation as fallback."
                )
            
            result = ValidationResult(
                valid=False,
                errors=list(set(all_errors)),  # Remove duplicates
                warnings=warnings,
                score=last_result.score,
                fixed_yaml=last_result.fixed_yaml,
                fixes_applied=last_result.fixes_applied,
                strategy_name=last_result.strategy_name if last_result.strategy_name else "Basic Validation",
                services_unavailable=services_unavailable if services_unavailable else None,
            )
            return result

        # No strategies available
        logger.error("All validation strategies failed or unavailable")
        result = ValidationResult(
            valid=False,
            errors=["All validation strategies failed or unavailable"],
            warnings=[],
            strategy_name="None",
            services_unavailable=services_unavailable if services_unavailable else None,
        )
        return result
