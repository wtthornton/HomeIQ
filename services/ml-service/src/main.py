"""
ML Service - Classical Machine Learning
Phase 1: Containerized AI Models

Provides classical ML algorithms for:
- Pattern clustering (KMeans, DBSCAN)
- Anomaly detection (Isolation Forest)
- Feature importance (Random Forest)
- Batch processing capabilities
"""

import logging
import time
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .algorithms.clustering import ClusteringManager
from .algorithms.anomaly_detection import AnomalyDetectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global managers
clustering_manager: ClusteringManager = None
anomaly_manager: AnomalyDetectionManager = None

# Create FastAPI app
app = FastAPI(
    title="ML Service",
    description="Classical machine learning algorithms for pattern detection",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ClusteringRequest(BaseModel):
    data: List[List[float]] = Field(..., description="Data points to cluster")
    algorithm: str = Field("kmeans", description="Clustering algorithm (kmeans, dbscan)")
    n_clusters: Optional[int] = Field(None, description="Number of clusters (for KMeans)")
    eps: Optional[float] = Field(None, description="Epsilon parameter (for DBSCAN)")

class ClusteringResponse(BaseModel):
    labels: List[int] = Field(..., description="Cluster labels")
    n_clusters: int = Field(..., description="Number of clusters found")
    algorithm: str = Field(..., description="Algorithm used")
    processing_time: float = Field(..., description="Processing time in seconds")

class AnomalyRequest(BaseModel):
    data: List[List[float]] = Field(..., description="Data points to analyze")
    contamination: float = Field(0.1, description="Expected proportion of outliers")

class AnomalyResponse(BaseModel):
    labels: List[int] = Field(..., description="Anomaly labels (1=normal, -1=anomaly)")
    scores: List[float] = Field(..., description="Anomaly scores")
    n_anomalies: int = Field(..., description="Number of anomalies detected")
    processing_time: float = Field(..., description="Processing time in seconds")

class BatchProcessRequest(BaseModel):
    operations: List[Dict[str, Any]] = Field(..., description="List of operations to process")

class BatchProcessResponse(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Results for each operation")
    processing_time: float = Field(..., description="Total processing time in seconds")

# Initialize managers
@app.on_event("startup")
async def startup_event():
    """Initialize ML managers on startup"""
    global clustering_manager, anomaly_manager
    
    logger.info("🚀 Starting ML Service...")
    try:
        clustering_manager = ClusteringManager()
        anomaly_manager = AnomalyDetectionManager()
        logger.info("✅ ML Service started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start ML Service: {e}")
        raise

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ml-service",
        "algorithms_available": {
            "clustering": ["kmeans", "dbscan"],
            "anomaly_detection": ["isolation_forest"]
        }
    }

@app.get("/algorithms/status")
async def get_algorithm_status():
    """Get detailed algorithm status"""
    return {
        "clustering": {
            "kmeans": "available",
            "dbscan": "available"
        },
        "anomaly_detection": {
            "isolation_forest": "available"
        }
    }

@app.post("/cluster", response_model=ClusteringResponse)
async def cluster_data(request: ClusteringRequest):
    """Cluster data using specified algorithm"""
    if not clustering_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        start_time = time.time()
        
        if request.algorithm == "kmeans":
            labels, n_clusters = await clustering_manager.kmeans_cluster(
                data=request.data,
                n_clusters=request.n_clusters
            )
        elif request.algorithm == "dbscan":
            labels, n_clusters = await clustering_manager.dbscan_cluster(
                data=request.data,
                eps=request.eps
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown algorithm: {request.algorithm}")
        
        processing_time = time.time() - start_time
        
        return ClusteringResponse(
            labels=labels,
            n_clusters=n_clusters,
            algorithm=request.algorithm,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error clustering data: {e}")
        raise HTTPException(status_code=500, detail=f"Clustering failed: {e}")

@app.post("/anomaly", response_model=AnomalyResponse)
async def detect_anomalies(request: AnomalyRequest):
    """Detect anomalies in data using Isolation Forest"""
    if not anomaly_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        start_time = time.time()
        
        labels, scores = await anomaly_manager.detect_anomalies(
            data=request.data,
            contamination=request.contamination
        )
        
        n_anomalies = sum(1 for label in labels if label == -1)
        processing_time = time.time() - start_time
        
        return AnomalyResponse(
            labels=labels,
            scores=scores,
            n_anomalies=n_anomalies,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {e}")

@app.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process(request: BatchProcessRequest):
    """Process multiple operations in batch"""
    try:
        start_time = time.time()
        results = []
        
        for operation in request.operations:
            op_type = operation.get("type")
            op_data = operation.get("data", {})
            
            if op_type == "cluster":
                if not clustering_manager:
                    raise HTTPException(status_code=503, detail="Clustering service not ready")
                
                algorithm = op_data.get("algorithm", "kmeans")
                data = op_data.get("data", [])
                
                if algorithm == "kmeans":
                    labels, n_clusters = await clustering_manager.kmeans_cluster(
                        data=data,
                        n_clusters=op_data.get("n_clusters")
                    )
                elif algorithm == "dbscan":
                    labels, n_clusters = await clustering_manager.dbscan_cluster(
                        data=data,
                        eps=op_data.get("eps")
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown clustering algorithm: {algorithm}")
                
                results.append({
                    "type": "cluster",
                    "algorithm": algorithm,
                    "labels": labels,
                    "n_clusters": n_clusters
                })
            
            elif op_type == "anomaly":
                if not anomaly_manager:
                    raise HTTPException(status_code=503, detail="Anomaly detection service not ready")
                
                data = op_data.get("data", [])
                contamination = op_data.get("contamination", 0.1)
                
                labels, scores = await anomaly_manager.detect_anomalies(
                    data=data,
                    contamination=contamination
                )
                
                results.append({
                    "type": "anomaly",
                    "labels": labels,
                    "scores": scores,
                    "n_anomalies": sum(1 for label in labels if label == -1)
                })
            
            else:
                raise HTTPException(status_code=400, detail=f"Unknown operation type: {op_type}")
        
        processing_time = time.time() - start_time
        
        return BatchProcessResponse(
            results=results,
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
