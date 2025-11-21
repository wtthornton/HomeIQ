"""
Log Format Validation and Consistency Checks
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ValidationResult:
    """Result of log validation"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]


class LogValidator:
    """Validator for structured log format and consistency"""

    # Required fields for structured logs
    REQUIRED_FIELDS = {
        "timestamp", "level", "service", "message",
    }

    # Optional but recommended fields
    RECOMMENDED_FIELDS = {
        "correlation_id", "context", "performance",
    }

    # Valid log levels
    VALID_LEVELS = {
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL",
    }

    # Valid service names (should match actual services)
    VALID_SERVICES = {
        "websocket-ingestion",
        "enrichment-pipeline",
        "data-retention",
        "admin-api",
        "health-dashboard",
        "weather-api",
    }

    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        self.validation_suggestions = []

    def validate_log_entry(self, log_entry: str) -> ValidationResult:
        """
        Validate a single log entry

        Args:
            log_entry: JSON string log entry

        Returns:
            ValidationResult with validation status and issues
        """
        self.validation_errors = []
        self.validation_warnings = []
        self.validation_suggestions = []

        try:
            # Parse JSON
            log_data = json.loads(log_entry)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON format: {e!s}"],
                warnings=[],
                suggestions=[],
            )

        # Validate required fields
        self._validate_required_fields(log_data)

        # Validate field formats
        self._validate_field_formats(log_data)

        # Validate context structure
        self._validate_context_structure(log_data)

        # Validate performance metrics
        self._validate_performance_metrics(log_data)

        # Check for consistency issues
        self._check_consistency(log_data)

        is_valid = len(self.validation_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=self.validation_errors.copy(),
            warnings=self.validation_warnings.copy(),
            suggestions=self.validation_suggestions.copy(),
        )

    def _validate_required_fields(self, log_data: dict[str, Any]):
        """Validate that all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in log_data:
                self.validation_errors.append(f"Missing required field: {field}")

    def _validate_field_formats(self, log_data: dict[str, Any]):
        """Validate field formats and values"""
        # Validate timestamp format
        if "timestamp" in log_data:
            timestamp = log_data["timestamp"]
            if not self._is_valid_timestamp(timestamp):
                self.validation_errors.append(f"Invalid timestamp format: {timestamp}")

        # Validate log level
        if "level" in log_data:
            level = log_data["level"]
            if level not in self.VALID_LEVELS:
                self.validation_errors.append(f"Invalid log level: {level}")

        # Validate service name
        if "service" in log_data:
            service = log_data["service"]
            if service not in self.VALID_SERVICES:
                self.validation_warnings.append(f"Unknown service name: {service}")

        # Validate correlation ID format
        if "correlation_id" in log_data:
            corr_id = log_data["correlation_id"]
            if corr_id and not self._is_valid_correlation_id(corr_id):
                self.validation_warnings.append(f"Invalid correlation ID format: {corr_id}")

    def _validate_context_structure(self, log_data: dict[str, Any]):
        """Validate context structure and fields"""
        if "context" in log_data:
            context = log_data["context"]
            if not isinstance(context, dict):
                self.validation_errors.append("Context field must be a dictionary")
                return

            # Check for recommended context fields
            recommended_context_fields = {
                "filename", "lineno", "function", "module", "pathname",
            }

            for field in recommended_context_fields:
                if field not in context:
                    self.validation_suggestions.append(f"Consider adding context field: {field}")

    def _validate_performance_metrics(self, log_data: dict[str, Any]):
        """Validate performance metrics structure"""
        if "performance" in log_data:
            performance = log_data["performance"]
            if not isinstance(performance, dict):
                self.validation_errors.append("Performance field must be a dictionary")
                return

            # Check for required performance fields
            if "operation" not in performance:
                self.validation_warnings.append("Performance metrics missing operation field")

            if "duration_ms" in performance:
                duration = performance["duration_ms"]
                if not isinstance(duration, (int, float)) or duration < 0:
                    self.validation_errors.append("Invalid duration_ms value in performance metrics")

    def _check_consistency(self, log_data: dict[str, Any]):
        """Check for consistency issues"""
        # Check if error level has exception info
        if log_data.get("level") == "ERROR" and "exception" not in log_data:
            self.validation_suggestions.append("Error level logs should include exception information")

        # Check if performance metrics are present but no operation
        if "performance" in log_data and "operation" not in log_data["performance"]:
            self.validation_warnings.append("Performance metrics present but no operation specified")

    def _is_valid_timestamp(self, timestamp: str) -> bool:
        """Check if timestamp is in valid ISO format"""
        try:
            # Try to parse ISO format timestamp
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    def _is_valid_correlation_id(self, corr_id: str) -> bool:
        """Check if correlation ID has valid format"""
        # Expected format: req_timestamp_hex
        pattern = r"^req_\d+_[a-f0-9]{8}$"
        return bool(re.match(pattern, corr_id))

    def validate_log_batch(self, log_entries: list[str]) -> dict[str, ValidationResult]:
        """
        Validate a batch of log entries

        Args:
            log_entries: List of JSON string log entries

        Returns:
            Dictionary mapping log entry index to validation result
        """
        results = {}

        for i, log_entry in enumerate(log_entries):
            results[str(i)] = self.validate_log_entry(log_entry)

        return results

    def get_validation_summary(self, results: dict[str, ValidationResult]) -> dict[str, Any]:
        """
        Get summary of validation results

        Args:
            results: Dictionary of validation results

        Returns:
            Summary statistics
        """
        total_entries = len(results)
        valid_entries = sum(1 for result in results.values() if result.is_valid)
        total_errors = sum(len(result.errors) for result in results.values())
        total_warnings = sum(len(result.warnings) for result in results.values())
        total_suggestions = sum(len(result.suggestions) for result in results.values())

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "invalid_entries": total_entries - valid_entries,
            "validation_rate": (valid_entries / total_entries * 100) if total_entries > 0 else 0,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_suggestions": total_suggestions,
            "error_rate": (total_errors / total_entries) if total_entries > 0 else 0,
        }

    def validate_service_logs(self, service_name: str, log_entries: list[str]) -> ValidationResult:
        """
        Validate logs for a specific service

        Args:
            service_name: Name of the service
            log_entries: List of log entries for the service

        Returns:
            Combined validation result
        """
        all_errors = []
        all_warnings = []
        all_suggestions = []

        for log_entry in log_entries:
            result = self.validate_log_entry(log_entry)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_suggestions.extend(result.suggestions)

        # Check service-specific consistency
        self._validate_service_consistency(service_name, log_entries, all_warnings, all_suggestions)

        is_valid = len(all_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
        )

    def _validate_service_consistency(self, service_name: str, log_entries: list[str],
                                    warnings: list[str], suggestions: list[str]):
        """Validate service-specific consistency"""
        # Check if all logs have the correct service name
        service_mismatches = 0
        for log_entry in log_entries:
            try:
                log_data = json.loads(log_entry)
                if log_data.get("service") != service_name:
                    service_mismatches += 1
            except json.JSONDecodeError:
                continue

        if service_mismatches > 0:
            warnings.append(f"{service_mismatches} log entries have incorrect service name")

        # Check for correlation ID consistency
        correlation_ids = set()
        for log_entry in log_entries:
            try:
                log_data = json.loads(log_entry)
                corr_id = log_data.get("correlation_id")
                if corr_id:
                    correlation_ids.add(corr_id)
            except json.JSONDecodeError:
                continue

        if len(correlation_ids) > 1:
            suggestions.append(f"Multiple correlation IDs found in service logs: {len(correlation_ids)} unique IDs")


def validate_log_format(log_entry: str) -> ValidationResult:
    """
    Convenience function to validate a single log entry

    Args:
        log_entry: JSON string log entry

    Returns:
        ValidationResult
    """
    validator = LogValidator()
    return validator.validate_log_entry(log_entry)


def validate_log_consistency(log_entries: list[str]) -> dict[str, Any]:
    """
    Convenience function to validate log consistency across entries

    Args:
        log_entries: List of log entries

    Returns:
        Validation summary
    """
    validator = LogValidator()
    results = validator.validate_log_batch(log_entries)
    return validator.get_validation_summary(results)
