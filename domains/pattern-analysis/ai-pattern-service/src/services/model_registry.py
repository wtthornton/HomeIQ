"""Model registry for ML pattern detectors. Story 40.7."""
import logging
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import MLModel

logger = logging.getLogger(__name__)

MODEL_STORAGE_DIR = Path("/app/data/models")


class ModelRegistry:
    """Simple model registry for managing trained ML models."""

    def __init__(self, db: AsyncSession, storage_dir: Path | None = None):
        self.db = db
        self.storage_dir = storage_dir or MODEL_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def register_model(
        self,
        model_name: str,
        version: str,
        file_path: str,
        metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Register a trained model in the registry."""
        # Store model file in versioned directory
        dest_dir = self.storage_dir / model_name / version
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / Path(file_path).name

        if Path(file_path).exists() and str(file_path) != str(dest_path):
            shutil.copy2(file_path, dest_path)

        model = MLModel(
            model_name=model_name,
            version=version,
            file_path=str(dest_path),
            metrics=metrics or {},
            metadata_=metadata or {},
            is_active=True,
        )
        self.db.add(model)

        # Deactivate previous versions
        stmt = select(MLModel).where(
            MLModel.model_name == model_name,
            MLModel.version != version,
            MLModel.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        for old_model in result.scalars().all():
            old_model.is_active = False

        await self.db.flush()
        logger.info("Registered model %s v%s at %s", model_name, version, dest_path)
        return model.id

    async def get_active_model(self, model_name: str) -> dict[str, Any] | None:
        """Get the currently active model version."""
        stmt = (
            select(MLModel)
            .where(
                MLModel.model_name == model_name,
                MLModel.is_active == True,  # noqa: E712
            )
            .order_by(MLModel.trained_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return {
            "id": model.id,
            "model_name": model.model_name,
            "version": model.version,
            "file_path": model.file_path,
            "metrics": model.metrics,
            "trained_at": model.trained_at.isoformat(),
            "is_active": model.is_active,
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """List all registered models with metrics."""
        stmt = select(MLModel).order_by(MLModel.model_name, MLModel.trained_at.desc())
        result = await self.db.execute(stmt)
        return [
            {
                "id": m.id,
                "model_name": m.model_name,
                "version": m.version,
                "metrics": m.metrics,
                "trained_at": m.trained_at.isoformat(),
                "is_active": m.is_active,
            }
            for m in result.scalars().all()
        ]

    async def rollback(self, model_name: str, target_version: str) -> bool:
        """Rollback to a previous model version."""
        # Deactivate current
        stmt = select(MLModel).where(
            MLModel.model_name == model_name,
            MLModel.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        for m in result.scalars().all():
            m.is_active = False

        # Activate target
        stmt = select(MLModel).where(
            MLModel.model_name == model_name,
            MLModel.version == target_version,
        )
        result = await self.db.execute(stmt)
        target = result.scalar_one_or_none()
        if not target:
            return False
        target.is_active = True
        await self.db.flush()
        logger.info("Rolled back %s to v%s", model_name, target_version)
        return True
