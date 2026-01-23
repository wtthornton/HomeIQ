#!/bin/bash
# Automated embedding consistency test runner
# Tests sentence-transformers 3.3.1 vs 5.1.2 compatibility

set -e

echo "========================================================================"
echo "sentence-transformers Embedding Consistency Test"
echo "Testing: 3.3.1 vs 5.1.2"
echo "Model: all-MiniLM-L6-v2"
echo "========================================================================"
echo ""

# Create virtual environment for testing
echo "Creating test virtual environment..."
python3 -m venv embedding_test_env
source embedding_test_env/bin/activate

# Test old version (3.3.1)
echo ""
echo "========================================================================"
echo "Phase 1: Testing sentence-transformers 3.3.1"
echo "========================================================================"
echo ""

pip install -q sentence-transformers==3.3.1 numpy
python test_embedding_consistency.py --generate old

# Test new version (5.1.2)
echo ""
echo "========================================================================"
echo "Phase 2: Testing sentence-transformers 5.1.2"
echo "========================================================================"
echo ""

pip install -q --upgrade sentence-transformers==5.1.2
python test_embedding_consistency.py --generate new

# Compare embeddings
echo ""
echo "========================================================================"
echo "Phase 3: Comparing Embeddings"
echo "========================================================================"
echo ""

python test_embedding_consistency.py --compare

# Cleanup
echo ""
echo "========================================================================"
echo "Cleanup"
echo "========================================================================"
echo ""

deactivate
rm -rf embedding_test_env

echo ""
echo "✓ Test complete!"
echo ""
echo "Results saved in embedding_tests/ directory:"
echo "  - embeddings_old.npz (3.3.1 embeddings)"
echo "  - embeddings_new.npz (5.1.2 embeddings)"
echo "  - metadata_old.json (3.3.1 metadata)"
echo "  - metadata_new.json (5.1.2 metadata)"
echo "  - comparison_report.json (similarity analysis)"
echo ""
