#!/bin/bash
# Run script for Raspberry Pi — Scenario 1 (UI + Pi Camera + strobe on device)
# Uses system Python (no virtual environment)

set -e
cd "$(dirname "$0")"

# Scenario 1 defaults (override via environment if needed)
export PYTHONPATH="${PYTHONPATH:-.}"
export RIO_SIMULATION="${RIO_SIMULATION:-false}"
export RIO_CAMERA_TYPE="${RIO_CAMERA_TYPE:-rpi}"
export RIO_ROI_MODE="${RIO_ROI_MODE:-hardware}"
# Scenario 1 UI: hide Droplet Detection tab (hybrid CoolerMaster keeps its own launch defaults)
export RIO_DROPLET_ANALYSIS_ENABLED="${RIO_DROPLET_ANALYSIS_ENABLED:-false}"
export RIO_FLOW_ENABLED="${RIO_FLOW_ENABLED:-false}"
export RIO_HEATER_ENABLED="${RIO_HEATER_ENABLED:-false}"
export RIO_PUMP_ENABLED="${RIO_PUMP_ENABLED:-false}"
# Same proven concurrency setting as hybrid host (scripts/dev/run-hybrid-host.sh):
# without this, gevent monkey-patch starves the Pi Camera MJPEG capture loop.
export RIO_NO_GEVENT_PATCH="${RIO_NO_GEVENT_PATCH:-true}"

echo "Starting Rio microfluidics controller (Scenario 1)..."
echo "  Simulation:  $RIO_SIMULATION"
echo "  Camera:      $RIO_CAMERA_TYPE"
echo "  ROI mode:    $RIO_ROI_MODE"
echo "  Droplet:     $RIO_DROPLET_ANALYSIS_ENABLED"
echo "  Flow/Heater: $RIO_FLOW_ENABLED / $RIO_HEATER_ENABLED"
echo "  No gevent:   $RIO_NO_GEVENT_PATCH"
echo ""

# Prefer python3; fall back to python if needed
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

exec "$PY" -u main.py
