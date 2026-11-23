# pressure_and_flow_pic firmware v3.0 (2026-11-02)

Base: Pierre's build of 2026-04-09 (`pierre/original_is_actually_v2/firmware`, ADC 475 SPS / 8 ms,
refresh counter, active-sensor mask). That build was reproduced byte-for-byte with XC16 v2.10 +
dsPIC33CK-MP_DFP 1.1.51 before applying these changes (`firmware-build/build.sh`).

Design rule for v3.0: **no change to timing, to the ADC/SPI state machines, or to any existing packet
format.** With no v3 command issued, the PIC behaves exactly like v2 (same boot register write,
same loop), except that CRC-rejected readings no longer overwrite the flow value.

## Changes

| File | Change |
|---|---|
| `sensirion_lg16.c` | `sensirion_measurement_read()` reads 3 bytes `[MSB][LSB][CRC]` and verifies the Sensirion CRC-8 (poly 0x31, init 0x00, check("123456789") = 0xA2). Mismatch -> `ERR_SENSIRION_CRC_FAIL` (71); caller keeps the previous value. |
| `sensirion_lg16.c` | `i2c_wait_for_reply()` reports an address NACK as `ERR_SENSIRION_NOT_READY` (73) instead of the generic comms error. Timing unchanged (still waits the 8 ms timeout). With hold-master disabled a NACK on the read header means "measurement still running" (datasheet §4.5). |
| `sensirion_lg16.c` | New `sensirion_set_resolution(bits)`: drains the pending measurement, writes Advanced User Register bits 11:9, reads back to verify. Register only, never EEPROM (volatile, lost on sensor reset). |
| `main.c` | Per-channel counters `ok / crc_err / i2c_err / not_ready` incremented in `read_flows()`. |
| `main.c` | Boot: resolution bits are written explicitly to the default (16 bit = factory value) in the same register write that already disabled hold-master, so the value written at boot is unchanged. |
| `main.c` | New packets 14..17 (below). `GET_ID` string stays `MICROFLOW`. |
| `common.h` | Error codes 71/72/73, `COPY_32BIT_TO_PTR`. |

## New SPI packets (existing 1..13 unchanged)

| Type | Name | Request | Reply |
|---|---|---|---|
| 14 | GET_FLOW_STATS | `[chan U8]` | `[err][ok U32][crc_err U32][i2c_err U32][not_ready U32]` little-endian |
| 15 | SET_FLOW_RESOLUTION | `[bits U8]` 9..16 | `[err]` — blocks up to ~100 ms per present sensor; host must wait longer for the reply (piflow uses 0.6 s) |
| 16 | GET_FLOW_RESOLUTION | `[]` | `[err][bits U8]` |
| 17 | GET_FW_VERSION | `[]` | `[err][major U8][minor U8]` = 3, 0 |

Resolution vs measurement time (datasheet §4.2 typ.): 16 bit 69 ms, 15 bit 35 ms, 14 bit 17.5 ms,
13 bit 8.9 ms, 12 bit 4.6 ms, 11 bit 2.4 ms, 10 bit 1.3 ms, 9 bit 0.8 ms. Each bit less roughly doubles
sensor noise. 16 bit = precision mode (default); 12–13 bit = fast mode for pulsation studies.

## Interpreting the counters

- `crc_err > 0` while exact-zero samples appear on the Pi -> zeros were corrupted transfers (now rejected).
- `crc_err == 0` and zeros persist -> zeros are produced elsewhere (Pi side / SPI); investigate there.
- `not_ready` is large by design at 16 bit (the 8 ms loop polls a 74 ms measurement). Benign.
- `i2c_err` should stay ~0 in steady state; growth = bus problem (mux, wiring, sensor).

## Host side

`pi-webapp/piflow.py`: `get_fw_version()`, `get_flow_stats(sensor)`, `set_flow_resolution(bits)`,
`get_flow_resolution()`. `pi-webapp/api.py`: `GET /api/flow/firmware`, `GET /api/flow/stats?sensors=1`,
`GET|POST /api/flow/resolution` (`{"bits": 12}`). Existing scripts/notebook need no change.

