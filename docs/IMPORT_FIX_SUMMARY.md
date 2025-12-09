# Import Error Fix Summary

## Issue Fixed

**Error**: `ImportError: cannot import name 'spi' from 'spi_handler'`

**Location**: `drivers/heater.py`, `drivers/flow.py`, `drivers/strobe.py`

## Root Cause

The `spi` variable is a **global variable** that's initialized by `spi_init()`, not a directly importable constant. You cannot import a global variable that doesn't exist yet.

## Solution

Changed all driver files to:
1. Import the `spi_handler` module (not individual names)
2. Access `spi_handler.spi` after `spi_init()` is called
3. Access functions as `spi_handler.spi_select_device()`, etc.

## Changes Made

### Before (Broken):
```python
from spi_handler import spi_select_device, spi_deselect_current, spi_lock, spi_release, pi_wait_s, spi
# ...
spi.xfer2([0])  # Error: spi not importable
```

### After (Fixed):
```python
import spi_handler
# ...
spi_handler.spi.xfer2([0])  # Works: access via module after initialization
spi_handler.spi_select_device(port)  # Works: access function via module
```

## Files Updated

- ✅ `drivers/heater.py` - All `spi` and function calls updated
- ✅ `drivers/flow.py` - All `spi` and function calls updated  
- ✅ `drivers/strobe.py` - All `spi` and function calls updated

## Verification

```bash
cd software
RIO_SIMULATION=true python3 -c "import sys; sys.path.insert(0, '.'); from drivers.heater import PiHolder; print('✓ OK')"
```

✅ All imports now work correctly.

