"""
Diff Generation - Generate JSON/YAML diffs for automation plans
"""

import json
import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def generate_json_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """
    Generate JSON diff between two automation plans.

    Args:
        old: Original automation plan
        new: New automation plan

    Returns:
        Dict with added, removed, and modified fields
    """
    diff = {
        "added": {},
        "removed": {},
        "modified": {},
    }

    # Compare recursively
    _compare_dicts(old, new, diff, "")

    return diff


def generate_yaml_diff(old_yaml: str, new_yaml: str) -> dict[str, Any]:
    """
    Generate diff between two YAML strings.

    Args:
        old_yaml: Original YAML
        new_yaml: New YAML

    Returns:
        Dict with diff information
    """
    try:
        old_dict = yaml.safe_load(old_yaml) or {}
        new_dict = yaml.safe_load(new_yaml) or {}
        return generate_json_diff(old_dict, new_dict)
    except Exception as e:
        logger.exception(f"Failed to generate YAML diff: {e}")
        return {
            "added": {},
            "removed": {},
            "modified": {},
            "error": str(e),
        }


def _compare_dicts(old: dict[str, Any], new: dict[str, Any], diff: dict[str, Any], path: str):
    """Recursively compare two dictionaries"""
    # Check for removed keys
    for key in old:
        full_path = f"{path}.{key}" if path else key
        if key not in new:
            _set_nested_value(diff["removed"], full_path, old[key])

    # Check for added/modified keys
    for key in new:
        full_path = f"{path}.{key}" if path else key
        if key not in old:
            _set_nested_value(diff["added"], full_path, new[key])
        else:
            old_val = old[key]
            new_val = new[key]

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                _compare_dicts(old_val, new_val, diff, full_path)
            elif isinstance(old_val, list) and isinstance(new_val, list):
                _compare_lists(old_val, new_val, diff, full_path)
            elif old_val != new_val:
                _set_nested_value(diff["modified"], full_path, {
                    "old": old_val,
                    "new": new_val,
                })


def _compare_lists(old: list[Any], new: list[Any], diff: dict[str, Any], path: str):
    """Compare two lists"""
    if len(old) != len(new):
        _set_nested_value(diff["modified"], path, {
            "old": old,
            "new": new,
            "type": "list_length_change",
        })
    else:
        # Compare elements
        for i, (old_item, new_item) in enumerate(zip(old, new, strict=False)):
            if old_item != new_item:
                item_path = f"{path}[{i}]"
                if isinstance(old_item, dict) and isinstance(new_item, dict):
                    _compare_dicts(old_item, new_item, diff, item_path)
                else:
                    _set_nested_value(diff["modified"], item_path, {
                        "old": old_item,
                        "new": new_item,
                    })


def _set_nested_value(d: dict[str, Any], path: str, value: Any):
    """Set a nested value in a dict using dot notation path"""
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def format_diff_for_display(diff: dict[str, Any]) -> str:
    """
    Format diff for human-readable display.

    Args:
        diff: Diff dict from generate_json_diff

    Returns:
        Human-readable diff string
    """
    lines = []

    if diff.get("added"):
        lines.append("Added:")
        for path, value in _flatten_dict(diff["added"]).items():
            lines.append(f"  + {path}: {json.dumps(value)}")

    if diff.get("removed"):
        lines.append("Removed:")
        for path, value in _flatten_dict(diff["removed"]).items():
            lines.append(f"  - {path}: {json.dumps(value)}")

    if diff.get("modified"):
        lines.append("Modified:")
        for path, change in _flatten_dict(diff["modified"]).items():
            if isinstance(change, dict) and "old" in change and "new" in change:
                lines.append(f"  ~ {path}:")
                lines.append(f"    old: {json.dumps(change['old'])}")
                lines.append(f"    new: {json.dumps(change['new'])}")
            else:
                lines.append(f"  ~ {path}: {json.dumps(change)}")

    return "\n".join(lines) if lines else "No changes"


def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten nested dict to dot-notation keys"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

