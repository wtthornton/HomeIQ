#!/usr/bin/env python3
"""
Verification Script for N-Level Synergy Detection Setup
Epic AI-4, Story AI4.1: Device Embedding Generation

Verifies:
- All required packages installed
- Models quantized and loadable
- Database tables created
- System requirements met
"""

import sys
from pathlib import Path


# Colors for terminal output
class Colors:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color

def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{text.center(60)}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def check_python_version():
    """Verify Python version."""
    print("🐍 Checking Python version...")
    version = sys.version_info

    if version.major >= 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    print_error(f"Python {version.major}.{version.minor}.{version.micro} (requires 3.11+)")
    return False

def check_dependencies():
    """Verify required packages installed."""
    print("\n📦 Checking dependencies...")

    required_packages = {
        "sentence_transformers": "sentence-transformers",
        "transformers": "transformers",
        "optimum.intel.openvino": "optimum[openvino,intel]",
        "openvino": "openvino",
        "torch": "torch",
        "numpy": "numpy",
    }

    missing = []
    installed = []

    for module, package in required_packages.items():
        try:
            __import__(module)
            installed.append(package)
        except ImportError:
            missing.append(package)

    for pkg in installed:
        print_success(f"{pkg}")

    if missing:
        for pkg in missing:
            print_error(f"{pkg} - NOT INSTALLED")
        print(f"\n{Colors.YELLOW}Install missing packages:{Colors.NC}")
        print(f"pip install {' '.join(missing)}")
        return False

    return True

def check_models():
    """Verify models are quantized and present."""
    print("\n🤖 Checking quantized models...")

    models_dir = Path("./models/nlevel-synergy")

    models = {
        "embedding-int8": "Embedding Model (all-MiniLM-L6-v2)",
        "reranker-int8": "Re-ranker Model (bge-reranker-base-int8-ov)",
        "classifier-int8": "Classifier Model (flan-t5-small)",
    }

    all_present = True

    for model_dir, description in models.items():
        model_path = models_dir / model_dir / "openvino_model.xml"

        if model_path.exists():
            size = sum(f.stat().st_size for f in (models_dir / model_dir).rglob("*") if f.is_file())
            size_mb = size / (1024 * 1024)
            print_success(f"{description} ({size_mb:.1f} MB)")
        else:
            print_error(f"{description} - NOT FOUND")
            all_present = False

    if not all_present:
        print(f"\n{Colors.YELLOW}Quantize models first:{Colors.NC}")
        print("bash scripts/quantize-nlevel-models.sh")
        return False

    return True

def test_model_loading():
    """Test loading models."""
    print("\n🔧 Testing model loading...")

    try:
        from optimum.intel.openvino import OVModelForFeatureExtraction

        print("  Loading embedding model...")
        OVModelForFeatureExtraction.from_pretrained(
            "./models/nlevel-synergy/embedding-int8",
        )
        print_success("Embedding model loaded")

        return True
    except Exception as e:
        print_error(f"Model loading failed: {e}")
        return False

def check_database():
    """Verify database tables exist."""
    print("\n🗄️  Checking database...")

    try:
        import sqlite3

        db_path = Path("./data/ai_automation.db")

        if not db_path.exists():
            print_error(f"Database not found: {db_path}")
            print(f"\n{Colors.YELLOW}Run migration first:{Colors.NC}")
            print("alembic upgrade head")
            return False

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for device_embeddings table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_embeddings'")
        if cursor.fetchone():
            print_success("device_embeddings table exists")
        else:
            print_error("device_embeddings table NOT FOUND")
            print(f"\n{Colors.YELLOW}Run migration:{Colors.NC}")
            print("alembic upgrade head")
            conn.close()
            return False

        # Check for updated synergy_opportunities columns
        cursor.execute("PRAGMA table_info(synergy_opportunities)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {"synergy_depth", "chain_devices", "embedding_similarity", "final_score"}
        missing_columns = required_columns - columns

        if missing_columns:
            print_error(f"synergy_opportunities missing columns: {missing_columns}")
            print(f"\n{Colors.YELLOW}Run migration:{Colors.NC}")
            print("alembic upgrade head")
            conn.close()
            return False
        print_success("synergy_opportunities table updated")

        conn.close()
        return True

    except Exception as e:
        print_error(f"Database check failed: {e}")
        return False

def check_system_requirements():
    """Check system requirements."""
    print("\n💻 Checking system requirements...")

    import platform

    # Check CPU features (AVX2 for OpenVINO)
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
                if "avx2" in cpuinfo:
                    print_success("CPU supports AVX2 (OpenVINO compatible)")
                else:
                    print_warning("CPU may not support AVX2 (OpenVINO may be slower)")
        else:
            print_warning("CPU feature detection skipped (non-Linux)")
    except:
        print_warning("Could not detect CPU features")

    # Check disk space
    import shutil
    _total, _used, free = shutil.disk_usage("./")
    free_gb = free / (1024 ** 3)

    if free_gb >= 2:
        print_success(f"Disk space: {free_gb:.1f} GB free")
    else:
        print_warning(f"Low disk space: {free_gb:.1f} GB free (recommend 2GB+)")

    # Check memory
    try:
        import psutil
        mem = psutil.virtual_memory()
        mem_gb = mem.total / (1024 ** 3)

        if mem_gb >= 2:
            print_success(f"RAM: {mem_gb:.1f} GB")
        else:
            print_warning(f"Low RAM: {mem_gb:.1f} GB (recommend 2GB+)")
    except ImportError:
        print_warning("Could not check RAM (psutil not installed)")

    return True

def main():
    """Run all verification checks."""
    print_header("N-Level Synergy Detection Setup Verification")
    print("Epic AI-4: Device Embedding Generation")
    print("Story AI4.1: Verifying development environment\n")

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Quantized Models", check_models),
        ("Model Loading", test_model_loading),
        ("Database", check_database),
        ("System Requirements", check_system_requirements),
    ]

    results = {}

    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"{name} check failed with exception: {e}")
            results[name] = False

    # Summary
    print_header("Verification Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, status in results.items():
        if status:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print(f"\n{Colors.BLUE}Results: {passed}/{total} checks passed{Colors.NC}\n")

    if passed == total:
        print(f"{Colors.GREEN}╔════════════════════════════════════════════════════╗{Colors.NC}")
        print(f"{Colors.GREEN}║  ✅ All checks passed! Ready for implementation!  ║{Colors.NC}")
        print(f"{Colors.GREEN}╚════════════════════════════════════════════════════╝{Colors.NC}")
        print(f"\n{Colors.YELLOW}Next steps:{Colors.NC}")
        print("  1. Review Story AI4.1: docs/stories/story-ai4-01-device-embedding-generation.md")
        print("  2. Create feature branch: git checkout -b feature/ai4.1-device-embeddings")
        print("  3. Start implementation!")
        return 0
    print(f"{Colors.RED}╔════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.RED}║  ❌ Some checks failed. Please fix issues above.  ║{Colors.NC}")
    print(f"{Colors.RED}╚════════════════════════════════════════════════════╝{Colors.NC}")
    return 1

if __name__ == "__main__":
    sys.exit(main())

