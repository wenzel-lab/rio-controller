## Purpose and Scope

This document is a **permanent repository guide**: it explains how the Rio controller repo is organized and how the major parts fit together, and it links to the authoritative READMEs for setup and usage. It **should not** contain step-by-step installation instructions, troubleshooting logs, release notes, or deep implementation details (those belong in the relevant subdirectory READMEs).

## Documentation Gradient (how to read this repo)

- **Top-level docs** (this file, `/README.md`): newcomer- and user-oriented (“what is this, what do I need, where do I start?”).
- **Subsystem READMEs** (`software/`, `pi-deployment/`, `hardware-modules/*/`): practitioner-oriented (“how do I run/deploy this module?”).
- **Deep subfolders** (`software/controllers/`, `software/drivers/`, `software/tests/`, firmware folders): developer/AI-agent oriented (“how it works, invariants, how to change safely without forking logic”).

## What this repository contains

Rio is a modular microfluidics controller consisting of:
- **Open hardware designs and firmware** for a Raspberry Pi HAT and pluggable modules.
- **Python control software** (web UI + device control logic) that runs on a Raspberry Pi or in a simulation mode on a developer machine.

Start here:
- Project overview: [`README.md`](README.md)
- Software installation/usage: [`software/README.md`](software/README.md)
- Raspberry Pi deployment package usage: [`pi-deployment/README.md`](pi-deployment/README.md)

## Repository Structure (high level)

- **`hardware-modules/`**: open-hardware module designs (BOMs, images, PCB files, and PIC firmware projects).
  - **Core board / interface**: Pi HAT (`hardware-modules/rpi-hat/`)
  - **Modules**:
    - Strobe imaging: `hardware-modules/strobe-imaging/` (firmware in `strobe_pic/`)
    - Pressure/flow control: `hardware-modules/pressure-flow-control/` (firmware in `pressure_and_flow_pic/`)
    - Heating/stirring: `hardware-modules/heating-stirring/` (firmware in `sample_holder_pic/`)
  - **Notes**:
    - Firmware folders are MPLAB X projects and include generated output (`build/`, `dist/`) and generated sources (`mcc_generated_files/`).

- **`software/`**: primary source-of-truth for the Python application.
  - Entry point: `software/main.py`
  - Configuration/constants: `software/config.py` + example configs under `software/configurations/`
  - Drivers (hardware adapters): `software/drivers/` (camera backends under `software/drivers/camera/`)
  - Device controllers (business logic): `software/controllers/`
  - Web app (Flask UI): `software/rio-webapp/` (web controllers under `software/rio-webapp/controllers/`)
  - Droplet detection pipeline: `software/droplet-detection/`
  - Simulation layer (no-hardware dev/testing): `software/simulation/`
  - Tests: `software/tests/` (pytest config in `software/pyproject.toml`)

- **`pi-deployment/`**: Raspberry Pi deployment bundle generated from `software/`.
  - Purpose: a minimal, runnable copy for Pi updates (scripts + requirements + code subset).
  - Policy: treat as a build artifact/distribution output, not a second source tree.

- **Root-level operational scripts**:
  - `create-pi-deployment.sh`: generates `pi-deployment/` from `software/`
  - `deploy-to-pi.sh`: ships a deployment bundle to a Pi over SSH
  - `SOCKETIO_UPGRADE_PI.sh` and related scripts: targeted upgrade/troubleshooting helpers

- **Metadata**:
  - `okh-manifest.yml`: Open Know-How manifest linking hardware modules and software
  - `LICENSE.md`: repository licensing summary

- **`docs/`**: **temporary audit/planning output only** (should not be referenced by permanent docs or runtime code).

## Documentation map (recommended reading order)

This repo is easiest to understand by reading from shallow → deep:

### 1) Entry points

- Project overview: [`README.md`](README.md)
- System/repo guide: [`ARCHITECTURE.md`](ARCHITECTURE.md)

### 2) Hardware modules (assembly + usage)

- Pi HAT: [`hardware-modules/rpi-hat/README.md`](hardware-modules/rpi-hat/README.md)
- Strobe imaging module: [`hardware-modules/strobe-imaging/README.md`](hardware-modules/strobe-imaging/README.md)
- Pressure/flow module: [`hardware-modules/pressure-flow-control/README.md`](hardware-modules/pressure-flow-control/README.md)
- Heating/stirring module: [`hardware-modules/heating-stirring/README.md`](hardware-modules/heating-stirring/README.md)

