"""
Canonical mapping between flow-control "firmware modes" and "UI modes".

Why this exists:
- Historically, the mapping logic lived in multiple places (config, device controller,
  web controller, view model). That made it easy for changes to drift.
- Track 2 of Phase B makes this mapping a single source-of-truth and imports it everywhere.
"""

from __future__ import annotations

# UI control modes (indices into the string list below):
#   0 = Off
#   1 = Set Pressure
#   2 = Flow Closed Loop
FLOW_CTRL_MODE_STR = ["Off", "Set Pressure", "Flow Closed Loop"]

# Firmware control modes (from the pressure/flow PIC firmware):
#   0 = Off
#   1 = Pressure Open Loop
#   2 = Pressure Closed Loop (deprecated / hidden in UI)
#   3 = Flow Closed Loop
#
# Note: Firmware mode 2 is intentionally mapped to UI mode 0 to hide it.
CONTROL_MODE_FIRMWARE_TO_UI = {
    0: 0,  # Off -> Off
    1: 1,  # Pressure Open Loop -> Set Pressure
    2: 0,  # Pressure Closed Loop (hidden) -> Off
    3: 2,  # Flow Closed Loop -> Flow Closed Loop
}

CONTROL_MODE_UI_TO_FIRMWARE = {
    0: 0,  # Off -> Off
    1: 1,  # Set Pressure -> Pressure Open Loop
    2: 3,  # Flow Closed Loop -> Flow Closed Loop
}
