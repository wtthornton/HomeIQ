"""
Model Versioning

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.5: Incremental Model Updates

Manage model versions and rollback.
"""

import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .quality_model import PatternQualityModel

logger = logging.getLogger(__name__)


class ModelVersionManager:
    """
    Manage model versions and rollback.
    
    Tracks model versions, metadata, and enables rollback to previous versions.
    """
    
    def __init__(self, models_dir: Path | str):
        """
        Initialize version manager.
        
        Args:
            models_dir: Directory to store model versions
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.models_dir / "versions.json"
        self._versions: dict[str, dict[str, Any]] = {}
        self._load_versions()
    
    def _load_versions(self) -> None:
        """Load version metadata from disk."""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r') as f:
                    self._versions = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading versions: {e}")
                self._versions = {}
        else:
            self._versions = {}
    
    def _save_versions(self) -> None:
        """Save version metadata to disk."""
        try:
            with open(self.version_file, 'w') as f:
                json.dump(self._versions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving versions: {e}", exc_info=True)
    
    def _generate_version(self) -> str:
        """
        Generate new version string.
        
        Returns:
            Version string (timestamp-based)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"v{timestamp}"
    
    def save_version(
        self,
        model: PatternQualityModel,
        version: str | None = None,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Save model version.
        
        Args:
            model: Model to save
            version: Version string (auto-generated if None)
            metadata: Optional metadata (metrics, training info, etc.)
        
        Returns:
            Version string
        """
        if version is None:
            version = self._generate_version()
        
        # Save model file
        model_path = self.models_dir / f"model_{version}.joblib"
        model.save(model_path)
        
        # Save metadata
        version_metadata = {
            'version': version,
            'model_path': str(model_path),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metrics': model.metrics.copy() if model.metrics else {},
            'trained_at': model.trained_at.isoformat() if model.trained_at else None,
            'version_number': model.version,
        }
        
        if metadata:
            version_metadata.update(metadata)
        
        self._versions[version] = version_metadata
        self._save_versions()
        
        logger.info(f"Saved model version: {version}")
        return version
    
    def load_version(self, version: str) -> PatternQualityModel:
        """
        Load specific model version.
        
        Args:
            version: Version string
        
        Returns:
            Loaded model
        """
        if version not in self._versions:
            raise ValueError(f"Version {version} not found")
        
        version_metadata = self._versions[version]
        model_path = Path(version_metadata['model_path'])
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model = PatternQualityModel.load(model_path)
        logger.info(f"Loaded model version: {version}")
        return model
    
    def get_current_version(self) -> str | None:
        """
        Get current (latest) version.
        
        Returns:
            Latest version string or None
        """
        if not self._versions:
            return None
        
        # Sort by created_at (most recent first)
        sorted_versions = sorted(
            self._versions.items(),
            key=lambda x: x[1].get('created_at', ''),
            reverse=True
        )
        
        return sorted_versions[0][0] if sorted_versions else None
    
    def rollback(self, version: str, target_path: Path | str) -> bool:
        """
        Rollback to specific version (copy to target path).
        
        Args:
            version: Version to rollback to
            target_path: Path to copy model to (becomes current model)
        
        Returns:
            True if successful
        """
        try:
            model = self.load_version(version)
            target_path = Path(target_path)
            
            # Save to target path
            model.save(target_path)
            
            logger.info(f"Rolled back to version {version} at {target_path}")
            return True
        except Exception as e:
            logger.error(f"Error rolling back to version {version}: {e}", exc_info=True)
            return False
    
    def list_versions(self) -> list[dict[str, Any]]:
        """
        List all model versions.
        
        Returns:
            List of version metadata, sorted by created_at (newest first)
        """
        versions = list(self._versions.values())
        versions.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        return versions
    
    def delete_version(self, version: str) -> bool:
        """
        Delete a model version.
        
        Args:
            version: Version to delete
        
        Returns:
            True if successful
        """
        if version not in self._versions:
            return False
        
        try:
            version_metadata = self._versions[version]
            model_path = Path(version_metadata['model_path'])
            
            # Delete model file
            if model_path.exists():
                model_path.unlink()
            
            # Remove from versions
            del self._versions[version]
            self._save_versions()
            
            logger.info(f"Deleted model version: {version}")
            return True
        except Exception as e:
            logger.error(f"Error deleting version {version}: {e}", exc_info=True)
            return False
    
    def get_version_metadata(self, version: str) -> dict[str, Any] | None:
        """
        Get metadata for a specific version.
        
        Args:
            version: Version string
        
        Returns:
            Version metadata or None
        """
        return self._versions.get(version)

