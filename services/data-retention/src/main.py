"""Main data retention service."""

import logging
import asyncio
import os
from typing import Optional
from aiohttp import web

from .retention_policy import RetentionPolicyManager, RetentionPolicy, RetentionPeriod
from .data_cleanup import DataCleanupService
from .storage_monitor import StorageMonitor
from .data_compression import DataCompressionService
from .backup_restore import BackupRestoreService

logger = logging.getLogger(__name__)

class DataRetentionService:
    """Main data retention and storage management service."""
    
    def __init__(self):
        """Initialize data retention service."""
        self.policy_manager = RetentionPolicyManager()
        self.cleanup_service: Optional[DataCleanupService] = None
        self.storage_monitor: Optional[StorageMonitor] = None
        self.compression_service: Optional[DataCompressionService] = None
        self.backup_service: Optional[BackupRestoreService] = None
        
        # Configuration
        self.cleanup_interval_hours = int(os.getenv('CLEANUP_INTERVAL_HOURS', '24'))
        self.monitoring_interval_minutes = int(os.getenv('MONITORING_INTERVAL_MINUTES', '5'))
        self.compression_interval_hours = int(os.getenv('COMPRESSION_INTERVAL_HOURS', '24'))
        self.backup_interval_hours = int(os.getenv('BACKUP_INTERVAL_HOURS', '24'))
        self.backup_dir = os.getenv('BACKUP_DIR', '/backups')
        
        logger.info("Data retention service initialized")
    
    async def start(self) -> None:
        """Start the data retention service."""
        logger.info("Starting data retention service...")
        
        # Initialize services
        self.cleanup_service = DataCleanupService()
        self.storage_monitor = StorageMonitor()
        self.compression_service = DataCompressionService()
        self.backup_service = BackupRestoreService(backup_dir=self.backup_dir)
        
        # Start services
        await self.cleanup_service.start()
        await self.storage_monitor.start()
        await self.compression_service.start()
        await self.backup_service.start()
        
        # Schedule periodic tasks
        await self.cleanup_service.schedule_cleanup(self.cleanup_interval_hours)
        await self.storage_monitor.schedule_monitoring(self.monitoring_interval_minutes)
        await self.compression_service.schedule_compression(self.compression_interval_hours)
        await self.backup_service.schedule_backups(self.backup_interval_hours)
        
        logger.info("Data retention service started")
    
    async def stop(self) -> None:
        """Stop the data retention service."""
        logger.info("Stopping data retention service...")
        
        if self.cleanup_service:
            await self.cleanup_service.stop()
        
        if self.storage_monitor:
            await self.storage_monitor.stop()
        
        if self.compression_service:
            await self.compression_service.stop()
        
        if self.backup_service:
            await self.backup_service.stop()
        
        logger.info("Data retention service stopped")
    
    def get_service_status(self) -> dict:
        """Get service status."""
        return {
            "cleanup_service": self.cleanup_service is not None,
            "storage_monitor": self.storage_monitor is not None,
            "compression_service": self.compression_service is not None,
            "backup_service": self.backup_service is not None,
            "policy_count": len(self.policy_manager.get_all_policies())
        }
    
    def get_retention_policies(self) -> list:
        """Get all retention policies."""
        return [policy.to_dict() for policy in self.policy_manager.get_all_policies()]
    
    def add_retention_policy(self, policy_data: dict) -> None:
        """Add a new retention policy."""
        policy = RetentionPolicy(
            name=policy_data["name"],
            description=policy_data["description"],
            retention_period=policy_data["retention_period"],
            retention_unit=RetentionPeriod(policy_data["retention_unit"]),
            enabled=policy_data.get("enabled", True)
        )
        
        self.policy_manager.add_policy(policy)
    
    def update_retention_policy(self, policy_data: dict) -> None:
        """Update an existing retention policy."""
        policy = RetentionPolicy(
            name=policy_data["name"],
            description=policy_data["description"],
            retention_period=policy_data["retention_period"],
            retention_unit=RetentionPeriod(policy_data["retention_unit"]),
            enabled=policy_data.get("enabled", True)
        )
        
        self.policy_manager.update_policy(policy)
    
    def remove_retention_policy(self, policy_name: str) -> None:
        """Remove a retention policy."""
        self.policy_manager.remove_policy(policy_name)
    
    async def run_cleanup(self, policy_name: Optional[str] = None) -> list:
        """Run data cleanup."""
        if not self.cleanup_service:
            raise RuntimeError("Cleanup service not initialized")
        
        return [result.to_dict() for result in await self.cleanup_service.run_cleanup(policy_name)]
    
    def get_storage_metrics(self) -> Optional[dict]:
        """Get current storage metrics."""
        if not self.storage_monitor:
            return None
        
        metrics = self.storage_monitor.get_current_metrics()
        return metrics.to_dict() if metrics else None
    
    def get_storage_alerts(self) -> list:
        """Get active storage alerts."""
        if not self.storage_monitor:
            return []
        
        return [alert.to_dict() for alert in self.storage_monitor.get_active_alerts()]
    
    def get_compression_statistics(self) -> dict:
        """Get compression statistics."""
        if not self.compression_service:
            return {}
        
        return self.compression_service.get_compression_statistics()
    
    async def create_backup(self, backup_type: str = "full", 
                          include_data: bool = True,
                          include_config: bool = True,
                          include_logs: bool = False) -> dict:
        """Create a backup."""
        if not self.backup_service:
            raise RuntimeError("Backup service not initialized")
        
        backup_info = await self.backup_service.create_backup(
            backup_type=backup_type,
            include_data=include_data,
            include_config=include_config,
            include_logs=include_logs
        )
        
        return backup_info.to_dict()
    
    async def restore_backup(self, backup_id: str, restore_data: bool = True,
                           restore_config: bool = True, restore_logs: bool = False) -> bool:
        """Restore from a backup."""
        if not self.backup_service:
            raise RuntimeError("Backup service not initialized")
        
        return await self.backup_service.restore_backup(
            backup_id=backup_id,
            restore_data=restore_data,
            restore_config=restore_config,
            restore_logs=restore_logs
        )
    
    def get_backup_history(self, limit: int = 100) -> list:
        """Get backup history."""
        if not self.backup_service:
            return []
        
        return [backup.to_dict() for backup in self.backup_service.get_backup_history(limit)]
    
    def get_backup_statistics(self) -> dict:
        """Get backup statistics."""
        if not self.backup_service:
            return {}
        
        return self.backup_service.get_backup_statistics()
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """Clean up old backup files."""
        if not self.backup_service:
            return 0
        
        return self.backup_service.cleanup_old_backups(days_to_keep)
    
    def get_service_statistics(self) -> dict:
        """Get comprehensive service statistics."""
        stats = {
            "service_status": self.get_service_status(),
            "policy_statistics": self.policy_manager.get_policy_statistics()
        }
        
        if self.cleanup_service:
            stats["cleanup_statistics"] = self.cleanup_service.get_cleanup_statistics()
        
        if self.storage_monitor:
            stats["storage_statistics"] = self.storage_monitor.get_storage_statistics()
        
        if self.compression_service:
            stats["compression_statistics"] = self.compression_service.get_compression_statistics()
        
        if self.backup_service:
            stats["backup_statistics"] = self.backup_service.get_backup_statistics()
        
        return stats

# Global service instance
data_retention_service = DataRetentionService()

async def health_check_handler(request: web.Request) -> web.Response:
    """Simple health check handler."""
    try:
        # Get basic service status
        service_status = data_retention_service.get_service_status()
        
        health_data = {
            "status": "healthy",
            "timestamp": data_retention_service.get_service_status().get("timestamp", "unknown"),
            "service": "data-retention",
            "uptime": service_status.get("uptime_seconds", 0)
        }
        
        return web.json_response(health_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response(
            {
                "status": "error",
                "timestamp": "unknown",
                "error": str(e)
            },
            status=500
        )

async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Start the data retention service
        await data_retention_service.start()
        
        # Create and start the web application
        app = web.Application()
        
        # Add health check route
        app.router.add_get('/health', health_check_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Get port from environment
        port = int(os.getenv('PORT', '8080'))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"Data retention service started on port {port}")
        
        # Keep service running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        await data_retention_service.stop()

if __name__ == "__main__":
    asyncio.run(main())
