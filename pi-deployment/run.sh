#!/bin/bash
# Run script for Raspberry Pi
# Uses system Python (no virtual environment)

cd "$(dirname "$0")"

# Set default environment variables if not set
export RIO_STROBE_CONTROL_MODE=${RIO_STROBE_CONTROL_MODE:-strobe-centric}
export RIO_SIMULATION=${RIO_SIMULATION:-false}
export RIO_DROPLET_ANALYSIS_ENABLED=${RIO_DROPLET_ANALYSIS_ENABLED:-true}
export RIO_FLOW_ENABLED=${RIO_FLOW_ENABLED:-false}
export RIO_HEATER_ENABLED=${RIO_HEATER_ENABLED:-false}

echo "Starting Rio microfluidics controller..."
echo "Control mode: $RIO_STROBE_CONTROL_MODE"
echo "Simulation: $RIO_SIMULATION"
echo "Droplet detection: $RIO_DROPLET_ANALYSIS_ENABLED"
echo ""

python main.py
