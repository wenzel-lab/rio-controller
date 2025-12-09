# Code Fix Summary - UnboundLocalError in heater.py

## Issue Fixed

**Error**: `UnboundLocalError: local variable 'valid' referenced before assignment`

**Location**: `software/drivers/heater.py`, `packet_query()` method

**Root Cause**: The variables `valid` and `data_read` were not initialized before the try block. If an exception occurred before they were set, the return statement would fail.

## Solution

Initialized `valid` and `data_read` before the try block and ensured they're set even on exceptions:

```python
def packet_query( self, type, data ):
    valid = False  # Initialize before try block
    data_read = []  # Initialize before try block
    try:
        # ... existing code ...
    except Exception as e:
        # ... error handling ...
        valid = False
        data_read = []
    finally:
        # ... cleanup ...
    return valid, data_read
```

## Files Fixed

- ✅ `software/drivers/heater.py` - Fixed `packet_query()` method
- ✅ `software/drivers/flow.py` - Applied same fix for consistency

## Verification

```bash
cd software
RIO_SIMULATION=true python3 -c "from drivers.heater import PiHolder; print('✓ OK')"
```

✅ Import and initialization now work correctly.

