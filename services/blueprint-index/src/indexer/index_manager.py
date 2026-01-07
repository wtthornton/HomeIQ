"""Index manager for coordinating blueprint indexing jobs."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import IndexedBlueprint, IndexingJob
from .blueprint_parser import BlueprintParser
from .discourse_indexer import DiscourseBlueprintIndexer
from .github_indexer import GitHubBlueprintIndexer

logger = logging.getLogger(__name__)


class IndexManager:
    """
    Manages blueprint indexing jobs.
    
    Coordinates GitHub and Discourse indexers,
    tracks job progress, and handles deduplication.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize index manager."""
        self.db = db
        self.parser = BlueprintParser()
    
    async def start_indexing_job(
        self,
        job_type: str = "full",
        force_refresh: bool = False,
    ) -> IndexingJob:
        """
        Start a new indexing job.
        
        Args:
            job_type: Type of job ('github', 'discourse', 'full')
            force_refresh: Force re-indexing even if recently indexed
            
        Returns:
            IndexingJob model
        """
        # Check for running jobs
        running_query = select(IndexingJob).where(IndexingJob.status == "running")
        running_result = await self.db.execute(running_query)
        running_job = running_result.scalar_one_or_none()
        
        if running_job:
            logger.warning(f"Indexing job already running: {running_job.id}")
            return running_job
        
        # Create new job
        job = IndexingJob(
            job_type=job_type,
            status="running",
            started_at=datetime.now(timezone.utc),
            config={"force_refresh": force_refresh},
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info(f"Started indexing job: {job.id} (type={job_type})")
        
        # Run indexing in background
        asyncio.create_task(self._run_indexing_job(job.id, job_type))
        
        return job
    
    async def _run_indexing_job(self, job_id: str, job_type: str):
        """Run indexing job asynchronously."""
        try:
            # Import here to get fresh session
            from ..database import get_db_context
            
            async with get_db_context() as db:
                # Get job
                job_query = select(IndexingJob).where(IndexingJob.id == job_id)
                job_result = await db.execute(job_query)
                job = job_result.scalar_one_or_none()
                
                if not job:
                    logger.error(f"Job not found: {job_id}")
                    return
                
                all_blueprints = []
                
                # Index from GitHub
                if job_type in ("github", "full"):
                    async with GitHubBlueprintIndexer() as github_indexer:
                        def github_progress(processed, total):
                            job.processed_items = processed
                            job.total_items = total
                        
                        github_blueprints = await github_indexer.index_all(
                            progress_callback=github_progress
                        )
                        all_blueprints.extend(github_blueprints)
                        logger.info(f"Indexed {len(github_blueprints)} from GitHub")
                
                # Index from Discourse
                if job_type in ("discourse", "full"):
                    async with DiscourseBlueprintIndexer() as discourse_indexer:
                        def discourse_progress(processed, total):
                            job.processed_items = len(all_blueprints) + processed
                            job.total_items = len(all_blueprints) + total
                        
                        discourse_blueprints = await discourse_indexer.index_all(
                            progress_callback=discourse_progress
                        )
                        all_blueprints.extend(discourse_blueprints)
                        logger.info(f"Indexed {len(discourse_blueprints)} from Discourse")
                
                # Store blueprints (with deduplication)
                stored_count = 0
                failed_count = 0
                
                for blueprint in all_blueprints:
                    try:
                        # Check for existing blueprint by source URL
                        existing_query = select(IndexedBlueprint).where(
                            IndexedBlueprint.source_url == blueprint.source_url
                        )
                        existing_result = await db.execute(existing_query)
                        existing = existing_result.scalar_one_or_none()
                        
                        if existing:
                            # Update existing
                            for key, value in blueprint.to_dict().items():
                                if key != "id" and value is not None:
                                    setattr(existing, key, value)
                            existing.indexed_at = datetime.now(timezone.utc)
                        else:
                            # Add new
                            db.add(blueprint)
                        
                        stored_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to store blueprint: {e}")
                        failed_count += 1
                
                await db.commit()
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.indexed_items = stored_count
                job.failed_items = failed_count
                job.total_items = len(all_blueprints)
                job.processed_items = len(all_blueprints)
                
                await db.commit()
                
                logger.info(
                    f"Indexing job completed: {job_id} "
                    f"(indexed={stored_count}, failed={failed_count})"
                )
                
        except Exception as e:
            logger.error(f"Indexing job failed: {job_id} - {e}", exc_info=True)
            
            # Mark job as failed
            try:
                from ..database import get_db_context
                
                async with get_db_context() as db:
                    job_query = select(IndexingJob).where(IndexingJob.id == job_id)
                    job_result = await db.execute(job_query)
                    job = job_result.scalar_one_or_none()
                    
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.now(timezone.utc)
                        job.error_message = str(e)
                        await db.commit()
                        
            except Exception as inner_e:
                logger.error(f"Failed to update job status: {inner_e}")
    
    async def get_job(self, job_id: str) -> Optional[IndexingJob]:
        """Get indexing job by ID."""
        query = select(IndexingJob).where(IndexingJob.id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_recent_jobs(self, limit: int = 10) -> list[IndexingJob]:
        """Get recent indexing jobs."""
        query = (
            select(IndexingJob)
            .order_by(IndexingJob.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running indexing job."""
        job = await self.get_job(job_id)
        
        if not job or job.status != "running":
            return False
        
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return True
