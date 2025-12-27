# Configuration Quick Reference

This document provides a quick overview of configuration options for different platform setups.

---

## Platform Configurations

### 1. Strobe Only (32-bit) with Droplet Detection

**File:** `software/configurations/config-example-strobe-only-32bit.yaml`

**Hardware:**
- 32-bit Raspberry Pi OS
- Strobe module
- Raspberry Pi Camera V2 (Sony IMX219, 3280 × 2464 pixels)

**Key Settings:**
```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
```

**Configuration Highlights:**
- Strobe port: 24 (SPI device select, GPIO pin 24 BOARD numbering)
- Camera type: `rpi` (32-bit compatible, requires picamera package)
- Control mode: `strobe-centric` (software trigger, strobe timing controls exposure)
- Droplet detection: Enabled
- Flow controller: Not included
- Heaters: Not included

**Firmware Requirement:** Firmware with software trigger support. Only available on 32-bit due to picamera package limitation.

**Resolution & Framerate:** 
- Display resolution: Adjustable via web interface (Camera Configuration tab)
- Available presets: 640×480, 800×600, 1024×768, 1280×960, 1920×1080
- Snapshot resolution: Selectable via UI (display or full 3280×2464)
- Framerate: Automatically optimized from strobe timing (use "Optimize" button)

---

### 2. Strobe Only (64-bit) with Droplet Detection

**File:** `software/configurations/config-example-strobe-only-64bit.yaml`

**Hardware:**
- 64-bit Raspberry Pi OS
- Strobe module
- Raspberry Pi Camera V2 or HQ Camera

**Key Settings:**
```bash
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
```

**Configuration Highlights:**
- Strobe port: 24 (SPI device select, GPIO pin 24 BOARD numbering)
- Camera type: `rpi` (V2 Camera) or `rpi_hq` (HQ Camera)
- Control mode: `camera-centric` (hardware trigger, camera frame callback triggers strobe)
- GPIO trigger: Pin 18 (BCM numbering) required for camera-strobe sync
- Droplet detection: Enabled
- Flow controller: Not included
- Heaters: Not included

**Firmware Requirement:** New firmware with hardware trigger support

**Resolution & Framerate:** 
- Display resolution: Adjustable via web interface (Camera Configuration tab)
- Available presets: 640×480, 800×600, 1024×768, 1280×960, 1920×1080
- Snapshot resolution: Selectable via UI (display or full sensor resolution)
  - V2 Camera: 3280×2464 pixels
  - HQ Camera: ~4056×3040 pixels
- Framerate: Automatically optimized from strobe timing (use "Optimize" button)

---

### 3. Full Features (64-bit) with Droplet Detection

**File:** `software/configurations/config-example-full-features-64bit.yaml`

**Hardware:**
- 64-bit Raspberry Pi OS
- Strobe module
- Flow controller (4 channels)
- Heaters (4 units)
- Raspberry Pi HQ Camera (recommended) or V2 camera
- Droplet detection enabled

**Key Settings:**
```bash
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
```

**Configuration Highlights:**
- Strobe port: 24 (SPI device select, GPIO pin 24 BOARD numbering)
- Flow port: 26 (SPI device select, GPIO pin 26 BOARD numbering)
- Heater ports: 31, 33, 32, 36 (SPI device select, GPIO pins BOARD numbering)
- Camera type: `rpi_hq` (HQ Camera, recommended) or `rpi` (V2 Camera)
- Control mode: `camera-centric` (hardware trigger, camera frame callback triggers strobe)
- GPIO trigger: Pin 18 (BCM numbering) required for camera-strobe sync
- Droplet detection: Enabled

**Firmware Requirement:** New firmware with hardware trigger support

**Resolution & Framerate:** 
- Display resolution: Adjustable via web interface (Camera Configuration tab)
- Available presets: 640×480, 800×600, 1024×768, 1280×960, 1920×1080
- Snapshot resolution: Selectable via UI (display or full sensor resolution)
  - V2 Camera: 3280×2464 pixels
  - HQ Camera: ~4056×3040 pixels
- Framerate: Automatically optimized from strobe timing (use "Optimize" button)

