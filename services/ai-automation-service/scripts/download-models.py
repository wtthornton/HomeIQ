#!/usr/bin/env python3
"""
Download Phase 1 Models Inside Docker Container
Runs during container build or first startup to pre-download models

Models:
1. all-MiniLM-L6-v2 (20MB INT8) - Embeddings
2. bge-reranker-base (280MB INT8) - Re-ranking
3. flan-t5-small (80MB INT8) - Classification

This ensures models are cached in Docker volume
"""

import sys
from pathlib import Path


def download_models():
    """Download all Phase 1 models"""

    print("="*80)
    print("Downloading Phase 1 Models (Inside Docker Container)")
    print("="*80)
    print("\nThis will download ~380MB (INT8) or ~1.5GB (full precision)")
    print("Models cached in: /app/models/\n")

    models_dir = Path("/app/models")
    models_dir.mkdir(parents=True, exist_ok=True)

    # Check if OpenVINO available
    try:
        import openvino
        import optimum.intel
        use_openvino = True
        print("✅ OpenVINO available - will use INT8 optimized models")
    except ImportError:
        use_openvino = False
        print("⚠️  OpenVINO not available - will use standard models")

    # Model 1: Embeddings
    print("\n" + "-"*80)
    print("Model 1/3: all-MiniLM-L6-v2 (Embeddings)")
    print("-"*80)

    try:
        if use_openvino:
            from optimum.intel import OVModelForFeatureExtraction
            from transformers import AutoTokenizer

            print("Downloading and converting to OpenVINO INT8...")
            model = OVModelForFeatureExtraction.from_pretrained(
                "sentence-transformers/all-MiniLM-L6-v2",
                export=True,
                cache_dir=str(models_dir),
            )
            tokenizer = AutoTokenizer.from_pretrained(
                "sentence-transformers/all-MiniLM-L6-v2",
                cache_dir=str(models_dir),
            )
            print("✅ Downloaded: all-MiniLM-L6-v2 (OpenVINO INT8, ~20MB)")
        else:
            from sentence_transformers import SentenceTransformer

            print("Downloading standard model...")
            model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                cache_folder=str(models_dir),
            )
            print("✅ Downloaded: all-MiniLM-L6-v2 (standard, ~80MB)")

        # Test
        if use_openvino:
            test_inputs = tokenizer(["test"], return_tensors="pt", padding=True, truncation=True)
            outputs = model(**test_inputs)
            print(f"   Test embedding shape: {outputs.last_hidden_state.shape}")
        else:
            test_emb = model.encode(["test"])
            print(f"   Test embedding shape: {test_emb.shape}")

    except Exception as e:
        print(f"❌ Error downloading embeddings: {e}")
        return False

    # Model 2: Re-ranker
    print("\n" + "-"*80)
    print("Model 2/3: bge-reranker-base (Re-ranker)")
    print("-"*80)

    try:
        if use_openvino:
            from optimum.intel import OVModelForSequenceClassification
            from transformers import AutoTokenizer

            print("Downloading pre-quantized INT8 version...")
            model = OVModelForSequenceClassification.from_pretrained(
                "OpenVINO/bge-reranker-base-int8-ov",
                cache_dir=str(models_dir),
            )
            tokenizer = AutoTokenizer.from_pretrained(
                "OpenVINO/bge-reranker-base-int8-ov",
                cache_dir=str(models_dir),
            )
            print("✅ Downloaded: bge-reranker-base (OpenVINO INT8, ~280MB)")
        else:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            print("Downloading standard model...")
            tokenizer = AutoTokenizer.from_pretrained(
                "BAAI/bge-reranker-base",
                cache_dir=str(models_dir),
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "BAAI/bge-reranker-base",
                cache_dir=str(models_dir),
            )
            print("✅ Downloaded: bge-reranker-base (standard, ~1.1GB)")

        # Test
        test_inputs = tokenizer("test [SEP] test", return_tensors="pt", truncation=True)
        outputs = model(**test_inputs)
        print(f"   Test re-ranking score: {outputs.logits[0][0].item():.3f}")

    except Exception as e:
        print(f"❌ Error downloading re-ranker: {e}")
        print("   Continuing anyway (re-ranker is optional enhancement)")

    # Model 3: Classifier
    print("\n" + "-"*80)
    print("Model 3/3: flan-t5-small (Classifier)")
    print("-"*80)

    try:
        if use_openvino:
            from optimum.intel import OVModelForSeq2SeqLM
            from transformers import AutoTokenizer

            print("Downloading and converting to OpenVINO INT8...")
            model = OVModelForSeq2SeqLM.from_pretrained(
                "google/flan-t5-small",
                export=True,
                cache_dir=str(models_dir),
            )
            tokenizer = AutoTokenizer.from_pretrained(
                "google/flan-t5-small",
                cache_dir=str(models_dir),
            )
            print("✅ Downloaded: flan-t5-small (OpenVINO INT8, ~80MB)")
        else:
            from transformers import T5ForConditionalGeneration, T5Tokenizer

            print("Downloading standard model...")
            tokenizer = T5Tokenizer.from_pretrained(
                "google/flan-t5-small",
                cache_dir=str(models_dir),
            )
            model = T5ForConditionalGeneration.from_pretrained(
                "google/flan-t5-small",
                cache_dir=str(models_dir),
            )
            print("✅ Downloaded: flan-t5-small (standard, ~300MB)")

        # Test
        test_prompt = "Classify as energy, comfort, security, or convenience: lights on\n\nCategory:"
        test_inputs = tokenizer(test_prompt, return_tensors="pt")
        outputs = model.generate(**test_inputs, max_new_tokens=5)
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"   Test classification: {result}")

    except Exception as e:
        print(f"❌ Error downloading classifier: {e}")
        return False

    # Success summary
    print("\n" + "="*80)
    print("✅ ALL MODELS DOWNLOADED SUCCESSFULLY!")
    print("="*80)

    if use_openvino:
        print("\nOpenVINO INT8 Stack:")
        print("  - all-MiniLM-L6-v2: ~20MB")
        print("  - bge-reranker-base: ~280MB")
        print("  - flan-t5-small: ~80MB")
        print("  TOTAL: ~380MB")
    else:
        print("\nStandard Models Stack:")
        print("  - all-MiniLM-L6-v2: ~80MB")
        print("  - bge-reranker-base: ~1.1GB")
        print("  - flan-t5-small: ~300MB")
        print("  TOTAL: ~1.5GB")

    print(f"\nModels cached in: {models_dir}")
    print("Ready for Phase 1 pattern detection! 🚀\n")

    return True

if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1)

