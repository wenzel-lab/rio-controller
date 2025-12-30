# software/rio-webapp/controllers/ — Socket.IO handlers (“web controllers”)

This folder owns the Socket.IO contract between the browser UI and the server. These modules parse event payloads from the browser, call into the **device controllers** in `../../controllers/`, and emit view-friendly updates back to the UI.

## What’s inside (and what each file handles)

- `camera_controller.py` — `CameraController`
  - listens on **`"cam_select"`**
  - handles camera backend switching via `controllers.camera.Camera.strobe_cam.set_camera_type(...)`
  - emits **`"reload"`** to force a UI refresh after camera changes

- `flow_controller.py` — `FlowController`
  - listens on **`"flow"`**
  - supported commands include: `"pressure_mbar_target"`, `"flow_ul_hr_target"`, `"control_mode"`, `"flow_pi_consts"`
  - emits **`"flows"`** with formatted per-channel state

- `heater_controller.py` — `HeaterController`
  - listens on **`"heater"`**
  - supported commands include: `"temp_c_target"`, `"pid_enable"`, `"power_limit_pc"`, `"autotune"`, `"stir"`
  - emits **`"heaters"`** with formatted state

- `droplet_web_controller.py` — `DropletWebController` (optional, only if droplet detection is enabled)
  - listens on **`"droplet"`**
  - supports commands: `"start"`, `"stop"`, `"config"`, `"profile"`, `"get_status"`, `"reset"`
  - emits (examples):
    - **`"droplet:status"`**, **`"droplet:histogram"`**, **`"droplet:statistics"`**
    - **`"droplet:config_updated"`**, **`"droplet:error"`**

- `view_model.py` — `ViewModel`
  - pure formatting layer used to turn controller state into template/client payloads
  - should not contain device/business logic

## Payload shape (shared convention)

Most events follow the pattern:

- payload has `cmd` (string) and optional `parameters` (object/dict)
- server handlers validate, call a controller method, then emit a “current state” payload back

Treat event names and payload schemas as a public API: update browser JS and any tests at the same time.

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change event names or payload formats, update this document.


