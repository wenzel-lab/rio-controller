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
   - Strobe-centric control mode
   - Droplet detection enabled

2. **`config-example-strobe-only-64bit.yaml`**
   - 64-bit Raspberry Pi OS
   - Strobe + Camera
   - Camera-centric control mode
   - Droplet detection enabled

3. **`config-example-full-features-64bit.yaml`**
   - 64-bit Raspberry Pi OS
   - Strobe + Camera + Flow Controller + Heaters
   - Camera-centric control mode
   - Droplet detection enabled

### Detailed Reference Examples

- **`config-example-strobe-centric-32bit.yaml`** - Detailed 32-bit strobe-centric configuration
- **`config-example-camera-centric-64bit.yaml`** - Detailed 64-bit camera-centric configuration

## Documentation

The configuration “quick reference” is included in this README (below) to avoid keeping parallel documentation files in the deployment bundle.

## Usage

Configuration is done via **environment variables**. The YAML files in this folder are **examples / documented presets** (they are not automatically parsed by `pi-deployment/main.py`).

This folder is copied from `software/configurations/` when `create-pi-deployment.sh` generates the deployment bundle.

Example:
```bash
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow control tab (for strobe-only configs)
export RIO_HEATER_ENABLED=false    # Hide heater tab (for strobe-only configs)
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

This bundle is generated from `software/`, so the examples below match the same environment variables used by `pi-deployment/main.py`.

<details>
<summary><strong>Platform presets (recommended starting points)</strong></summary>

### 1) Strobe-only (32-bit) + droplet detection

- **Example file**: `config-example-strobe-only-32bit.yaml`
- **Key env**:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false
```

### 2) Strobe-only (64-bit) + droplet detection

- **Example file**: `config-example-strobe-only-64bit.yaml`
- **Key env**:

```bash
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false
export RIO_HEATER_ENABLED=false
```

### 3) Full features (64-bit) + droplet detection

- **Example file**: `config-example-full-features-64bit.yaml`
- **Key env**:

```bash
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=true
export RIO_HEATER_ENABLED=true
```

</details>

<details>
<summary><strong>Strobe control modes</strong></summary>

### Strobe-centric (`RIO_STROBE_CONTROL_MODE=strobe-centric`)

- Strobe timing is the “clock” (software-trigger style).

### Camera-centric (`RIO_STROBE_CONTROL_MODE=camera-centric`)

- Camera frame callback triggers strobe via GPIO (hardware-trigger style).
- Trigger uses **BCM pin 18** (see `pi-deployment/config.py`).

</details>

<details>
<summary><strong>SPI port assignments (BOARD numbering)</strong></summary>

| Component | Port (BOARD) |
|---|---:|
| Strobe | 24 |
| Flow | 26 |
| Heater 1 | 31 |
| Heater 2 | 33 |
| Heater 3 | 32 |
| Heater 4 | 36 |

</details>