## Flash procedure (2026-11-03)

1. PICkit: verify device ID (dsPIC33CK256MP502), **read and save** current flash -> `backup-pic-<date>.hex`.
   Compare with `pierre/*/dist/PICkit3/production/*.hex` to learn which build was running.
2. Program `firmware-build/out-v3/pressure_and_flow_pic.production.hex`.
3. Pi: `GET /api/flow/firmware` -> `{major:3, minor:0}`; `GET /api/flow/sensors` -> live flow as before;
   `GET /api/flow/stats?sensors=1` -> `ok` increasing (~11/s at 16 bit), `crc_err`, `i2c_err`.
4. If anything is off: reprogram the backup hex (step 1).

## Deferred to v3.1 (timing-affecting, after v3.0 proves stable)

- Skip `sensirion_measurement_start()` after a NOT_READY read (it is NACKed anyway and costs an 8 ms spin).
- Exit `i2c_wait_for_reply()` immediately on NACK instead of spinning to the 8 ms timeout.
  Together these roughly double the PIC loop rate at 16 bit.

## v3.1 (2026-11-03, built, not yet flashed)

Finding from run `v3_run4` (12 bit, 94 Hz): `flow_refresh_counter` advanced every
`read_flows()` cycle (58 900 increments = ok 58 773 + crc 128 + i2c 35), i.e. it
indexed PIC cycles, not measurements. At 16 bit this made 50 % of "new" samples
stale copies (sensor still measuring); at 12 bit 0.3 % (CRC / I2C failures).

Change (main.c, `read_flows`): the counter increments only if at least one active
channel returned `ERR_OK` in that cycle. Packet formats unchanged. Per-channel
sequence numbers remain available as the `ok` counters in GET_FLOW_STATS (type 14).
GET_FW_VERSION returns 3.1. Host rule: a sample is new iff `refresh_counter` changed.

Hex: `pressure_and_flow_pic.v3.1.hex` (md5 6f549923…). Timing is unchanged.

## v3.2 (2026-11-04, built + desk-tested, not yet flashed)

Findings behind this version (run `v3_run5`, 13 bit, v3.1, 94 Hz Pi polling):
- The Pi captured 87.5 unique/s of ~102 produced: 14 % of PIC cycles were never
  seen because the host polled a single "latest value" register. The sensor
  measurement was also coupled to the ADC scan (one trigger per ~9.8 ms cycle).
- `i2c_wait_for_reply()` spun the full 8 ms on a NACK and then called
  `I2C2_Abort()` (re-initialises I2C2 and resets the ADC state machine), so a
  NACK could never be used as the cheap "still measuring" answer it is.

Changes (expert review `b6ced22e`, "approve with changes", all items applied):
- `sensirion_lg16.c` `i2c_wait_for_reply`: returns as soon as the driver finishes;
  `ADDRESS_NO_ACK`/`DATA_NO_ACK` -> `ERR_SENSIRION_NOT_READY`; `I2C2_Abort()` only
  if still PENDING after the timeout. `sensirion_measurement_start`: address NACK
  -> `ERR_SENSIRION_COMMS_FAIL` (no sensor). `pca9544a_write`: same rule.
- `sensirion_set_resolution`: drains the pending result at 1 attempt/ms for up to
  `SENSIRION_DRAIN_TIMEOUT_MS` (80), accepting CRC_FAIL (idle sensor answers the
  first read header without a frame). New `sensirion_processing_time_min_ms()`.
- Default resolution **13 bit** (`SENSIRION_RESOLUTION_DEFAULT_BITS`): 1 uL/h step,
  8.2-9.4 ms per measurement, lowest MAD measured (24-36 vs 40 uL/h at 12/16 bit).
