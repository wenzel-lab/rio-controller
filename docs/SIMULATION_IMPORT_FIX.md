# Simulation Mode Import Fixes

## Issue
Multiple files were directly importing `spidev` and `RPi.GPIO`, which aren't available on Mac/PC, causing `ModuleNotFoundError` even when simulation mode was enabled.

## Files Fixed

### ✅ `picommon.py`
- Now detects `RIO_SIMULATION` environment variable
- Automatically uses `SimulatedSPIHandler` and `SimulatedGPIO` in simulation mode
- Falls back to real hardware when not in simulation mode

### ✅ `pistrobe.py`
- Removed unused `import spidev` (wasn't actually used)
- Uses `picommon.spi` which handles simulation automatically

### ✅ `piflow.py`
- Removed unused `import spidev` (wasn't actually used)
- Uses `picommon.spi` which handles simulation automatically

### ✅ `piholder.py`
- Removed unused `import spidev` (wasn't actually used)
- Uses `picommon.spi` which handles simulation automatically

### ✅ `pistrobecam.py`
- Changed from `import RPi.GPIO as GPIO` to `GPIO = picommon.GPIO`
- Now uses the GPIO from picommon which handles simulation automatically

## How It Works

1. **`picommon.py`** checks `RIO_SIMULATION` environment variable at import time
2. If simulation mode: imports and uses `SimulatedSPIHandler` and `SimulatedGPIO`
3. If real hardware: imports and uses `spidev` and `RPi.GPIO`
4. All other files use `picommon.spi` and `picommon.GPIO`, which automatically work in both modes

## Usage

```bash
# Enable simulation mode
export RIO_SIMULATION=true

# Run webapp
cd user-interface-software/src/webapp
python pi_webapp.py
```

You should see:
```
[picommon] Using simulated SPI/GPIO (simulation mode)
[SimulatedSPIHandler] Initialized (bus=0, mode=2, speed=30000Hz)
```

## Verification

All hardware imports are now handled through `picommon`, which means:
- ✅ No direct `spidev` imports in device files
- ✅ No direct `RPi.GPIO` imports in device files
- ✅ All hardware access goes through `picommon`
- ✅ Simulation mode works automatically when `RIO_SIMULATION=true`

