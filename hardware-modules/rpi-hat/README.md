## hardware-modules/rpi-hat/ — Raspberry Pi HAT (core board interface)

The Pi HAT (hardware attached on top), an expansion board, helps to physically connect the Raspberry Pi board with modules for bi-directional communication and supply current to the actuators.

<img src="images/pi_hat.jpg" width=40%>   <img src="images/pi_hat_pcb.jpg" width=42%>

### Connectors

This directory contains:

- `Bill-of-Materials.csv`: parts list for the HAT
- `images/`: photos and connector diagrams

The Pi HAT provides power distribution and exposes SPI + GPIO chip-select lines to the module connectors.

In the software, module selection pins are modeled as “ports” in `software/drivers/spi_handler.py` (BOARD numbering). Key constants include:

- `PORT_STROBE = 24`
- `PORT_FLOW = 26`
- `PORT_HEATER1 = 31`, `PORT_HEATER2 = 33`, `PORT_HEATER3 = 32`, `PORT_HEATER4 = 36`

These constants are used by the drivers/controllers to select which module is active on the shared SPI bus.

#### Flow Module Power Connector

<img src="images/pi_flow_connector.png" width=30%>

This is a 2x5 standard DuPont male header.

#### Cable for Flow Module Power Connector

<img src="images/pi_flow_power_cable.png" width=70%>
