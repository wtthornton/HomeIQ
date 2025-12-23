#!/bin/bash
# Setup script for home-assistant-datasets

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATASETS_DIR="$PROJECT_ROOT/tests/datasets"

echo "Setting up home-assistant-datasets for testing..."
echo "Project root: $PROJECT_ROOT"
echo "Datasets directory: $DATASETS_DIR"

# Check if datasets directory exists
if [ -d "$DATASETS_DIR/datasets" ] && [ -f "$DATASETS_DIR/datasets/assist-mini/home.yaml" ]; then
    echo "✅ Datasets already exist at $DATASETS_DIR/datasets"
    exit 0
fi

# Create datasets directory
mkdir -p "$DATASETS_DIR"

# Clone repository
echo "Cloning home-assistant-datasets repository..."
cd "$DATASETS_DIR"

if [ -d "home-assistant-datasets" ]; then
    echo "✅ Repository already cloned, updating..."
    cd home-assistant-datasets
    git pull
else
    git clone https://github.com/allenporter/home-assistant-datasets.git
    cd home-assistant-datasets
fi

# Check if datasets directory exists in repo
if [ -d "datasets" ]; then
    # Create symlink or copy
    if [ ! -e "$DATASETS_DIR/datasets" ]; then
        echo "Creating symlink to datasets..."
        ln -s "$DATASETS_DIR/home-assistant-datasets/datasets" "$DATASETS_DIR/datasets"
    fi
    echo "✅ Datasets available at $DATASETS_DIR/datasets"
else
    echo "❌ Error: datasets directory not found in repository"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Available datasets:"
ls -1 "$DATASETS_DIR/datasets" | head -10
echo ""
echo "To use in tests, set DATASET_ROOT environment variable:"
echo "  export DATASET_ROOT=$DATASETS_DIR/datasets"