### 3) Firmware (developer-facing)

- Strobe firmware: [`hardware-modules/strobe-imaging/strobe_pic/README.md`](hardware-modules/strobe-imaging/strobe_pic/README.md)
- Pressure/flow firmware: [`hardware-modules/pressure-flow-control/pressure_and_flow_pic/README.md`](hardware-modules/pressure-flow-control/pressure_and_flow_pic/README.md)
- Heating/stirring firmware: [`hardware-modules/heating-stirring/sample_holder_pic/README.md`](hardware-modules/heating-stirring/sample_holder_pic/README.md)

### 4) Software (practitioner + developer)

- Software root guide: [`software/README.md`](software/README.md)
- Device controllers: [`software/controllers/README.md`](software/controllers/README.md)
- Drivers: [`software/drivers/README.md`](software/drivers/README.md)
- Camera drivers: [`software/drivers/camera/README.md`](software/drivers/camera/README.md)
- Web app: [`software/rio-webapp/README.md`](software/rio-webapp/README.md)
- Web controllers: [`software/rio-webapp/controllers/README.md`](software/rio-webapp/controllers/README.md)
- Droplet detection pipeline: [`software/droplet-detection/README.md`](software/droplet-detection/README.md)
- Simulation layer: [`software/simulation/README.md`](software/simulation/README.md)
- Tests: [`software/tests/README.md`](software/tests/README.md)
- Configuration examples: [`software/configurations/README.md`](software/configurations/README.md)

### 5) Deployment (practitioner)

- Raspberry Pi deployment bundle: [`pi-deployment/README.md`](pi-deployment/README.md)
- Example deployment configs: [`pi-deployment/configurations/README.md`](pi-deployment/configurations/README.md)

## Conceptual Architecture (system level)

At runtime, the software is layered roughly as:
- **Drivers** (`software/drivers/`): low-level SPI/GPIO and device-specific hardware access; camera abstraction.
- **Device controllers** (`software/controllers/`): state + business logic orchestrating drivers (flow, heater, camera, strobe integration, droplet detector controller).
- **Web app** (`software/rio-webapp/`): Flask routes/templates/static assets and WebSocket handlers; presents the UI and translates user commands into controller calls.
- **Droplet detection pipeline** (`software/droplet-detection/`): image-processing pipeline and utilities (tests/benchmarks/optimization live alongside this code in `software/`).
- **Simulation** (`software/simulation/`): drop-in replacements so development/testing can run without physical hardware.

Terminology note used throughout the repo:
- **Device controller**: hardware control logic/state (in `software/controllers/`).
- **Web controller**: request/WebSocket handling (in `software/rio-webapp/controllers/`).

## Configuration (what decides which parts run)

Configuration is primarily driven by environment variables (`RIO_*`) plus a small number of config/constants in `software/config.py`.
- **Hardware vs simulation**: routine dev/tests use `RIO_SIMULATION=true`; hardware runs use `RIO_SIMULATION=false`.
- **Feature toggles**: modules such as droplet analysis, flow, heater can be enabled/disabled via env vars (see `software/README.md` and `pi-deployment/README.md`).
- **Control mode**: strobe-centric vs camera-centric mode is selected via `RIO_STROBE_CONTROL_MODE` (see deployment/software docs).

Example configuration files live under:
- [`software/configurations/`](software/configurations/)
- [`pi-deployment/configurations/`](pi-deployment/configurations/)

## Deployment and the role of `pi-deployment/`

`pi-deployment/` exists to make it easy to update a Raspberry Pi with a minimal set of files.

Important policy:
- **Source-of-truth**: `software/` is the source-of-truth for application code.
- **Build artifact**: `pi-deployment/` is intended to be *generated* from `software/` (see `create-pi-deployment.sh`) and should not become an independently maintained fork.

Recommended usage:
- **Developers**: develop and run tests from `software/` (simulation mode unless explicitly testing hardware).
- **End users**: obtain a ready-to-use deployment bundle (ideally via a release artifact) or generate it locally using `create-pi-deployment.sh`.


