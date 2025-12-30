#!/usr/bin/env bash
# Deploy the generated `pi-deployment/` bundle to a Raspberry Pi over SSH.
#
# Usage:
#   ./deploy-to-pi.sh [pi-hostname-or-ip]
#
# This script is intended to be run from your development machine (Mac/PC),
# not from the Raspberry Pi itself.

set -euo pipefail

PI_HOST="${1:-raspberrypi.local}"
PI_USER="${PI_USER:-pi}"
DEPLOY_DIR="pi-deployment"

echo "Rio Microfluidics Controller - Deployment Script"
echo "================================================"
echo ""
echo "Target: ${PI_USER}@${PI_HOST}"
echo ""

# Guardrail: refuse to run on a Raspberry Pi (common cause of nested deployments).
if [[ "$(uname -s)" == "Linux" ]] && [[ -r /sys/firmware/devicetree/base/model ]]; then
    if grep -q "Raspberry Pi" /sys/firmware/devicetree/base/model; then
        echo "Error: This script should be run from your Mac/PC, not on the Raspberry Pi."
        echo "Reason: running deployment commands on the Pi is a common cause of nested paths like:"
        echo "  ~/rio-controller/pi-deployment/pi-deployment/..."
        exit 1
    fi
fi

echo "Step 1: Generating ${DEPLOY_DIR}/ ..."
./create-pi-deployment.sh

if [[ ! -d "${DEPLOY_DIR}" ]]; then
    echo "Error: ${DEPLOY_DIR}/ was not created by create-pi-deployment.sh"
    exit 1
fi

if [[ ! -f "${DEPLOY_DIR}/setup.sh" ]] || [[ ! -f "${DEPLOY_DIR}/run.sh" ]]; then
    echo "Error: ${DEPLOY_DIR}/ does not look like a valid deployment bundle (missing setup.sh/run.sh)."
    exit 1
fi

echo ""
echo "Step 2: Preparing destination on Pi..."
ssh "${PI_USER}@${PI_HOST}" << 'ENDSSH'
set -euo pipefail
mkdir -p ~/rio-controller

# Guardrail: if someone previously synced into ~/rio-controller/pi-deployment/,
# remove that nested copy so the next rsync lands at the correct depth.
if [[ -f ~/rio-controller/pi-deployment/setup.sh ]] || [[ -f ~/rio-controller/pi-deployment/run.sh ]]; then
  echo "Detected nested deployment at ~/rio-controller/pi-deployment/ — removing it."
  rm -rf ~/rio-controller/pi-deployment
fi
ENDSSH

echo ""
echo "Step 3: Syncing bundle to Pi (rsync)..."
echo "Note: The trailing slash on '${DEPLOY_DIR}/' is intentional."
rsync -avz --delete \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  "${DEPLOY_DIR}/" "${PI_USER}@${PI_HOST}:~/rio-controller/"

echo ""
echo "Deployment sync complete."
echo ""
echo "Next steps on the Pi:"
echo "  ssh ${PI_USER}@${PI_HOST}"
echo "  cd ~/rio-controller"
echo "  ./setup.sh   # first time only (or after dependency changes)"
echo "  ./run.sh"
