## AI-generated notice

This file was AI-generated and may contain errors. Please verify against source code and hardware behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change firmware behavior or host protocol, please update this document.

## Purpose

Firmware for the **Pressure and Flow Control Module** PIC controller. It communicates with the host (Raspberry Pi) over SPI and implements:
- pressure setpoint output (DAC) and pressure readback (ADC)
- optional flow sensing over I2C (Sensirion)
- closed-loop flow control (FPID) with persisted PID constants

## Project structure (what to edit)

- **Main logic + protocol handlers**: `main.c`
- **SPI packet transport**: `spi.c`, `spi.h` (packet framing, checksum, timeouts)
- **I2C devices**:
  - ADC: `ads1115.c/h`
  - I2C mux: `pca9544a.c/h`
  - Flow sensor: `sensirion_lg16.c/h`
- **Non-volatile storage**:
  - `storage.c/h` (persistent FPID constants per channel)
  - `eeprom.c/h` (EEPROM access)
- **MCC-generated peripherals**: `mcc_generated_files/` (do not hand-edit)

## Build and flash (MPLAB X)

Typical workflow:
1. Open the `pressure_and_flow_pic` project in **MPLAB X IDE**.
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
- `2` **SET_PRESSURE_TARGET**
- `3` **GET_PRESSURE_TARGET**
- `4` **GET_PRESSURE_ACTUAL**
- `5` **SET_FLOW_TARGET**
- `6` **GET_FLOW_TARGET**
- `7` **GET_FLOW_ACTUAL**
- `8` **SET_CONTROL_MODE**
- `9` **GET_CONTROL_MODE**
- `10` **SET_FPID_CONSTS**
- `11` **GET_FPID_CONSTS**

Payload formats are defined in `main.c` (see the packet handling switch). Treat `main.c` + `spi_packet_*` code as the source-of-truth for host-side drivers.

## Persisted parameters

`storage.c` persists:
- `pid_consts[NUM_PRESSURE_CLTRLS][3]` (per-channel PID constants)
- an EEPROM version field

If you change storage layout, update versioning and any host assumptions.


