# Rio Microfluidics Controller - Raspberry Pi Deployment

This is a minimal deployment package containing only the essential files needed to run the Rio microfluidics controller on Raspberry Pi.

## Quick Start

### 1. Setup (First time only)

```bash
./setup.sh
```

This will:
- Upgrade pip
- Install required packages to system Python
- Verify installation

**Note:** Packages are installed to system Python. No virtual environment is used.

### 2. Run

```bash
./run.sh
```

Or manually:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow tab if not used
export RIO_HEATER_ENABLED=false    # Hide heater tab if not used
python main.py
```

## Environment Variables

- `RIO_STROBE_CONTROL_MODE`: `strobe-centric` (32-bit, old firmware) or `camera-centric` (new firmware)
- `RIO_SIMULATION`: `false` for hardware operation
- `RIO_DROPLET_ANALYSIS_ENABLED`: `true` to enable droplet detection
- `RIO_PORT`: Port number (default: 5000)

## Configuration

See `configurations/` directory for example configuration files.

## Hardware Requirements

- Raspberry Pi OS (32-bit or 64-bit)
- System packages should already be installed:
  - spidev (SPI communication)
  - RPi.GPIO (GPIO control)
  - picamera (for 32-bit) or picamera2 (for 64-bit)

If hardware packages are missing:
```bash
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

## Troubleshooting

See the full documentation in the main repository for troubleshooting steps.
