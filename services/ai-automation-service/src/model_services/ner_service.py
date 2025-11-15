"""
NER Model Service - Containerized Entity Extraction
Provides NER-based entity extraction as a microservice
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import logging
from transformers import pipeline
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NER Model Service",
    description="Pre-trained NER model for entity extraction",
    version="1.0.0"
)

# Global NER pipeline (loaded once at startup)
ner_pipeline = None

class EntityExtractionRequest(BaseModel):
    query: str
    confidence_threshold: float = 0.8

class EntityExtractionResponse(BaseModel):
    entities: List[Dict[str, Any]]
    processing_time: float
    model_used: str
    confidence_scores: List[float]

@app.on_event("startup")
async def startup_event():
    """Load NER model on startup"""
    global ner_pipeline
    try:
        logger.info("Loading NER model: dslim/bert-base-NER")
        ner_pipeline = pipeline("ner", model="dslim/bert-base-NER")
        logger.info("NER model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load NER model: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": ner_pipeline is not None,
        "model_name": "dslim/bert-base-NER"
    }

@app.post("/extract", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """
    Extract entities from query using NER model
    
    Args:
        request: Entity extraction request with query and confidence threshold
        
    Returns:
        EntityExtractionResponse with extracted entities and metadata
    """
    if ner_pipeline is None:
        raise HTTPException(status_code=500, detail="NER model not loaded")
    
    start_time = time.time()
    
    try:
        # Extract entities using NER
        raw_entities = ner_pipeline(request.query)
        
        # Filter by confidence threshold
        filtered_entities = [
            entity for entity in raw_entities 
            if entity.get('score', 0) >= request.confidence_threshold
        ]
        
        # Convert to our format
        entities = []
        confidence_scores = []
        
        for entity in filtered_entities:
            # Map NER labels to our entity types
            entity_type = "device" if entity['entity'] in ['B-DEVICE', 'I-DEVICE'] else "area"
            
            entities.append({
                'name': entity['word'],
                'type': entity_type,
                'domain': 'unknown',
                'confidence': entity['score'],
                'extraction_method': 'ner',
                'start': entity['start'],
                'end': entity['end']
            })
            confidence_scores.append(entity['score'])
        
        processing_time = time.time() - start_time
        
        logger.info(f"Extracted {len(entities)} entities in {processing_time:.3f}s")
        
        return EntityExtractionResponse(
            entities=entities,
            processing_time=processing_time,
            model_used="dslim/bert-base-NER",
            confidence_scores=confidence_scores
        )
        
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_name": "dslim/bert-base-NER",
        "model_type": "Named Entity Recognition",
        "language": "English",
        "entities_detected": ["PERSON", "ORG", "LOC", "MISC"],
        "model_size": "~400MB",
        "loaded": ner_pipeline is not None
    }

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return {
        "service": "NER Model Service",
        "model": "dslim/bert-base-NER",
        "status": "running",
        "uptime": "calculated_on_request"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8031)
