"""Health check endpoint for data retention service."""

import logging
from datetime import datetime

from aiohttp import web

from .main import data_retention_service

logger = logging.getLogger(__name__)

async def health_check(request: web.Request) -> web.Response:
    """
    Health check endpoint.

    Returns:
        web.Response: Health status response
    """
    try:
        # Get service status
        service_status = data_retention_service.get_service_status()

        # Get storage metrics
        storage_metrics = data_retention_service.get_storage_metrics()

        # Get active alerts
        storage_alerts = data_retention_service.get_storage_alerts()

        # Determine overall health
        overall_status = "healthy"
        if storage_alerts:
            critical_alerts = [alert for alert in storage_alerts if alert["severity"] == "critical"]
            overall_status = "critical" if critical_alerts else "warning"

        health_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service_status": service_status,
            "storage_metrics": storage_metrics,
            "active_alerts": len(storage_alerts),
            "alerts": storage_alerts,
        }

        return web.json_response(health_data)

    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return web.json_response(
            {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            },
            status=500,
        )

async def get_statistics(request: web.Request) -> web.Response:
    """
    Get service statistics.

    Returns:
        web.Response: Statistics response
    """
    try:
        stats = data_retention_service.get_service_statistics()
        return web.json_response(stats)

    except Exception as e:
        logger.exception(f"Statistics request failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def get_policies(request: web.Request) -> web.Response:
    """
    Get retention policies.

    Returns:
        web.Response: Policies response
    """
    try:
        policies = data_retention_service.get_retention_policies()
        return web.json_response({"policies": policies})

    except Exception as e:
        logger.exception(f"Policies request failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def add_policy(request: web.Request) -> web.Response:
    """
    Add a new retention policy.

    Returns:
        web.Response: Success response
    """
    try:
        data = await request.json()
        data_retention_service.add_retention_policy(data)

        return web.json_response(
            {"message": "Policy added successfully"},
            status=201,
        )

    except Exception as e:
        logger.exception(f"Add policy failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=400,
        )

async def update_policy(request: web.Request) -> web.Response:
    """
    Update an existing retention policy.

    Returns:
        web.Response: Success response
    """
    try:
        data = await request.json()
        data_retention_service.update_retention_policy(data)

        return web.json_response(
            {"message": "Policy updated successfully"},
        )

    except Exception as e:
        logger.exception(f"Update policy failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=400,
        )

async def delete_policy(request: web.Request) -> web.Response:
    """
    Delete a retention policy.

    Returns:
        web.Response: Success response
    """
    try:
        policy_name = request.match_info["policy_name"]
        data_retention_service.remove_retention_policy(policy_name)

        return web.json_response(
            {"message": "Policy deleted successfully"},
        )

    except Exception as e:
        logger.exception(f"Delete policy failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=400,
        )

async def run_cleanup(request: web.Request) -> web.Response:
    """
    Run data cleanup.

    Returns:
        web.Response: Cleanup results
    """
    try:
        policy_name = request.query.get("policy_name")
        results = await data_retention_service.run_cleanup(policy_name)

        return web.json_response({"results": results})

    except Exception as e:
        logger.exception(f"Run cleanup failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def create_backup(request: web.Request) -> web.Response:
    """
    Create a backup.

    Returns:
        web.Response: Backup information
    """
    try:
        data = await request.json()
        backup_info = await data_retention_service.create_backup(
            backup_type=data.get("backup_type", "full"),
            include_data=data.get("include_data", True),
            include_config=data.get("include_config", True),
            include_logs=data.get("include_logs", False),
        )

        return web.json_response(backup_info, status=201)

    except Exception as e:
        logger.exception(f"Create backup failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def restore_backup(request: web.Request) -> web.Response:
    """
    Restore from a backup.

    Returns:
        web.Response: Restore result
    """
    try:
        data = await request.json()
        backup_id = data.get("backup_id")

        if not backup_id:
            return web.json_response(
                {"error": "backup_id is required"},
                status=400,
            )

        success = await data_retention_service.restore_backup(
            backup_id=backup_id,
            restore_data=data.get("restore_data", True),
            restore_config=data.get("restore_config", True),
            restore_logs=data.get("restore_logs", False),
        )

        if success:
            return web.json_response({"message": "Backup restored successfully"})
        return web.json_response(
            {"error": "Backup restore failed"},
            status=500,
        )

    except Exception as e:
        logger.exception(f"Restore backup failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def get_backup_history(request: web.Request) -> web.Response:
    """
    Get backup history.

    Returns:
        web.Response: Backup history
    """
    try:
        limit = int(request.query.get("limit", 100))
        history = data_retention_service.get_backup_history(limit)

        return web.json_response({"backups": history})

    except Exception as e:
        logger.exception(f"Get backup history failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def get_backup_statistics(request: web.Request) -> web.Response:
    """
    Get backup statistics.

    Returns:
        web.Response: Backup statistics
    """
    try:
        stats = data_retention_service.get_backup_statistics()
        return web.json_response(stats)

    except Exception as e:
        logger.exception(f"Get backup statistics failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

async def cleanup_old_backups(request: web.Request) -> web.Response:
    """
    Clean up old backup files.

    Returns:
        web.Response: Cleanup result
    """
    try:
        days_to_keep = int(request.query.get("days_to_keep", 30))
        deleted_count = data_retention_service.cleanup_old_backups(days_to_keep)

        return web.json_response({
            "message": f"Cleaned up {deleted_count} old backup files",
            "deleted_count": deleted_count,
        })

    except Exception as e:
        logger.exception(f"Cleanup old backups failed: {e}")
        return web.json_response(
            {"error": str(e)},
            status=500,
        )

def create_app() -> web.Application:
    """
    Create web application with routes.

    Returns:
        web.Application: Configured web application
    """
    app = web.Application()

    # Health check routes
    app.router.add_get("/health", health_check)
    app.router.add_get("/stats", get_statistics)

    # Policy management routes
    app.router.add_get("/policies", get_policies)
    app.router.add_post("/policies", add_policy)
    app.router.add_put("/policies", update_policy)
    app.router.add_delete("/policies/{policy_name}", delete_policy)

    # Cleanup routes
    app.router.add_post("/cleanup", run_cleanup)

    # Backup and restore routes
    app.router.add_post("/backup", create_backup)
    app.router.add_post("/restore", restore_backup)
    app.router.add_get("/backups", get_backup_history)
    app.router.add_get("/backup-stats", get_backup_statistics)
    app.router.add_delete("/backups/cleanup", cleanup_old_backups)

    return app
