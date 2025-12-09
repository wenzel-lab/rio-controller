# Quick Fix: Simulation Mode Setup

## Issue Fixed

The `picommon.py` was trying to import `spidev` which isn't available on Mac/PC. This has been fixed to automatically use simulated hardware when `RIO_SIMULATION=true`.

## What Was Changed

1. ✅ Created `rio-config.yaml` file in repository root
2. ✅ Updated `picommon.py` to detect simulation mode and use simulated SPI/GPIO
3. ✅ Made YAML import optional (config works with just environment variables)

## How to Run Now

### Step 1: Install PyYAML (if you want YAML config support)

```bash
mamba activate rio-simulation
pip install PyYAML
```

**Note:** YAML is optional - you can use just the environment variable method.

### Step 2: Enable Simulation Mode

```bash
export RIO_SIMULATION=true
```

### Step 3: Run the Webapp

```bash
cd user-interface-software/src/webapp
python pi_webapp.py
```

## What Happens Now

When `RIO_SIMULATION=true`:
- ✅ `picommon.py` automatically uses `SimulatedSPIHandler` instead of `spidev`
- ✅ `picommon.py` automatically uses `SimulatedGPIO` instead of `RPi.GPIO`
- ✅ All SPI/GPIO operations are simulated
- ✅ No hardware libraries needed

## Verification

You should see this message when running:
```
[picommon] Using simulated SPI/GPIO (simulation mode)
[SimulatedSPIHandler] Initialized (bus=0, mode=2, speed=30000Hz)
```

If you see errors about missing modules, make sure:
1. Environment is activated: `mamba activate rio-simulation`
2. Simulation mode is enabled: `export RIO_SIMULATION=true`
3. You're in the correct directory: `user-interface-software/src/webapp`

