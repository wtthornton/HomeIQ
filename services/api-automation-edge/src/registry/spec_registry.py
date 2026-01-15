"""
Automation Spec Registry

Epic C2: Spec registry with versioning and immutable storage
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class SpecVersion(Base):
    """Database model for spec versions"""
    __tablename__ = "spec_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    spec_id = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    home_id = Column(String, index=True, nullable=False)
    spec_hash = Column(String, unique=True, nullable=False, index=True)
    spec_content = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    is_active = Column(String, default="false")  # "true" or "false" for SQLite compatibility
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "version": self.version,
            "home_id": self.home_id,
            "spec_hash": self.spec_hash,
            "spec_content": json.loads(self.spec_content),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "is_active": self.is_active == "true"
        }


class SpecRegistry:
    """
    Registry for automation specs with versioning and immutable storage.
    
    Features:
    - Store specs by home ID
    - Track deployed versions and history
    - Immutable artifact storage (hash-based)
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize spec registry.
        
        Args:
            database_url: Database URL (defaults to settings)
        """
        self.database_url = database_url or settings.database_url
        
        # Create engine and session
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        logger.info(f"Spec registry initialized with database: {self.database_url}")
    
    def _compute_hash(self, spec: Dict[str, Any]) -> str:
        """
        Compute hash for spec (for immutable storage).
        
        Args:
            spec: Spec dictionary
        
        Returns:
            SHA256 hash string
        """
        spec_str = json.dumps(spec, sort_keys=True)
        return hashlib.sha256(spec_str.encode()).hexdigest()
    
    def store_spec(
        self,
        spec: Dict[str, Any],
        home_id: str,
        deploy: bool = False
    ) -> Dict[str, Any]:
        """
        Store automation spec.
        
        Args:
            spec: Automation spec dictionary
            home_id: Home ID
            deploy: Whether to mark as active/deployed
        
        Returns:
            Stored spec version dictionary
        """
        spec_id = spec.get("id")
        version = spec.get("version")
        
        if not spec_id or not version:
            raise ValueError("Spec must have 'id' and 'version' fields")
        
        spec_hash = self._compute_hash(spec)
        spec_content = json.dumps(spec)
        
        db = self.SessionLocal()
        try:
            # Check if this exact spec already exists
            existing = db.query(SpecVersion).filter(
                SpecVersion.spec_hash == spec_hash
            ).first()
            
            if existing:
                logger.info(f"Spec {spec_id} v{version} already exists (hash: {spec_hash[:8]}...)")
                return existing.to_dict()
            
            # Deactivate previous versions if deploying
            if deploy:
                db.query(SpecVersion).filter(
                    SpecVersion.spec_id == spec_id,
                    SpecVersion.home_id == home_id
                ).update({"is_active": "false"})
            
            # Create new version
            spec_version = SpecVersion(
                spec_id=spec_id,
                version=version,
                home_id=home_id,
                spec_hash=spec_hash,
                spec_content=spec_content,
                deployed_at=datetime.utcnow() if deploy else None,
                is_active="true" if deploy else "false"
            )
            
            db.add(spec_version)
            db.commit()
            db.refresh(spec_version)
            
            logger.info(f"Stored spec {spec_id} v{version} for home {home_id} (hash: {spec_hash[:8]}...)")
            return spec_version.to_dict()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store spec: {e}")
            raise
        finally:
            db.close()
    
    def get_spec(
        self,
        spec_id: str,
        home_id: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get automation spec.
        
        Args:
            spec_id: Spec ID
            home_id: Home ID
            version: Optional version (defaults to active version)
        
        Returns:
            Spec dictionary or None if not found
        """
        db = self.SessionLocal()
        try:
            query = db.query(SpecVersion).filter(
                SpecVersion.spec_id == spec_id,
                SpecVersion.home_id == home_id
            )
            
            if version:
                query = query.filter(SpecVersion.version == version)
            else:
                query = query.filter(SpecVersion.is_active == "true")
            
            spec_version = query.first()
            
            if spec_version:
                return json.loads(spec_version.spec_content)
            return None
            
        finally:
            db.close()
    
    def get_spec_history(
        self,
        spec_id: str,
        home_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get spec version history.
        
        Args:
            spec_id: Spec ID
            home_id: Home ID
        
        Returns:
            List of spec version dictionaries (sorted by created_at desc)
        """
        db = self.SessionLocal()
        try:
            versions = db.query(SpecVersion).filter(
                SpecVersion.spec_id == spec_id,
                SpecVersion.home_id == home_id
            ).order_by(SpecVersion.created_at.desc()).all()
            
            return [v.to_dict() for v in versions]
        finally:
            db.close()
    
    def get_active_specs(self, home_id: str) -> List[Dict[str, Any]]:
        """
        Get all active specs for a home.
        
        Args:
            home_id: Home ID
        
        Returns:
            List of active spec dictionaries
        """
        db = self.SessionLocal()
        try:
            versions = db.query(SpecVersion).filter(
                SpecVersion.home_id == home_id,
                SpecVersion.is_active == "true"
            ).all()
            
            return [json.loads(v.spec_content) for v in versions]
        finally:
            db.close()
    
    def deploy_spec(
        self,
        spec_id: str,
        home_id: str,
        version: str
    ) -> bool:
        """
        Deploy a specific spec version (mark as active).
        
        Args:
            spec_id: Spec ID
            home_id: Home ID
            version: Version to deploy
        
        Returns:
            True if deployment successful
        """
        db = self.SessionLocal()
        try:
            # Deactivate all versions of this spec
            db.query(SpecVersion).filter(
                SpecVersion.spec_id == spec_id,
                SpecVersion.home_id == home_id
            ).update({"is_active": "false"})
            
            # Activate specified version
            result = db.query(SpecVersion).filter(
                SpecVersion.spec_id == spec_id,
                SpecVersion.home_id == home_id,
                SpecVersion.version == version
            ).update({
                "is_active": "true",
                "deployed_at": datetime.utcnow()
            })
            
            db.commit()
            
            if result > 0:
                logger.info(f"Deployed spec {spec_id} v{version} for home {home_id}")
                return True
            else:
                logger.warning(f"Spec {spec_id} v{version} not found for home {home_id}")
                return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to deploy spec: {e}")
            return False
        finally:
            db.close()
    
    def get_last_known_good(
        self,
        spec_id: str,
        home_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get last known good version (most recently deployed).
        
        Args:
            spec_id: Spec ID
            home_id: Home ID
        
        Returns:
            Spec dictionary or None
        """
        db = self.SessionLocal()
        try:
            version = db.query(SpecVersion).filter(
                SpecVersion.spec_id == spec_id,
                SpecVersion.home_id == home_id,
                SpecVersion.deployed_at.isnot(None)
            ).order_by(SpecVersion.deployed_at.desc()).first()
            
            if version:
                return json.loads(version.spec_content)
            return None
        finally:
            db.close()