---

## Configuration Methods

### Method 1: Environment Variables (Current)

The system currently uses environment variables for configuration:

```bash
# Required for strobe control mode (choose based on your firmware)
export RIO_STROBE_CONTROL_MODE=strobe-centric  # For firmware with software trigger (32-bit only)
# OR
export RIO_STROBE_CONTROL_MODE=camera-centric  # For firmware with hardware trigger

# Optional
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
```

**For desktop launchers:** Add environment variables in the Exec line:
```ini
Exec=env RIO_STROBE_CONTROL_MODE=strobe-centric python /path/to/main.py
```

### Method 2: Direct Code Edit

Edit `software/config.py`:

```python
STROBE_CONTROL_MODE = os.getenv("RIO_STROBE_CONTROL_MODE", "strobe-centric").lower()
```

Use `"strobe-centric"` as default for 32-bit systems with old firmware, or `"camera-centric"` for systems with new firmware.

### Method 3: YAML Configuration (Documentation)

The YAML example files (`config-example-*.yaml`) serve as documentation and show default values. 
- Camera resolution and snapshot settings can be adjusted via the web interface (Camera Configuration tab)
- YAML values are initial defaults only; UI settings take precedence once the application is running
- The YAML format may be used for future configuration system enhancements

---

## Strobe Control Modes

### Strobe-Centric Mode (`RIO_STROBE_CONTROL_MODE=strobe-centric`)

- **Trigger:** Software trigger (trigger_mode = 0)
- **Control:** Strobe timing controls camera exposure
- **Frame Callback:** Not used
- **GPIO:** Minimal use (GPIO pin 18 optional, not required)
- **Firmware:** Compatible with firmware that supports software trigger mode
- **Platform:** 32-bit Raspberry Pi OS only (requires picamera package)
- **Use Case:** Existing working 32-bit systems. This mode works perfectly fine.
- **Note:** Replaced by camera-centric mode with new strobe chip firmware, but fully functional.

### Camera-Centric Mode (`RIO_STROBE_CONTROL_MODE=camera-centric`)

- **Trigger:** Hardware trigger (trigger_mode = 1)
- **Control:** Camera frame callback triggers strobe via GPIO
- **Frame Callback:** Used to trigger PIC via GPIO pin 18 (BCM numbering)
- **GPIO:** GPIO pin 18 (BCM) required for trigger signal
- **Firmware:** Requires new firmware with hardware trigger support
- **Platform:** 32-bit or 64-bit (uses picamera2 on 64-bit)
- **Use Case:** New hardware/firmware deployment or when better synchronization is needed

---

## SPI Port Assignments

| Component | Port (BOARD) | Purpose                    |
|-----------|--------------|----------------------------|
| Strobe    | 24           | SPI device select (GPIO 24)|
| Flow      | 26           | SPI device select (GPIO 26)|
| Heater 1  | 31           | SPI device select (GPIO 31)|
| Heater 2  | 33           | SPI device select (GPIO 33)|
| Heater 3  | 32           | SPI device select (GPIO 32)|
| Heater 4  | 36           | SPI device select (GPIO 36)|

**Note:** 
- Ports use BOARD numbering (physical pin numbers)
- GPIO pin 18 (BCM numbering) is used for camera-strobe trigger signal in camera-centric mode only
- SPI communication uses 30 kHz speed with reply pause times (0.1s for strobe/flow, 0.05s for heaters)
- Reply pause allows PIC microcontrollers time to process commands (~10 commands/sec for strobe/flow)

---

## Camera Types

| Type      | Architecture | Description                                           |
|-----------|--------------|-------------------------------------------------------|
| `none`    | Any          | No camera                                             |
| `rpi`     | 32-bit       | Raspberry Pi Camera V2 (Sony IMX219, 3280×2464 pixels)|
| `rpi`     | 64-bit       | Raspberry Pi Camera V2 (uses picamera2)               |
| `rpi_hq`  | 64-bit       | Raspberry Pi HQ Camera (12.3 megapixels)              |
| `mako`    | Any          | MAKO camera (requires vimba-python driver)            |

