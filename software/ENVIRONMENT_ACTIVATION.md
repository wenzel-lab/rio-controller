# Environment Activation Guide

## Current Status

This guide explains how to properly activate and use your mamba environment for the Rio controller software.

## Activate Mamba Environment

```bash
# Activate the rio-simulation environment
mamba activate rio-simulation

# Verify you're in the right environment
which python
# Should show: ~/mambaforge/envs/rio-simulation/bin/python (or similar)

# Verify dependencies are installed
python -c "import flask_socketio; print('✓ Dependencies OK')"
```

## If Dependencies Are Missing in Mamba Environment

If you activate `rio-simulation` and get import errors, install dependencies:

```bash
mamba activate rio-simulation
cd software
pip install -r requirements-simulation.txt
```

## Running the Application

After activating the environment:

```bash
mamba activate rio-simulation
cd software
RIO_SIMULATION=true python main.py 5001
```

## Folder Structure

The software is organized as follows:
- `software/main.py` - Application entry point
- `software/rio-webapp/` - Web application (controllers, templates, static files)
- `software/drivers/` - Low-level hardware drivers
- `software/controllers/` - High-level device controllers
- `software/simulation/` - Simulation layer for testing without hardware

See [software/README.md](README.md) for complete folder structure and organization.

