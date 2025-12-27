#!/bin/bash
# Setup script for Rio Controller Simulation Mode
# This script sets up the mamba environment and installs dependencies

set -e  # Exit on error

echo "============================================"
echo "Rio Controller Simulation Setup"
echo "============================================"
echo ""

# Check if mamba/conda is available
if command -v mamba &> /dev/null; then
    CONDA_CMD="mamba"
elif command -v conda &> /dev/null; then
    CONDA_CMD="conda"
    echo "Note: Using conda instead of mamba"
else
    echo "Error: Neither mamba nor conda found. Please install conda/mamba first."
    exit 1
fi

# Get software directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOFTWARE_DIR="$SCRIPT_DIR"

echo "Software directory: $SOFTWARE_DIR"
echo ""

# Step 1: Create environment
echo "Step 1: Creating mamba environment 'rio-simulation'..."
$CONDA_CMD create -n rio-simulation python=3.10 -y

# Step 2: Activate and install dependencies
echo ""
echo "Step 2: Installing dependencies..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rio-simulation

# Verify we're in the environment
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "⚠️  Warning: No conda environment detected. Activating rio-simulation..."
    conda activate rio-simulation
fi

echo "Active environment: $CONDA_DEFAULT_ENV"
echo "Python location: $(which python)"

# We're already in the software directory
cd "$SOFTWARE_DIR"

# Install dependencies (will install to active environment)
if [ -f "requirements-simulation.txt" ]; then
    echo "Installing from requirements-simulation.txt..."
    pip install -r requirements-simulation.txt
else
    echo "Installing core dependencies..."
    pip install Flask==1.0.2 Flask-SocketIO==4.3.2 eventlet==0.33.3
    pip install opencv-python numpy Pillow PyYAML
fi

# Step 3: Verify installation
echo ""
echo "Step 3: Verifying installation..."
python -c "import flask; import cv2; import numpy; import yaml; print('✓ All packages installed successfully!')"

# Step 4: Check config file
echo ""
echo "Step 4: Checking configuration..."
cd "$SOFTWARE_DIR"
if [ -f "rio-config.yaml" ]; then
    if grep -q "simulation: true" rio-config.yaml; then
        echo "✓ Configuration file found with simulation: true"
    else
        echo "⚠ Configuration file found but simulation is not set to true"
        echo "  Edit rio-config.yaml and set 'simulation: true'"
    fi
else
    echo "⚠ Configuration file not found. Creating default..."
    cat > rio-config.yaml << 'EOF'
simulation: true
camera:
  width: 640
  height: 480
  fps: 30
  generate_droplets: true
  droplet_count: 5
  droplet_size_range: [10, 50]
strobe:
  port: 24
  reply_pause_s: 0.1
flow:
  port: 26
  num_channels: 4
  pressure_range: [0, 6000]
  flow_range: [0, 1000]
EOF
    echo "✓ Created rio-config.yaml with simulation: true"
fi

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "To run the simulation:"
echo "  1. Activate environment: mamba activate rio-simulation"
echo "  2. Enable simulation: export RIO_SIMULATION=true"
echo "  3. Run webapp: cd software && python main.py"
echo ""
echo "Or use ./run-simulation.sh from the software directory for convenience."
echo ""

