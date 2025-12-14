#!/bin/bash
# Run script for Raspberry Pi
# Activates venv and runs the application

cd "$(dirname "$0")"

if [ ! -d "venv-rio" ]; then
    echo "Error: Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

source venv-rio/bin/activate

# Set default environment variables if not set
export RIO_STROBE_CONTROL_MODE=${RIO_STROBE_CONTROL_MODE:-strobe-centric}
export RIO_SIMULATION=${RIO_SIMULATION:-false}
export RIO_DROPLET_ANALYSIS_ENABLED=${RIO_DROPLET_ANALYSIS_ENABLED:-true}

echo "Starting Rio microfluidics controller..."
echo "Control mode: $RIO_STROBE_CONTROL_MODE"
echo "Simulation: $RIO_SIMULATION"
echo "Droplet detection: $RIO_DROPLET_ANALYSIS_ENABLED"
echo ""

python main.py
