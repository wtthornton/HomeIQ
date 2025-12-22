#!/usr/bin/env python3
"""
Download all ML models used by HomeIQ AI services.

This script pre-downloads models to a shared volume, ensuring:
- Deterministic model caching
- Faster service startup (no download delays)
- Offline capability after initial download
- Consistent model versions across services

Models downloaded:
1. all-MiniLM-L6-v2 (INT8) - Embeddings (ai-automation-service)
2. bge-reranker-base (INT8) - Re-ranking (ai-automation-service)
3. flan-t5-small (INT8) - Classification/Training (ai-automation-service, ai-training-service)

Usage:
    python download_all_models.py

Environment Variables:
    HF_HOME: HuggingFace cache directory (default: /app/models)
    MODELS_TO_DOWNLOAD: Comma-separated list of model names (optional)
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# Model definitions
MODELS = {
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "type": "embedding",
        "size_mb": 20,  # INT8
        "openvino": True,
    },
    "bge-reranker-base": {
        "name": "BAAI/bge-reranker-base",
        "type": "reranker",
        "size_mb": 280,  # INT8
        "openvino": True,
    },
    "flan-t5-small": {
        "name": "google/flan-t5-small",
        "type": "seq2seq",
        "size_mb": 80,  # INT8
        "openvino": False,  # Not available in OpenVINO format
    },
}


def check_openvino() -> bool:
    """Check if OpenVINO is available for optimized models."""
    try:
        import openvino
        import optimum.intel
        return True
    except ImportError:
        return False


def download_model(model_key: str, model_info: dict, cache_dir: Path, use_openvino: bool) -> bool:
    """Download a single model."""
    model_name = model_info["name"]
    model_type = model_info["type"]
    size_mb = model_info["size_mb"]
    supports_openvino = model_info.get("openvino", False)
    
    print(f"\n{'='*80}")
    print(f"Downloading: {model_key}")
    print(f"  Name: {model_name}")
    print(f"  Type: {model_type}")
    print(f"  Size: ~{size_mb}MB (INT8)" if supports_openvino and use_openvino else f"  Size: ~{size_mb * 4}MB (FP32)")
    print(f"{'='*80}")
    
    try:
        if supports_openvino and use_openvino:
            # Download OpenVINO-optimized model
            from optimum.intel import OVModelForFeatureExtraction, OVModelForSequenceClassification
            
            if model_type == "embedding":
                print(f"  Downloading OpenVINO INT8 model...")
                model = OVModelForFeatureExtraction.from_pretrained(
                    model_name,
                    export=True,
                    cache_dir=str(cache_dir),
                )
                print(f"  ✓ OpenVINO model downloaded and cached")
            elif model_type == "reranker":
                print(f"  Downloading OpenVINO INT8 model...")
                model = OVModelForSequenceClassification.from_pretrained(
                    model_name,
                    export=True,
                    cache_dir=str(cache_dir),
                )
                print(f"  ✓ OpenVINO model downloaded and cached")
            else:
                # Fallback to standard model
                from transformers import AutoModel
                print(f"  Downloading standard model (OpenVINO not supported)...")
                model = AutoModel.from_pretrained(
                    model_name,
                    cache_dir=str(cache_dir),
                )
                print(f"  ✓ Model downloaded and cached")
        else:
            # Download standard model
            if model_type == "embedding":
                from sentence_transformers import SentenceTransformer
                print(f"  Downloading SentenceTransformer model...")
                model = SentenceTransformer(model_name, cache_folder=str(cache_dir))
                print(f"  ✓ Model downloaded and cached")
            elif model_type == "seq2seq":
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                print(f"  Downloading tokenizer and model...")
                tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(cache_dir))
                print(f"  ✓ Model downloaded and cached")
            else:
                from transformers import AutoModel
                print(f"  Downloading standard model...")
                model = AutoModel.from_pretrained(model_name, cache_dir=str(cache_dir))
                print(f"  ✓ Model downloaded and cached")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error downloading model: {e}")
        return False


def main():
    """Main function to download all models."""
    print("="*80)
    print("HomeIQ Model Preparation")
    print("="*80)
    print("\nPre-downloading ML models for deterministic caching")
    print("This ensures models are available before service containers start.\n")
    
    # Get cache directory
    cache_dir = Path(os.getenv("HF_HOME", "/app/models"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Cache directory: {cache_dir}")
    
    # Check OpenVINO availability
    use_openvino = check_openvino()
    if use_openvino:
        print("✓ OpenVINO available - will use INT8 optimized models")
    else:
        print("⚠ OpenVINO not available - will use standard models (larger size)")
    
    # Get models to download (from env var or all)
    models_to_download = os.getenv("MODELS_TO_DOWNLOAD", "").split(",")
    models_to_download = [m.strip() for m in models_to_download if m.strip()]
    
    if models_to_download:
        # Download only specified models
        models = {k: v for k, v in MODELS.items() if k in models_to_download}
        if not models:
            print(f"✗ No valid models found in MODELS_TO_DOWNLOAD: {models_to_download}")
            sys.exit(1)
    else:
        # Download all models
        models = MODELS
    
    print(f"\nModels to download: {len(models)}")
    for key in models.keys():
        print(f"  - {key}")
    
    # Download each model
    results = {}
    for model_key, model_info in models.items():
        success = download_model(model_key, model_info, cache_dir, use_openvino)
        results[model_key] = success
    
    # Summary
    print(f"\n{'='*80}")
    print("Download Summary")
    print(f"{'='*80}")
    
    total = len(results)
    successful = sum(1 for v in results.values() if v)
    failed = total - successful
    
    for model_key, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {model_key}")
    
    print(f"\nTotal: {total} | Successful: {successful} | Failed: {failed}")
    
    if failed > 0:
        print(f"\n⚠ Some models failed to download. Services may download them on first use.")
        sys.exit(1)
    else:
        print(f"\n✓ All models downloaded successfully!")
        print(f"  Models cached in: {cache_dir}")
        print(f"  Services can now use these models without download delays.")
        sys.exit(0)


if __name__ == "__main__":
    main()

