## AI-generated notice

This file was AI-generated and may contain errors. Please verify against source code and hardware behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change firmware behavior or host protocol, please update this document.

## Purpose

Firmware for the **Heating and Stirring (Sample Holder) Module** PIC controller. It communicates with the host over SPI and implements:
- temperature sensing and reporting
- heater control (PID + power limiting)
- optional PID autotune workflow
- stirring control and status reporting
- persistence of key parameters to EEPROM

## Project structure (what to edit)

- **Main logic + protocol handlers**: `main.c`
- **SPI packet transport**: `spi.c`, `spi.h` (packet framing, checksum, timeouts)
- **Non-volatile storage**:
  - `storage.c/h` (persistent PID parameters, power limit, targets, run-on-start)
  - `eeprom.c/h` (EEPROM access)
- **MCC-generated peripherals**: `mcc_generated_files/` (do not hand-edit)

## Build and flash (MPLAB X)

Typical workflow:
1. Open the `sample_holder_pic` project in **MPLAB X IDE**.
2. Select your PIC programmer configuration (PICkit, etc.).
3. Build/flash.

Toolchain/device details are encoded in the MPLAB project (`nbproject/`) and MCU headers in `main.c`.

## SPI interface (host protocol)

### Packet framing

The SPI packet format is documented in `spi_packet_read()`:
- `[STX=2][size][packet_type][data...][checksum]`
- Checksum is defined so that the sum over `(STX + size + packet_type + data + checksum)` equals 0 modulo 256.

The dsPIC implementations also include timeout tracking (`ERR_PACKET_TIMEOUT`) via `spi_packet_init()` and a millisecond timer.

### Packet types (from `main.c`)

- `1` **GET_ID**
- `2` **TEMP_SET_TARGET**
- `3` **TEMP_GET_TARGET**
- `4` **TEMP_GET_ACTUAL**
- `5` **PID_SET_COEFFS**
- `6` **PID_GET_COEFFS**
- `7` **PID_SET_RUNNING**
- `8` **PID_GET_STATUS**
- `9` **AUTOTUNE_SET_RUNNING**
- `10` **AUTOTUNE_GET_RUNNING**
- `11` **AUTOTUNE_GET_STATUS**
- `12` **STIR_SET_RUNNING**
- `13` **STIR_GET_STATUS**
- `14` **STIR_SPEED_GET_ACTUAL**
- `15` **HEAT_POWER_LIMIT_SET**
- `16` **HEAT_POWER_LIMIT_GET**

Payload formats are defined in `main.c` (see the packet handling switch). Treat `main.c` + `spi_packet_*` code as the source-of-truth for host-side drivers.

## Persisted parameters

`storage.c` persists a compact struct including:
- PID coefficients
- temperature targets (scaled)
- run-on-start flag
- heater power limit (%)

If you change storage layout, update versioning and any host assumptions.


