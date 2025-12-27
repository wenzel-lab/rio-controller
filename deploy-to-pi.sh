#!/bin/bash
# Deploy the pi-deployment package to Raspberry Pi via SSH
# Usage: ./deploy-to-pi.sh [pi-hostname-or-ip]

set -e

PI_HOST="${1:-raspberrypi.local}"
PI_USER="pi"
DEPLOY_DIR="pi-deployment"
TARBALL="pi-deployment.tar.gz"

echo "Rio Microfluidics Controller - Deployment Script"
echo "================================================"
echo ""
echo "Target: $PI_USER@$PI_HOST"
echo ""

# Check if deployment directory exists
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "Error: Deployment directory '$DEPLOY_DIR' not found."
    echo "Please run ./create-pi-deployment.sh first to create the deployment package."
    exit 1
fi

# Create tarball
echo "Step 1: Creating deployment tarball..."
cd "$DEPLOY_DIR"
tar czf "../$TARBALL" .
cd ..

echo "Step 2: Copying to Raspberry Pi..."
echo "You may be prompted for the Pi's password..."

scp "$TARBALL" "$PI_USER@$PI_HOST:~/" || {
    echo ""
    echo "Error: Failed to copy files. Please check:"
    echo "  - Pi is connected to network"
    echo "  - SSH is enabled on Pi"
    echo "  - Hostname/IP is correct: $PI_HOST"
    echo "  - Username is correct: $PI_USER"
    exit 1
}

echo ""
echo "Step 3: Extracting and setting up on Pi..."
echo "You may be prompted for the Pi's password again..."

ssh "$PI_USER@$PI_HOST" << ENDSSH
    # Create directory if it doesn't exist
    mkdir -p ~/rio-controller
    
    # Extract tarball
    cd ~/rio-controller
    tar xzf ~/$TARBALL
    
    # Remove tarball
    rm ~/$TARBALL
    
    # Make scripts executable
    chmod +x setup.sh run.sh
    
    echo ""
    echo "Deployment complete!"
    echo ""
    echo "Next steps on the Pi:"
    echo "  1. cd ~/rio-controller"
    echo "  2. ./setup.sh"
    echo "  3. ./run.sh"
    echo ""
    echo "Or SSH into the Pi and run:"
    echo "  ssh $PI_USER@$PI_HOST"
    echo "  cd ~/rio-controller"
    echo "  ./setup.sh"
ENDSSH

echo ""
echo "Deployment complete!"
echo ""
echo "Local tarball kept at: $TARBALL (you can delete it if desired)"
echo ""
echo "To finish setup on the Pi, run:"
echo "  ssh $PI_USER@$PI_HOST"
echo "  cd ~/rio-controller"
echo "  ./setup.sh"
echo "  ./run.sh"
