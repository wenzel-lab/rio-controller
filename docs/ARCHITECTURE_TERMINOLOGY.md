# Architecture Terminology

## Overview

This document clarifies the terminology used in the Rio microfluidics controller software, particularly the distinction between "controller" in hardware control contexts vs. traditional MVC terminology.

## Terminology: "Controller" in Hardware Control Systems

### Device Controllers (`software/controllers/`)

In hardware control and embedded systems (like SQUID microscope software, robotics, and industrial automation), **"controller"** refers to the business logic layer that controls physical devices. This is the standard terminology in these domains.

**In our codebase:**
- `controllers/camera.py` - Camera device controller
- `controllers/flow_web.py` - Flow control device controller
- `controllers/heater_web.py` - Heater device controller
- `controllers/strobe_cam.py` - Strobe-camera integration controller

**These are equivalent to "Models" in traditional MVC**, but we use "controller" because:
1. It's the standard term in hardware control systems
2. It's more self-explanatory in embedded contexts
3. It aligns with existing hardware control software (e.g., SQUID)

### Web Controllers (`software/rio-webapp/controllers/`)

These handle HTTP requests and WebSocket events - this is the traditional MVC "Controller" layer.

**In our codebase:**
- `rio-webapp/controllers/camera_controller.py` - WebSocket handlers for camera
- `rio-webapp/controllers/flow_controller.py` - WebSocket handlers for flow
- `rio-webapp/controllers/heater_controller.py` - WebSocket handlers for heaters
- `rio-webapp/controllers/view_model.py` - Data formatting for views

## Architecture Layers

Our software follows **MVC+S** (Model-View-Controller-Simulation):

```
┌─────────────────────────────────────────┐
│  View Layer (Templates, Static Files)   │
│  rio-webapp/templates/, static/         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Web Controller Layer                   │
│  rio-webapp/controllers/                │
│  (HTTP/WebSocket handlers)              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Device Controller Layer                 │
│  controllers/                            │
│  (Business logic, device control)        │
│  [Equivalent to "Model" in MVC]          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Driver Layer                            │
│  drivers/                                │
│  (Low-level hardware communication)      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  Simulation Layer (optional)             │
│  simulation/                             │
│  (Drop-in hardware replacement)          │
└─────────────────────────────────────────┘
```

## Mapping to Traditional MVC

| Traditional MVC | Our Hardware Control Terminology | Location |
|----------------|----------------------------------|----------|
| **Model** | **Device Controller** | `controllers/` |
| **View** | **View** | `rio-webapp/templates/`, `static/` |
| **Controller** | **Web Controller** | `rio-webapp/controllers/` |
| N/A | **Driver** | `drivers/` |
| N/A | **Simulation** | `simulation/` |

## Why This Terminology?

1. **Hardware Control Standard**: In embedded systems, "controller" for device control is universal
2. **Self-Explanatory**: "Camera Controller" is clearer than "Camera Model" in hardware contexts
3. **Industry Alignment**: Matches terminology used in SQUID microscope software and similar systems
4. **Clarity**: Distinguishes between device control logic (`controllers/`) and web request handling (`rio-webapp/controllers/`)

## Summary

- **Device Controllers** (`controllers/`) = Business logic for device control (MVC "Model")
- **Web Controllers** (`rio-webapp/controllers/`) = HTTP/WebSocket request handlers (MVC "Controller")
- **Views** (`rio-webapp/templates/`) = Presentation layer (MVC "View")
- **Drivers** (`drivers/`) = Low-level hardware communication
- **Simulation** (`simulation/`) = Hardware replacement for testing

This terminology maintains clarity while respecting both hardware control conventions and web application architecture patterns.