- `main.c`: `read_flows()` (end of ADC scan) replaced by `poll_flows()`, called
  every main-loop iteration while no ADC I2C transaction is in flight
  (`adc_i2c_wait == 0`). Per channel: trigger (0xF1 + read header) -> wait
  `flow_tmin_ms` (datasheet minimum for the resolution) -> read at most once per
  ms until a valid frame -> store -> trigger again. NOT_READY counted and retried;
  give-up after `2*t_min+20` ms; CRC fail -> explicit re-trigger; I2C error ->
  mux re-selected. PCA9544A written only when the channel changes (`mux_selected`,
  invalidated on any error and after `I2C2_Aborted()`).
- Indexed ring per channel: `flow_ring[4][128]` of `{t_ms (timer_ms), flow_raw}`,
  sequence number = `flow_stats_ok[chan]` (wraps at 65536 in the protocol).
- New packet **18 GET_FLOW_BATCH**: `[chan U8][since_seq U16]` ->
  `[err][n U8][seq0 U16][scale U16][n x (t_ms U16, flow_raw I16)][crc8]`,
  n <= 16, CRC-8 (poly 0x31) over the payload. If `since_seq` is older than the
  ring or ahead of the head (PIC reset) the reply carries err 74
  `ERR_FLOW_BATCH_GAP` and starts from the oldest kept sample; the host resyncs
  `since = seq0 - 1`. Idempotent: a lost SPI reply is simply retried.
- SPI buffers 128 B (`READ_BUF_SIZE`/`WRITE_BUF_SIZE`, power of two asserted).
- `SET_FLOW_RESOLUTION` waits for an in-flight ADC transaction (<= 3 ms) before
  touching the bus and re-arms the scheduler; `SET_ACTIVE_SENSORS` replies once.
- GET_FW_VERSION returns 3.2. All previous packet types unchanged.

Host rules (`pi-webapp/api.py`, batch mode when fw >= 3.2):
- A sample is identified by `(chan, seq)`; `refresh_counter` = seq for legacy
  consumers. `/api/flow/history` samples carry `i` (monotonic store index),
  `seq`, `t_pic_ms`, `flow_raw`; page with `since_i`/`latest_i` (not `since`:
  `t` is estimated per batch and is not strictly ordered).
- `t_pic_ms` comes from the PIC FRC (+-1 %); for long runs fit `t_pic` vs Pi
  time linearly instead of trusting either clock alone.
- Honest mode is guaranteed for >= 12 bit (ring of 128 = 1.2 s at 13 bit); at
  9-10 bit a Python hiccup > 150-250 ms produces GAPs (counted, never hidden).

Post-flash checks: `ok == seq` and `gaps == 0` over 10 min; dt(t_pic) median
9.2-9.5 ms, p99 < 11 ms, no ~17 ms steps; `not_ready`/sample ~1-3; 20 resolution
changes 20/20; unplug sensor 5 s -> `i2c_err` grows, replug -> `ok` resumes
without PIC reset; pressure loop unaffected; `crc_err`/min <= v3.1.

Hex: `pressure_and_flow_pic.v3.2.hex` (md5 b53252b8…). Memory: 21624 B dynamic.

## v3.3 (2026-11-16, built, not yet flashed)

Plan: `audit/2026-11-11-plan-medicion-segun-datasheets.md` §2.1–2.3.

- **Timestamp 32 bits** (§2.2): `flow_sample_t.t_ms` pasa de `uint16_t` (wrap 65,536 s)
  a `uint32_t` (wrap 49,7 días). Nuevo `timer_ms_hi` (alto) incrementado en `timer_isr`
  cuando `timer_ms` da la vuelta; `timer_now32()` compone el valor con doble lectura de
  `hi` (a prueba de tick entre lecturas). `timer_ms` (16 bits) queda intacto para toda la
  aritmética de intervalos cortos y el timeout SPI.
- **GET_FLOW_BATCH (18)**: muestra pasa de 4 a 6 bytes (`t_ms U32, flow_raw I16`);
  paquete máximo 7 + 16×6 + 1 = 104 bytes, dentro del buffer SPI de 128. El host
  distingue el formato por GET_FW_VERSION (`piflow.batch_t32`); un payload v3.3 parseado
  como v3.2 (o viceversa) falla el CRC-8 — no hay lectura silenciosamente corrupta.
