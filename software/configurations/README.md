# Configuration Files

This directory contains example configuration files and documentation for the Rio microfluidics controller.

## Quick Start

1. Choose the appropriate pre-configuration file based on your hardware setup
2. Review the configuration file and adjust environment variables as needed
3. Set environment variables before running the application
4. Use the web interface to fine-tune camera resolution and other settings

## Pre-Configuration Files

### Recommended Starting Points

1. **`config-example-strobe-only-32bit.yaml`**
   - 32-bit Raspberry Pi OS
   - Strobe + Camera
   - PIC-paced strobe timing
   - Droplet detection enabled

### Detailed Reference Examples

- **`config-example-strobe-centric-32bit.yaml`** - Detailed 32-bit PIC-paced configuration

## Documentation

The configuration “quick reference” is included in this README (below) to avoid keeping parallel documentation files.

## Usage

Configuration is done via **environment variables**. The YAML files in this folder are **examples / documented presets** (they are not automatically parsed by `software/main.py`).

Where configuration is consumed in code:

- Constants and default values live in `software/config.py`.
- Runtime toggles are read directly via `os.getenv(...)` in various layers, for example:
  - `RIO_SIMULATION=true|false` (drivers pick simulation vs hardware backends)
  - `RIO_DROPLET_ANALYSIS_ENABLED=true|false` (enable droplet controller + UI)
  - `RIO_FLOW_ENABLED` / `RIO_HEATER_ENABLED` (explicitly show/hide tabs in the UI; see `software/rio-webapp/routes.py`)
  - `RIO_ROI_MODE=software|hardware` (ROI policy; software default. Hardware ROI applies only on camera backends that support it; otherwise it falls back to software ROI.)
  - `RIO_PUMP_ENABLED=true|false` (enable syringe pump controller via USB serial)
  - `RIO_PUMP_PORT=/dev/ttyUSB0` (optional: explicitly select pump serial port)

Example:
```bash
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow control tab (for strobe-only configs)
export RIO_HEATER_ENABLED=false    # Hide heater tab (for strobe-only configs)
export RIO_ROI_MODE=software
python main.py
```

## Tab Visibility Control

The web interface automatically shows/hides tabs based on configuration:

- **Flow Control Tab**: Shown if `RIO_FLOW_ENABLED=true` or if flow controller is initialized and has data
- **Heater Tab**: Shown if `RIO_HEATER_ENABLED=true` or if heaters are initialized and have data
- **Droplet Detection Tab**: Shown if `RIO_DROPLET_ANALYSIS_ENABLED=true` and droplet controller is available

For strobe-only configurations, set:
```bash
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false
```

This will hide the unused tabs in the web interface.

## Important Notes

- **Camera Resolution**: Can be adjusted via the web interface (Camera Configuration tab)
- **Framerate**: Automatically optimized from strobe timing (use "Optimize" button in UI)
- **Config files**: Show initial defaults; UI settings override config file defaults
- YAML files are for documentation - actual configuration is via environment variables

## More Information

## Configuration quick reference (platform presets, control modes, ports)

<details>
<summary><strong>Platform presets (recommended starting points)</strong></summary>

### 1) Strobe-only (32-bit) + droplet detection

- **Example file**: `config-example-strobe-only-32bit.yaml`
- **Key env**:

```bash
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false
```

- **Notes**:
  - Uses PIC-paced timing (strobe timing drives camera exposure).
  - Camera is the Pi camera using the legacy stack (32-bit / `picamera`).

</details>


<details>
<summary><strong>SPI port assignments (BOARD numbering)</strong></summary>

These are the “chip select” ports used by `software/drivers/spi_handler.py` (BOARD numbering):

| Component | Port (BOARD) |
|---|---:|
| Strobe | 24 |
| Flow | 26 |
| Heater 1 | 31 |
| Heater 2 | 33 |
| Heater 3 | 32 |
| Heater 4 | 36 |

</details>

<details>
<summary><strong>How to run (hardware vs simulation)</strong></summary>

From `software/`:

```bash
cd software

# Hardware mode
export RIO_SIMULATION=false
python main.py

# Simulation mode (no hardware)
export RIO_SIMULATION=true
python main.py
```

</details>