**Note:** 
- Camera resolution settings can now be adjusted via the web interface (Camera Configuration tab)
- Default resolution is 1024×768, but can be changed to any preset (640×480 to 1920×1080)
- Full sensor resolution is available for snapshots via the UI
- Lower display resolutions improve streaming performance and bandwidth
- Framerate is automatically calculated from strobe timing and optimized via the "Optimize" button

---

## Quick Start

### For Strobe Only 32-bit System (with droplet detection):

```bash
cd /home/pi/open-microfluidics-workstation/software
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

**Config file:** `software/configurations/config-example-strobe-only-32bit.yaml`

### For Strobe Only 64-bit System (with droplet detection):

```bash
cd /home/pi/open-microfluidics-workstation/software
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

**Config file:** `software/configurations/config-example-strobe-only-64bit.yaml`

### For Full Features 64-bit Platform (with droplet detection):

```bash
cd /home/pi/open-microfluidics-workstation/software
export RIO_STROBE_CONTROL_MODE=camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

**Config file:** `software/configurations/config-example-full-features-64bit.yaml`

---

## Verification

After starting the application, check logs for:

**Strobe-centric mode:**
```
INFO - Strobe control mode: strobe-centric (hardware_trigger=False)
INFO - Strobe configured for software trigger mode
```

**Camera-centric mode:**
```
INFO - Strobe control mode: camera-centric (hardware_trigger=True)
INFO - Strobe configured for hardware trigger mode
```

---

## Troubleshooting

### Wrong Mode Selected

**Problem:** Logs show incorrect control mode

**Solution:**
1. Check environment variable: `echo $RIO_STROBE_CONTROL_MODE`
2. Verify before running: `export RIO_STROBE_CONTROL_MODE=strobe-centric` (or `camera-centric`)
3. Check config.py default value if environment variable not set
4. For desktop launchers, ensure environment variable is set in the Exec line

### Hardware Not Detected

**Problem:** Components not responding

**Solution:**
1. Verify SPI is enabled: `sudo raspi-config` → Interface Options → SPI → Enable
2. Check port assignments match hardware connections
3. Verify power supply and connections
4. Check SPI bus and mode settings

### Camera Issues

**Problem:** Camera initialization fails

**Solution:**
1. Verify camera is enabled: `vcgencmd get_camera`
2. Test camera:
   - 32-bit: `raspistill -o test.jpg`
   - 64-bit: `libcamera-hello`
3. Check camera type matches your hardware

---

## Resolution and Framerate Configuration

### Via Web Interface (Recommended)

Camera resolution and snapshot settings can now be configured directly in the web interface:

1. **Display Resolution**: 
   - Navigate to "Camera Configuration" tab
   - Select from presets: 640×480, 800×600, 1024×768, 1280×960, 1920×1080
   - Camera will automatically restart with new resolution

2. **Snapshot Resolution**:
   - Same tab, "Snapshot Resolution" dropdown
   - Options: "Use Display Resolution" (fast) or "Full Sensor Resolution" (high quality)
   - Full resolution: 3280×2464 (V2) or ~4056×3040 (HQ Camera)

3. **Framerate**:
   - Automatically calculated from strobe timing parameters
   - Use the "Optimize" button to fine-tune framerate based on camera read time
   - Displayed in real-time in the strobe control section

### Configuration Files

The YAML configuration files show default values, but these are overridden by UI settings once the application is running. The config files serve as:
- Documentation of hardware capabilities
- Initial defaults when the application starts
- Reference for environment variable setup

---

## Additional Resources

- [Raspberry Pi Update Guide](../docs/raspberry-pi-update-guide.md) - Complete migration instructions
- Pre-configurations (in this directory):
  - `config-example-strobe-only-32bit.yaml` - Strobe only 32-bit
  - `config-example-strobe-only-64bit.yaml` - Strobe only 64-bit
  - `config-example-full-features-64bit.yaml` - Full features 64-bit
- Legacy detailed examples (in this directory):
  - `config-example-strobe-centric-32bit.yaml` - Detailed strobe-centric 32-bit example
  - `config-example-camera-centric-64bit.yaml` - Detailed camera-centric 64-bit example
