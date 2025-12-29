#!/bin/bash
# Test script for Socket.IO upgrade
# This script helps test the upgraded Socket.IO versions

set -e

echo "=========================================="
echo "Socket.IO Upgrade Test Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv-socketio-test" ]; then
    echo -e "${YELLOW}Creating test virtual environment...${NC}"
    python3 -m venv venv-socketio-test
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv-socketio-test/bin/activate

# Install upgraded packages
echo -e "${YELLOW}Installing upgraded Socket.IO packages...${NC}"
pip install --upgrade pip

# Try software directory first, fall back to pi-deployment
if [ -f "software/requirements-webapp-only-32bit-upgraded.txt" ]; then
    pip install -r software/requirements-webapp-only-32bit-upgraded.txt
elif [ -f "pi-deployment/requirements-webapp-only-32bit-upgraded.txt" ]; then
    pip install -r pi-deployment/requirements-webapp-only-32bit-upgraded.txt
else
    echo -e "${RED}Error: Could not find requirements-webapp-only-32bit-upgraded.txt${NC}"
    echo "Please ensure you're in the rio-controller directory"
    exit 1
fi

# Check installed versions
echo ""
echo -e "${GREEN}Installed versions:${NC}"
python3 -c "
import flask_socketio
import socketio
import engineio
print(f'Flask-SocketIO: {flask_socketio.__version__}')
print(f'python-socketio: {socketio.__version__}')
print(f'python-engineio: {engineio.__version__}')
"

echo ""
echo -e "${GREEN}✓ Installation complete${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the application:"
if [ -f "pi-deployment/main.py" ]; then
    echo "   python pi-deployment/main.py"
elif [ -f "software/main.py" ]; then
    echo "   python software/main.py"
else
    echo "   python main.py  # (adjust path as needed)"
fi
echo "2. Open the web interface in a browser"
echo "3. Check browser console for errors"
echo "4. Test all Socket.IO functionality"
echo ""
echo -e "${YELLOW}To rollback:${NC}"
echo "deactivate"
echo "source venv-rio/bin/activate  # Your original environment"
echo ""
echo -e "${GREEN}Test environment is ready!${NC}"

