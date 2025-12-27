#!/bin/bash
# Test runner script for droplet detection
# Runs tests in the mamba rio-simulation environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOFTWARE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Droplet Detection Test Suite"
echo "=========================================="
echo ""

# Activate mamba environment
echo "Activating mamba rio-simulation environment..."
source "$(conda info --base)/etc/profile.d/conda.sh" || source "$HOME/mambaforge/etc/profile.d/conda.sh" || true
conda activate rio-simulation || mamba activate rio-simulation || {
    echo "Warning: Could not activate mamba environment. Continuing with system Python..."
}

echo ""
echo "Running unit tests..."
echo "----------------------------------------"
cd "$SOFTWARE_DIR"
python -m unittest discover -s tests -p "test_droplet_detection.py" -v || {
    echo "Warning: unittest failed. Trying pytest..."
    python -m pytest tests/test_droplet_detection.py -v || echo "Tests failed or pytest not available"
}

echo ""
echo "Running integration tests..."
echo "----------------------------------------"
python -m droplet_detection.test_integration --images 5 || {
    echo "Warning: Integration tests failed or test images not available"
}

echo ""
echo "=========================================="
echo "Test suite complete"
echo "=========================================="
