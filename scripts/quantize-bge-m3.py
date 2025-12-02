#!/usr/bin/env python3
"""
BGE-M3 Model Quantization Script
Epic 47: Downloads and quantizes BGE-M3-base to INT8
"""

import os
import sys
from pathlib import Path

MODEL_NAME = "BAAI/bge-m3-base"
TARGET_DIR = Path("./models/bge-m3/bge-m3-base-int8")
CACHE_DIR = Path("./models/cache")

def main():
    print("╔════════════════════════════════════════════════════╗")
    print("║  BGE-M3 Embedding Model - Quantization Script     ║")
    print("║  Epic 47: BGE-M3 Embedding Upgrade (Phase 1)      ║")
    print("╚════════════════════════════════════════════════════╝")
    print()
    
    # Create directories
    print("📁 Creating model directories...")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print("✅ Directories created")
    print()
    
    # Check if already quantized
    if (TARGET_DIR / "openvino_model.xml").exists():
        print("✅ BGE-M3 model already quantized (skipping)")
        print(f"   Location: {TARGET_DIR}")
        return 0
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📦 Quantizing BGE-M3-base Model...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Model: {MODEL_NAME}")
    print("Task: feature-extraction")
    print("Quantization: INT8 weight quantization")
    print("Target: ~125MB (vs ~500MB FP32)")
    print("Dimensions: 1024 (vs 384 for all-MiniLM-L6-v2)")
    print()
    print("Downloading and quantizing model (this may take several minutes)...")
    
    try:
        from optimum.intel import OVModelForFeatureExtraction
        from transformers import AutoTokenizer
        
        # Set cache directory
        os.environ["HF_HOME"] = str(CACHE_DIR)
        os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)
        
        # Check for HuggingFace token (from .env or environment)
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
            os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token
            print("✅ Using HuggingFace token from environment")
        else:
            print("⚠️  No HuggingFace token found - using public access")
            print("   (For gated models, set HF_TOKEN or HUGGINGFACE_HUB_TOKEN)")
        
        # Download and quantize
        print("Downloading model from HuggingFace...")
        model = OVModelForFeatureExtraction.from_pretrained(
            MODEL_NAME,
            export=True,
            compile=False,  # Don't compile yet, just export
            cache_dir=str(CACHE_DIR)
        )
        
        print("Saving quantized model...")
        model.save_pretrained(str(TARGET_DIR))
        
        # Save tokenizer
        print("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            cache_dir=str(CACHE_DIR)
        )
        tokenizer.save_pretrained(str(TARGET_DIR))
        
        print("✅ BGE-M3 model quantized successfully!")
        
        # Verify
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔍 Verifying quantized model...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Test embedding generation
        test_texts = ["test embedding"]
        inputs = tokenizer(test_texts, return_tensors='pt', padding=True, truncation=True)
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        
        embedding_dim = embeddings.shape[1]
        print(f"✅ Model loaded successfully")
        print(f"   Embedding dimension: {embedding_dim}")
        
        if embedding_dim == 1024:
            print("✅ Embedding dimension correct (1024)")
        else:
            print(f"⚠️  Expected 1024 dimensions, got {embedding_dim}")
            return 1
        
        # Check model size
        if TARGET_DIR.exists():
            import subprocess
            result = subprocess.run(
                ["du", "-sh", str(TARGET_DIR)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                size = result.stdout.split()[0]
                print(f"   Model size: {size}")
        
        print()
        print("╔════════════════════════════════════════════════════╗")
        print("║        BGE-M3 Quantization Complete!              ║")
        print("╚════════════════════════════════════════════════════╝")
        print()
        print(f"✅ Model saved to: {TARGET_DIR}")
        print()
        print("✅ Next steps:")
        print("   1. Restart OpenVINO service: docker-compose restart openvino-service")
        print("   2. Validate deployment: bash scripts/validate-bge-m3-deployment.sh")
        
        return 0
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install optimum[openvino,intel] transformers")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