- **Contador de saturación** (§2.3): `flow_stats_saturated[chan]` incrementa cuando una
  lectura aceptada está en el riel ±32400 counts (±120 µl/min). GET_FLOW_STATS (14)
  anexa `[saturated U32]` al final: la respuesta pasa de 17 a 21 bytes; hosts viejos
  leen los primeros 17 sin cambio.
- **Trim OSCTUN** (§2.1): `OSCTUN = 0x0F` (+15 pasos ≈ +0,705 %) en
  `mcc_generated_files/clock.c`, anula el skew de −0,72 % del FRC medido contra la Pi.
  Verificar post-flash con un fit t_pic vs t_Pi (debería quedar |skew| < 0,05 %).
- GET_FW_VERSION devuelve 3.3. Paquetes 1–17 sin cambio de formato (14 solo anexa).

Host (`pi-webapp/piflow.py`): `parse_flow_batch(data, t32=)` soporta ambos anchos;
`get_fw_version()` fija `batch_t32`; `get_flow_stats()` devuelve `saturated` si la
respuesta trae ≥21 bytes. `api.py` no necesita cambios (la máscara `& 0xFFFF` de la
edad intra-batch sigue siendo válida: un batch abarca ≪65 s).

Post-flash checks: los de v3.2, más: `saturated` = 0 en flujo normal e incrementando
con el sensor en riel (soplar la línea); `t_pic_ms` monotónico > 65,6 s sin wrap;
skew del fit t_pic/t_Pi < 0,05 %; framing AD5664R al osciloscopio (espera 24 bits,
se envían 32 — confirmar dónde caen los bits de pad).

Hex: `pressure_and_flow_pic.v3.3.hex` (md5 f2a494ae…). Memory: 20582 B dynamic.
**Flasheado 2026-11-16** (PICkit3, respaldo `pic-backup/backup-v3.2-20261116.hex`). Post-flash OK:
fw 3.3, t_pic monotónico > 65,6 s, dt mediana 9 ms / p99 10 ms, 0 gaps, `saturated` presente.

## v3.4 (2026-11-16, built, not yet flashed)

Solo corrige el **signo del trim OSCTUN**: el skew del 11-nov era **+0,698 %** (FRC rápido),
no −0,72 % — la convención estaba invertida. Con +15 pasos (v3.3) el skew medido pasó a
**+1,400 %** (fit de 588 s contra NTP de la Pi, tras descartar un salto NTP de +629,5 s al
arranque). Dos puntos → pendiente medida 0,47 ‰/paso, igual al datasheet. Corrección:
`OSCTUN = 0x31` (−15 pasos en complemento a dos de 6 bits). Skew esperado post-flash ≈ 0,00 %.
GET_FW_VERSION devuelve 3.4. Ningún otro cambio.

⚠️ Mientras v3.4 no esté flasheado, el reloj del PIC corre +1,40 % rápido: una integral de
flujo sobre `t_pic_ms` sobreestima el volumen en ese mismo factor. **Flashear antes de la
calibración gravimétrica** (o dividir dt por 1,0140).

Dato del 16-nov relacionado: baseline con bomba apagada = **+3,0 µL/h** (MAD 2,9, estable en
10 min); `gravimetric_run.py` lo mide 60 s antes de cada corrida y lo resta.

Hex: `pressure_and_flow_pic.v3.4.hex` (md5 3bae2f85…).
**Flasheado 2026-11-17 09:50** (PICkit3; respaldo `pic-backup/backup-v3.3-20261117.hex`).
Post-flash: fw 3.4 ✓; **skew medido +0,12 %** (fit 15 min vs NTP, 0 saltos) — de +1,40 % (v3.3).
El residuo es deriva térmica del FRC (±0,047 %/paso quedó corto ~2–3 pasos esa mañana); se acepta:
5× bajo la incertidumbre de la balanza (0,6 %). Para corridas largas sigue vigente el fit
t_pic-vs-Pi del host como corrección fina.
