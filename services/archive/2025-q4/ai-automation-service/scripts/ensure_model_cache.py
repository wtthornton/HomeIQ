#!/usr/bin/env python3
"""
Ensure soft prompt training model is cached in the models volume.

This script runs on container startup to ensure the model is available
for training jobs, preventing timeouts during model download.
"""

import os
import sys
from pathlib import Path

def ensure_model_cached():
    """Check if flan-t5-small model is cached, download if missing."""
    model_name = "google/flan-t5-small"
    cache_dir = Path("/app/models")
    
    # Set environment variable (TRANSFORMERS_CACHE is deprecated, use HF_HOME only)
    os.environ['HF_HOME'] = str(cache_dir)
    # Remove TRANSFORMERS_CACHE if present to avoid deprecation warnings
    if 'TRANSFORMERS_CACHE' in os.environ:
        del os.environ['TRANSFORMERS_CACHE']
    
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        
        # Check if model.safetensors exists
        model_files = list(cache_dir.glob(f"**/models--google--flan-t5-small/**/model.safetensors"))
        
        if model_files:
            print(f"✓ Model already cached at: {model_files[0]}")
            # Verify it can be loaded
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir), local_files_only=True)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(cache_dir), local_files_only=True)
                print("✓ Model verified and ready for training")
                return True
            except Exception as e:
                print(f"⚠ Model file exists but cannot be loaded: {e}")
                print("  Re-downloading...")
        
        # Download model if missing or invalid
        print(f"Downloading {model_name} model (308MB, this may take 2-3 minutes)...")
        print("  This is a one-time download that will be cached for future use.")
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
        print("  ✓ Tokenizer downloaded")
        
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(cache_dir))
        print("  ✓ Model weights downloaded")
        
        # Verify
        model_files = list(cache_dir.glob(f"**/models--google--flan-t5-small/**/model.safetensors"))
        if model_files:
            print(f"✓ Model successfully cached at: {model_files[0]}")
            return True
        else:
            print("✗ Model download completed but file not found in expected location")
            return False
            
    except Exception as e:
        print(f"✗ Error ensuring model cache: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = ensure_model_cached()
    sys.exit(0 if success else 1)

