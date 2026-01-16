"""
Template Library

Loads and manages versioned automation templates from JSON files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from .template_schema import Template

logger = logging.getLogger(__name__)


class TemplateLibrary:
    """
    Library for loading and managing automation templates.
    
    Templates are stored as JSON files in the templates/ directory.
    Each template defines:
    - template_id and version
    - Parameter schema
    - Compilation mapping to HA automation structure
    - Safety classification
    """
    
    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize template library.
        
        Args:
            templates_dir: Directory containing template JSON files.
                          Defaults to src/templates/templates/ relative to this file.
        """
        if templates_dir is None:
            # Default to templates/ directory relative to this file
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.templates: dict[str, dict[int, Template]] = {}  # template_id -> version -> Template
        self._load_templates()
    
    def _load_templates(self):
        """Load all templates from JSON files."""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_dir}")
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            return
        
        template_files = list(self.templates_dir.glob("*.json"))
        logger.info(f"Loading {len(template_files)} templates from {self.templates_dir}")
        
        for template_file in template_files:
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template_data = json.load(f)
                
                template = Template(**template_data)
                template_id = template.template_id
                version = template.version
                
                if template_id not in self.templates:
                    self.templates[template_id] = {}
                
                self.templates[template_id][version] = template
                logger.debug(f"Loaded template: {template_id} v{version}")
                
            except Exception as e:
                logger.error(f"Failed to load template from {template_file}: {e}", exc_info=True)
        
        logger.info(f"Loaded {sum(len(versions) for versions in self.templates.values())} template versions")
    
    def get_template(self, template_id: str, version: Optional[int] = None) -> Optional[Template]:
        """
        Get a template by ID and optional version.
        
        Args:
            template_id: Template identifier
            version: Template version (if None, returns latest version)
        
        Returns:
            Template instance or None if not found
        """
        if template_id not in self.templates:
            return None
        
        versions = self.templates[template_id]
        
        if version is None:
            # Return latest version
            version = max(versions.keys())
        
        return versions.get(version)
    
    def list_templates(self) -> list[dict[str, Any]]:
        """
        List all available templates with their latest versions.
        
        Returns:
            List of template metadata dictionaries
        """
        result = []
        for template_id, versions in self.templates.items():
            latest_version = max(versions.keys())
            template = versions[latest_version]
            result.append({
                "template_id": template_id,
                "version": latest_version,
                "description": template.description,
                "safety_class": template.safety_class.value,
                "required_capabilities": template.required_capabilities.model_dump()
            })
        return result
    
    def get_latest_version(self, template_id: str) -> Optional[int]:
        """
        Get the latest version number for a template.
        
        Args:
            template_id: Template identifier
        
        Returns:
            Latest version number or None if template not found
        """
        if template_id not in self.templates:
            return None
        
        return max(self.templates[template_id].keys())
    
    def template_exists(self, template_id: str, version: Optional[int] = None) -> bool:
        """
        Check if a template exists.
        
        Args:
            template_id: Template identifier
            version: Template version (if None, checks if any version exists)
        
        Returns:
            True if template exists, False otherwise
        """
        if template_id not in self.templates:
            return False
        
        if version is None:
            return True
        
        return version in self.templates[template_id]
