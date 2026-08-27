#!/usr/bin/env bash
# Probe whether the strobe PIC accepts hardware-trigger mode (SPI packet type 5).
# Run on the Raspberry Pi with the API stopped (SPI exclusive).
#
# Usage (on Pi):
#   sudo systemctl stop rio-api  # or pkill -f 'python3 -m api.main'
#   cd ~/rio-controller && PYTHONPATH=. RIO_SIMULATION=false ./scripts/probe_strobe_trigger_mode.sh
#
# If set_trigger_mode returns False, flash:
#   hardware-modules/strobe-imaging/strobe_pic/main_hardware_trigger.c
#   (+ interrupt_manager_hardware_trigger.c) via MPLAB X / PICkit.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
export RIO_SIMULATION="${RIO_SIMULATION:-false}"
python3 - <<'PY'
from drivers.spi_handler import spi_init, PORT_STROBE
from drivers.strobe import PiStrobe
from config import STROBE_REPLY_PAUSE_S

spi_init(0, 2, 30000)
s = PiStrobe(PORT_STROBE, STROBE_REPLY_PAUSE_S)
ok_on = s.set_trigger_mode(True)
ok_off = s.set_trigger_mode(False)
print(f"set_trigger_mode(True)={ok_on}")
print(f"set_trigger_mode(False)={ok_off}")
if ok_on:
    print("OK: PIC supports hardware trigger (packet type 5).")
else:
    print(
        "FAIL: PIC firmware likely lacks hardware-trigger support. "
        "Flash main_hardware_trigger.c for Daheng LineOut → T1G sync."
    )
    raise SystemExit(1)
PY
