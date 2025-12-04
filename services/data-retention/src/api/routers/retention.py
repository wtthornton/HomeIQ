"""
Retention operations router for data-retention service.
"""

from fastapi import APIRouter, HTTPException, Request

from ..models import RetentionStatsResponse, RetentionOperationResponse

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get("/stats", response_model=RetentionStatsResponse)
async def get_stats(request: Request):
    """
    Get storage metrics.
    
    Returns current storage metrics and analytics.
    """
    try:
        service = request.app.state.service
        if not service.analytics:
            raise HTTPException(status_code=503, detail={"error": "Analytics service not available"})
        
        metrics = await service.analytics.calculate_storage_metrics()
        return {"metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/downsample-hourly", response_model=RetentionOperationResponse)
async def downsample_hourly(request: Request):
    """
    Manually trigger hourly downsampling.
    
    Executes hot to warm tier downsampling operation.
    """
    try:
        service = request.app.state.service
        if not service.retention_manager:
            raise HTTPException(status_code=503, detail={"error": "Retention manager not available"})
        
        result = await service.retention_manager.downsample_hot_to_warm()
        return {
            "success": True,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/downsample-daily", response_model=RetentionOperationResponse)
async def downsample_daily(request: Request):
    """
    Manually trigger daily downsampling.
    
    Executes warm to cold tier downsampling operation.
    """
    try:
        service = request.app.state.service
        if not service.retention_manager:
            raise HTTPException(status_code=503, detail={"error": "Retention manager not available"})
        
        result = await service.retention_manager.downsample_warm_to_cold()
        return {
            "success": True,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/archive-s3", response_model=RetentionOperationResponse)
async def archive_s3(request: Request):
    """
    Manually trigger S3 archival.
    
    Executes archival operation to move data to S3 storage.
    """
    try:
        service = request.app.state.service
        if not service.archival_manager:
            raise HTTPException(status_code=503, detail={"error": "Archival manager not available"})
        
        result = await service.archival_manager.archive_to_s3()
        return {
            "success": True,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/refresh-views", response_model=RetentionOperationResponse)
async def refresh_views(request: Request):
    """
    Manually trigger view refresh.
    
    Refreshes all materialized views.
    """
    try:
        service = request.app.state.service
        if not service.view_manager:
            raise HTTPException(status_code=503, detail={"error": "View manager not available"})
        
        result = await service.view_manager.refresh_all_views()
        return {
            "success": True,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

