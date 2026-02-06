"""Backup and restore capabilities for data retention service."""

import asyncio
import collections
import json
import logging
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class BackupInfo:
    """Backup information."""

    backup_id: str
    backup_type: str
    created_at: datetime
    size_bytes: int
    file_path: str
    metadata: dict[str, Any]
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert backup info to dictionary."""
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "file_path": self.file_path,
            "metadata": self.metadata,
            "success": self.success,
            "error_message": self.error_message
        }

ALLOWED_CONFIG_FILES = {"config.yaml", ".env", "influxdb.conf"}


def _safe_extract(tar: tarfile.TarFile, path: str | Path) -> None:
    """Safely extract tar archive, preventing path traversal (Zip Slip)."""
    abs_target = os.path.realpath(str(path))
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        abs_path = os.path.realpath(member_path)
        if not abs_path.startswith(abs_target + os.sep) and abs_path != abs_target:
            raise ValueError(f"Path traversal detected in archive: {member.name}")
    tar.extractall(path, filter='data')


class BackupRestoreService:
    """Service for backup and restore operations."""

    def __init__(self, influxdb_client=None, backup_dir: str = "/backups"):
        """
        Initialize backup restore service.
        
        Args:
            influxdb_client: InfluxDB client for data operations
            backup_dir: Directory for storing backups
        """
        self.influxdb_client = influxdb_client
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.backup_history: collections.deque[BackupInfo] = collections.deque(maxlen=1000)
        self.is_running = False
        self.backup_task: asyncio.Task | None = None

        logger.info(f"Backup restore service initialized with backup directory: {self.backup_dir}")

    async def start(self) -> None:
        """Start the backup service."""
        if self.is_running:
            logger.warning("Backup service is already running")
            return

        self.is_running = True
        logger.info("Backup restore service started")

    async def stop(self) -> None:
        """Stop the backup service."""
        if not self.is_running:
            return

        self.is_running = False

        if self.backup_task and not self.backup_task.done():
            self.backup_task.cancel()
            try:
                await self.backup_task
            except asyncio.CancelledError:
                pass

        logger.info("Backup restore service stopped")

    async def create_backup(self, backup_type: str = "full",
                          include_data: bool = True,
                          include_config: bool = True,
                          include_logs: bool = False) -> BackupInfo:
        """
        Create a backup.
        
        Args:
            backup_type: Type of backup (full, incremental, config)
            include_data: Whether to include data
            include_config: Whether to include configuration
            include_logs: Whether to include logs
            
        Returns:
            BackupInfo: Information about the created backup
        """
        backup_id = f"{backup_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        backup_file = self.backup_dir / f"{backup_id}.tar.gz"

        try:
            logger.info(f"Creating {backup_type} backup: {backup_id}")

            # Create temporary directory for backup contents
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Collect backup contents
                metadata = {
                    "backup_type": backup_type,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "include_data": include_data,
                    "include_config": include_config,
                    "include_logs": include_logs
                }

                # Add data if requested
                if include_data:
                    await self._backup_data(temp_path, metadata)

                # Add configuration if requested
                if include_config:
                    await self._backup_config(temp_path, metadata)

                # Add logs if requested
                if include_logs:
                    await self._backup_logs(temp_path, metadata)

                # Create backup metadata file
                metadata_file = temp_path / "backup_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)

                # Create compressed archive
                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(temp_path, arcname=".")

                # Get backup size
                backup_size = backup_file.stat().st_size

            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=datetime.now(timezone.utc),
                size_bytes=backup_size,
                file_path=str(backup_file),
                metadata=metadata,
                success=True
            )

            self.backup_history.append(backup_info)

            logger.info(f"Backup created successfully: {backup_id} ({backup_size} bytes)")
            return backup_info

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")

            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=datetime.now(timezone.utc),
                size_bytes=0,
                file_path=str(backup_file),
                metadata={},
                success=False,
                error_message=str(e)
            )

            self.backup_history.append(backup_info)
            return backup_info

    async def _backup_data(self, backup_path: Path, metadata: dict[str, Any]) -> None:
        """
        Backup data from InfluxDB.
        
        Args:
            backup_path: Path to store backup files
            metadata: Backup metadata dictionary
        """
        if not self.influxdb_client:
            # Mock implementation for testing
            data_file = backup_path / "data_export.json"
            mock_data = {
                "events": [
                    {"timestamp": "2024-01-01T00:00:00Z", "entity_id": "sensor.temp", "value": 20.5},
                    {"timestamp": "2024-01-01T01:00:00Z", "entity_id": "sensor.humidity", "value": 65}
                ]
            }

            with open(data_file, 'w') as f:
                json.dump(mock_data, f, indent=2)

            metadata["data_records"] = len(mock_data["events"])
            return

        try:
            # Export data from InfluxDB
            data_file = backup_path / "data_export.json"

            # Query all data from the last year
            query = """
            from(bucket: "home-assistant-events")
                |> range(start: -1y)
                |> limit(n: 100000)
            """

            result = await self.influxdb_client.query(query)
            exported_data = []

            for table in result:
                for record in table.records:
                    exported_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "tags": record.values
                    })

            with open(data_file, 'w') as f:
                json.dump({"events": exported_data}, f, indent=2)

            metadata["data_records"] = len(exported_data)
            logger.info(f"Backed up {len(exported_data)} data records")

        except Exception as e:
            logger.error(f"Data backup failed: {e}")
            metadata["data_error"] = str(e)

    async def _backup_config(self, backup_path: Path, metadata: dict[str, Any]) -> None:
        """
        Backup configuration files.
        
        Args:
            backup_path: Path to store backup files
            metadata: Backup metadata dictionary
        """
        try:
            config_dir = backup_path / "config"
            config_dir.mkdir(exist_ok=True)

            # Copy configuration files
            config_files = [
                "/app/config.yaml",
                "/app/.env",
                "/etc/influxdb/influxdb.conf"
            ]

            copied_files = []
            for config_file in config_files:
                if os.path.exists(config_file):
                    dest_file = config_dir / os.path.basename(config_file)
                    shutil.copy2(config_file, dest_file)
                    copied_files.append(config_file)

            metadata["config_files"] = copied_files
            logger.info(f"Backed up {len(copied_files)} configuration files")

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            metadata["config_error"] = str(e)

    async def _backup_logs(self, backup_path: Path, metadata: dict[str, Any]) -> None:
        """
        Backup log files.
        
        Args:
            backup_path: Path to store backup files
            metadata: Backup metadata dictionary
        """
        try:
            logs_dir = backup_path / "logs"
            logs_dir.mkdir(exist_ok=True)

            # Copy log files
            log_dirs = ["/var/log", "/app/logs"]
            copied_logs = []

            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            if file.endswith('.log'):
                                src_file = os.path.join(root, file)
                                rel_path = os.path.relpath(src_file, log_dir)
                                dest_file = logs_dir / rel_path
                                dest_file.parent.mkdir(parents=True, exist_ok=True)

                                shutil.copy2(src_file, dest_file)
                                copied_logs.append(src_file)

            metadata["log_files"] = copied_logs
            logger.info(f"Backed up {len(copied_logs)} log files")

        except Exception as e:
            logger.error(f"Log backup failed: {e}")
            metadata["log_error"] = str(e)

    async def restore_backup(self, backup_id: str, restore_data: bool = True,
                           restore_config: bool = True, restore_logs: bool = False) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_id: ID of backup to restore
            restore_data: Whether to restore data
            restore_config: Whether to restore configuration
            restore_logs: Whether to restore logs
            
        Returns:
            bool: True if restore was successful
        """
        try:
            # Find backup file
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            logger.info(f"Restoring backup: {backup_id}")

            # Extract backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                with tarfile.open(backup_file, "r:gz") as tar:
                    _safe_extract(tar, temp_path)

                # Read backup metadata
                metadata_file = temp_path / "backup_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                else:
                    metadata = {}

                # Restore data if requested
                if restore_data and metadata.get("include_data", False):
                    await self._restore_data(temp_path)

                # Restore configuration if requested
                if restore_config and metadata.get("include_config", False):
                    await self._restore_config(temp_path)

                # Restore logs if requested
                if restore_logs and metadata.get("include_logs", False):
                    await self._restore_logs(temp_path)

            logger.info(f"Backup restored successfully: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            return False

    async def _restore_data(self, backup_path: Path) -> None:
        """
        Restore data to InfluxDB.
        
        Args:
            backup_path: Path containing backup files
        """
        data_file = backup_path / "data_export.json"
        if not data_file.exists():
            logger.warning("No data file found in backup")
            return

        if not self.influxdb_client:
            logger.info("Mock data restore completed")
            return

        try:
            with open(data_file) as f:
                data = json.load(f)

            events = data.get("events", [])

            # Import data to InfluxDB
            from influxdb_client import Point, WritePrecision

            points = []
            for event in events:
                point = Point("home_assistant_event") \
                    .time(event["timestamp"], WritePrecision.NS) \
                    .field(event["field"], event["value"])

                # Add tags
                for tag_key, tag_value in event.get("tags", {}).items():
                    point.tag(tag_key, str(tag_value))

                points.append(point)

            # Write points to InfluxDB (new API: no write_api(), no bucket parameter)
            await self.influxdb_client.write(
                record=points
            )

            logger.info(f"Restored {len(events)} data records")

        except Exception as e:
            logger.error(f"Data restore failed: {e}")

    async def _restore_config(self, backup_path: Path) -> None:
        """
        Restore configuration files.
        
        Args:
            backup_path: Path containing backup files
        """
        config_dir = backup_path / "config"
        if not config_dir.exists():
            logger.warning("No config directory found in backup")
            return

        try:
            # Restore configuration files (whitelist only)
            for config_file in config_dir.iterdir():
                if config_file.is_file():
                    if config_file.name not in ALLOWED_CONFIG_FILES:
                        logger.warning(f"Skipping unrecognized config file: {config_file.name}")
                        continue
                    dest_path = Path("/app") / config_file.name
                    # Verify path doesn't escape target directory
                    if not dest_path.resolve().is_relative_to(Path("/app").resolve()):
                        logger.warning(f"Skipping suspicious config file: {config_file.name}")
                        continue
                    shutil.copy2(config_file, dest_path)
                    logger.info(f"Restored config file: {config_file.name}")

        except Exception as e:
            logger.error(f"Configuration restore failed: {e}")

    async def _restore_logs(self, backup_path: Path) -> None:
        """
        Restore log files.
        
        Args:
            backup_path: Path containing backup files
        """
        logs_dir = backup_path / "logs"
        if not logs_dir.exists():
            logger.warning("No logs directory found in backup")
            return

        try:
            # Restore log files
            for log_file in logs_dir.rglob("*.log"):
                if log_file.is_file():
                    dest_path = f"/var/log/{log_file.relative_to(logs_dir)}"
                    dest_path_obj = Path(dest_path)
                    dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(log_file, dest_path_obj)
                    logger.info(f"Restored log file: {log_file.name}")

        except Exception as e:
            logger.error(f"Log restore failed: {e}")

    async def schedule_backups(self, interval_hours: int = 24,
                             backup_type: str = "full") -> None:
        """
        Schedule periodic backups.
        
        Args:
            interval_hours: Interval between backups in hours
            backup_type: Type of backup to create
        """
        if self.backup_task and not self.backup_task.done():
            logger.warning("Backup task is already running")
            return

        async def backup_loop():
            while self.is_running:
                try:
                    logger.info("Starting scheduled backup")
                    backup_info = await self.create_backup(backup_type)

                    if backup_info.success:
                        logger.info(f"Scheduled backup completed: {backup_info.backup_id}")
                    else:
                        logger.error(f"Scheduled backup failed: {backup_info.error_message}")

                except Exception as e:
                    logger.error(f"Scheduled backup failed: {e}")

                # Wait for next backup
                await asyncio.sleep(interval_hours * 3600)

        self.backup_task = asyncio.create_task(backup_loop())
        logger.info(f"Scheduled {backup_type} backups every {interval_hours} hours")

    def get_backup_history(self, limit: int = 100) -> list[BackupInfo]:
        """
        Get backup history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of backup information
        """
        return list(self.backup_history)[-limit:] if self.backup_history else []

    def get_backup_statistics(self) -> dict[str, Any]:
        """
        Get backup statistics.
        
        Returns:
            Dictionary containing backup statistics
        """
        if not self.backup_history:
            return {
                "total_backups": 0,
                "successful_backups": 0,
                "failed_backups": 0,
                "total_size_bytes": 0,
                "average_size_bytes": 0,
                "success_rate": 0,
                "last_backup": None
            }

        successful_backups = [backup for backup in self.backup_history if backup.success]
        failed_backups = [backup for backup in self.backup_history if not backup.success]

        total_size = sum(backup.size_bytes for backup in successful_backups)

        return {
            "total_backups": len(self.backup_history),
            "successful_backups": len(successful_backups),
            "failed_backups": len(failed_backups),
            "total_size_bytes": total_size,
            "average_size_bytes": total_size / len(successful_backups) if successful_backups else 0,
            "success_rate": len(successful_backups) / len(self.backup_history) if self.backup_history else 0,
            "last_backup": self.backup_history[-1].created_at.isoformat() if self.backup_history else None
        }

    def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
        """
        Clean up old backup files.
        
        Args:
            days_to_keep: Number of days of backups to keep
            
        Returns:
            Number of backup files deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        deleted_count = 0

        try:
            for backup_file in self.backup_dir.glob("*.tar.gz"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup_file.name}")

            logger.info(f"Cleaned up {deleted_count} old backup files")

        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

        return deleted_count
