# Flash strobe PIC for Daheng frame-accurate hardware trigger

## Why

The host (CoolerMaster) already:

1. Drives Daheng **LineOut = ExposureActive** on strobe Enable
2. Calls SPI `set_trigger_mode(1)` then `enable`

Frame-to-frame sync needs firmware that speaks packet **5** (`SET_TRIGGER_MODE`)
*and* actually fires on the trigger edge. Firmware **v3** is the first version that
does both; see the defect table below for why earlier attempts did not.

## What to flash

- [`main.c`](main.c) — packets 1–7, polled trigger, LED on RC7 as GPIO
- [`mcc_generated_files/tmr1.c`](mcc_generated_files/tmr1.c) — `T1GCON` set for
  continuous gating so TMR1 measures the camera readout gap
- [`mcc_generated_files/interrupt_manager.c`](mcc_generated_files/interrupt_manager.c) — SPI ISR

`main_hardware_trigger.c` and `interrupt_manager_hardware_trigger.c` are
superseded drafts, excluded from the build. **Do not flash them.**

Device: **PIC16F18856 / PIC16F18857** (as in the MCC project).

## Wiring (hybrid)

```
Daheng MER2 opto LineOut (ExposureActive, default Line2 / env RIO_DAHENG_STROBE_LINE)
    ->  strobe board trigger input (PIC RC5, active low)
GND common between camera I/O and strobe board
```

RC5 has a weak internal pull-up, so the line idles at 3.3 V and the camera opto
pulls it to 0 V while exposing. Exposure start is a **falling** edge.

USB Daheng stays on CoolerMaster. Strobe SPI stays on the Raspberry Pi.

## Flash steps (MPLAB X + PICkit3/4)

1. Connect **PICkit** to the strobe programming header (see module README images).
2. Open `hardware-modules/strobe-imaging/strobe_pic/` in **MPLAB X**.
3. Select config **PICkit3** or **PICkit4**.
4. **Clean and Build**, then **Make and Program Device**
   (do not use “Program Device” alone — that can flash a stale hex under `dist/`).
5. Power-cycle the strobe board / Pi if needed.

## Verify on the Pi

Stop the Rio API (SPI exclusive), then:

```bash
cd ~/rio-controller
PYTHONPATH=. RIO_SIMULATION=false ./scripts/probe_strobe_trigger_mode.sh
```

Expect: `set_trigger_mode(True)=True`.

Restart the API (`cd ~/rio-controller && RIO_SIMULATION=false PYTHONPATH=. python3 -m api.main`),
restart the CoolerMaster UI, then:

1. Continuous **OFF**
2. Flash width e.g. **100** µs → **Set**
3. **ENABLED**

Host log should show hardware trigger mode ON (not “PIC HW trigger unavailable”).
Light flashes once per Daheng exposure (may look continuous at high Acq.FPS).

## Firmware v3: why the MCC trigger path never worked

Three independent defects, all bypassed in v3:

| Defect | Consequence |
|---|---|
| `TMR1` is gated by RC5 (`T1GE=1`) | TMR1 only counts while the trigger line is high, so it cannot time the flash |
| ISR keys off `TMR1IF` (overflow), not gate-complete | `hardware_trigger_strobe()` is essentially never called during streaming |
| `CLC1/2` + `TMR2/TMR4` latch (`TMR2==PR2` sticks while TMR2 is off) | free-run LED stays dark |

v3 detects the trigger by **polling RC5** for a falling edge and times the flash
with a blocking delay. It also takes the LED off the CLC entirely: `RC7PPS` is set
to `LATxy` so RC7 is a plain GPIO driven by `LATC7`. `LC3G3POL` is still written
alongside it, so if the PPS change were ineffective the previously working CLC3
hold path still drives the pin.

## Verifying v3 without a scope

On boot the firmware blinks the LED **3× 300 ms**. If you see that, build, flash
and LED drive are all good.

Two new SPI packets make the rest observable from the Pi:

- `6 GET_DIAG` — firmware version, live RC5 level, edge counter, flash counter, state
- `7 SELF_TEST` — 5 blinks of 250 ms on demand

```bash
# on the Pi, API stopped (SPI is exclusive)
pkill -f 'python3 -m api.main'
cd ~/rio-controller

PYTHONPATH=. RIO_SIMULATION=false python3 scripts/probe_strobe_diag.py --self-test
PYTHONPATH=. RIO_SIMULATION=false python3 scripts/probe_strobe_diag.py --seconds 30
```

Then stream the camera from the host with a slow, well-defined pulse train —
unconstrained streaming can leave `ExposureActive` at ~100 % duty, which produces
almost no edges and would look continuous anyway:

```bash
export GALAXY_ROOT=$HOME/Galaxy_camera
export LD_LIBRARY_PATH=$GALAXY_ROOT/lib/x86_64
.venv-daheng/bin/python3 /tmp/test_hw_strobe_v3.py --fps 5 --exposure-us 1000
```

Reading the result:

| `edge_count` | `trigger_count` | Conclusion |
|---|---|---|
| 0 | 0 | No signal at the pin — wiring or camera line config, not firmware |
| rising | 0 | Signal arrives, trigger logic wrong |
| rising | rising | Trigger path works |

Judging by eye alone is misleading: wait and flash are software-paced and clamped
to 65535 µs, so the sub-millisecond values the UI uses produce a ~99 % duty cycle
that looks like a steady light, not a blink. For a visible blink use
`--free-run`, which sets 60 ms per phase (~8 Hz).
