#!/bin/bash
# Quick run script for Rio Controller Simulation Mode

# Get repository root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$SCRIPT_DIR"

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

# Navigate to webapp directory
cd "$REPO_ROOT/user-interface-software/src/webapp"

echo "============================================"
echo "Starting Rio Controller Simulation"
echo "============================================"
echo "Environment: rio-simulation"
echo "Simulation mode: ENABLED"
echo "Web interface: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo "============================================"
echo ""

# Run the webapp
python pi_webapp.py

