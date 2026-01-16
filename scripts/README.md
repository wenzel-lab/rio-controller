# Scripts — Operational Scripts

This folder contains operational scripts for building, deploying, and developing the Rio microfluidics controller.

## Structure

- **`deploy/`** — Deployment scripts for Raspberry Pi
  - `create-pi-deployment.sh` — Generate deployment bundle (Linux/Mac)
  - `create-pi-deployment.bat` — Generate deployment bundle (Windows)
  - `deploy-to-pi.sh` — Deploy bundle to Pi via SSH (Linux/Mac)

- **`dev/`** — Development setup scripts
  - `setup-simulation.sh` — Set up development environment (mamba/conda)
  - `run-simulation.sh` — Run application in simulation mode

- **`pi/`** — Raspberry Pi operational scripts
  - `rio-mode` — Switch between UI-only and API-only systemd services
  - `systemd/` — Example systemd unit files (`rio-ui.service`, `rio-api.service`)

## Quick Reference

### Deployment Scripts

**Generate deployment bundle:**
```bash
# Linux/Mac
./scripts/deploy/create-pi-deployment.sh

# Windows
scripts\deploy\create-pi-deployment.bat
```

**Deploy to Raspberry Pi:**
```bash
# Linux/Mac only
./scripts/deploy/deploy-to-pi.sh [pi-hostname]
# Example: ./scripts/deploy/deploy-to-pi.sh raspberrypi.local
```

### Development Scripts

**Set up simulation environment:**
```bash
./scripts/dev/setup-simulation.sh
```

**Run in simulation mode:**
```bash
./scripts/dev/run-simulation.sh
```

## Script Details

### Deployment Scripts

#### `create-pi-deployment.sh` / `create-pi-deployment.bat`

Generates a minimal deployment bundle in `pi-deployment/` from the `software/` directory.

**What it does:**
- Copies runtime code (controllers, drivers, webapp, droplet-detection)
- Excludes tests, simulation, documentation
- Creates `setup.sh` and `run.sh` for the Pi
- Copies requirements files

**Usage:**
- Run from repository root
- Scripts automatically detect repo root location
- Output: `pi-deployment/` folder

#### `deploy-to-pi.sh`

Deploys the generated bundle to a Raspberry Pi over SSH using rsync.

**Requirements:**
- SSH access to the Pi
- `rsync` installed on your machine
- `create-pi-deployment.sh` must have been run first

**Usage:**
```bash
./scripts/deploy/deploy-to-pi.sh [pi-hostname]
# Default hostname: raspberrypi.local
```

**What it does:**
1. Generates deployment bundle (calls `create-pi-deployment.sh`)
2. Prepares destination on Pi (removes nested deployments)
3. Syncs files via rsync to `~/rio-controller/` on the Pi

### Development Scripts

#### `setup-simulation.sh`

Sets up a mamba/conda environment for development and simulation.

**Requirements:**
- mamba or conda installed
- Python 3.10

**What it does:**
1. Creates `rio-simulation` conda environment
2. Installs dependencies from `requirements-simulation.txt`
3. Verifies installation
4. Creates default `rio-config.yaml` if missing

**Usage:**
```bash
./scripts/dev/setup-simulation.sh
```

#### `run-simulation.sh`

Runs the application in simulation mode using the `rio-simulation` conda environment.

**Requirements:**
- `rio-simulation` environment must exist (run `setup-simulation.sh` first)

**Usage:**
```bash
./scripts/dev/run-simulation.sh
```

**What it does:**
1. Activates `rio-simulation` environment
2. Sets `RIO_SIMULATION=true`
3. Runs `python main.py` from `software/` directory

### Raspberry Pi Scripts

#### `pi/rio-mode`

Switches between UI and API services on a Pi (single-owner model).

**Install systemd services:**
```bash
sudo cp ./scripts/pi/systemd/rio-ui.service /etc/systemd/system/
sudo cp ./scripts/pi/systemd/rio-api.service /etc/systemd/system/
sudo systemctl daemon-reload
```

**Switch modes:**
```bash
./scripts/pi/rio-mode ui
./scripts/pi/rio-mode api
./scripts/pi/rio-mode status
```

## Path Handling

All scripts automatically detect the repository root, so they can be run from any location:

```bash
# These all work:
cd /path/to/rio-controller
./scripts/deploy/create-pi-deployment.sh

cd /path/to/rio-controller/scripts
./deploy/create-pi-deployment.sh

cd /somewhere/else
/path/to/rio-controller/scripts/deploy/create-pi-deployment.sh
```

## Platform Notes

### Linux/Mac
- All scripts use bash
- `deploy-to-pi.sh` requires `rsync` (usually pre-installed)
- Scripts use `/bin/bash` shebang

### Windows
- Use `create-pi-deployment.bat` instead of `.sh` files
- `deploy-to-pi.sh` not available (use WinSCP or WSL)
- Batch files assume execution from repo root

## Troubleshooting

### Scripts can't find repository root
- Ensure you're running from within the repository
- Check that `software/` and `pi-deployment/` directories exist at repo root

### Deployment fails
- Verify `pi-deployment/` was created successfully
- Check SSH access to Pi: `ssh pi@raspberrypi.local`
- Ensure `rsync` is installed: `which rsync`

### Simulation setup fails
- Verify mamba/conda is installed: `which mamba` or `which conda`
- Check Python version: `python --version` (should be 3.10+)
- Try activating environment manually: `conda activate rio-simulation`

## Related Documentation

- **Deployment**: See `pi-deployment/README.md` for Pi setup instructions
- **Development**: See `software/README.md` for development workflow
- **Architecture**: See `ARCHITECTURE.md` for repository structure

