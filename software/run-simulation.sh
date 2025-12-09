#!/bin/bash
# Quick run script for Rio Controller Simulation Mode

# Get software directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOFTWARE_DIR="$SCRIPT_DIR"

# Activate conda/mamba environment
source "$(conda info --base)/etc/profile.d/conda.sh"

if conda env list | grep -q "rio-simulation"; then
    echo "Activating rio-simulation environment..."
    conda activate rio-simulation
else
    echo "Error: rio-simulation environment not found."
    echo "Please run setup-simulation.sh first."
    exit 1
fi

# Enable simulation mode
export RIO_SIMULATION=true

# Verify we're in the environment
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "⚠️  Warning: No conda environment detected!"
    exit 1
fi

echo "Active environment: $CONDA_DEFAULT_ENV"
echo "Python location: $(which python)"

# Navigate to software directory (where we are)
cd "$SOFTWARE_DIR"

echo "============================================"
echo "Starting Rio Controller Simulation"
echo "============================================"
echo "Environment: $CONDA_DEFAULT_ENV"
echo "Simulation mode: ENABLED"
echo "Web interface: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo "============================================"
echo ""

# Run the webapp
python main.py

