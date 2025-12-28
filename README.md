# "Rio" the modular microfluidics controller [![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

This repository contains the _free_ and _open-source_ designs and documentation for the _core board_ and their _modules_ of a microfluidics workstation to enable _high-throughput droplet microfluidic_ biological assays. The designs contain an electronics board "hat" that plugs onto a Raspberry Pi single-board computer and interfaces with our _compact controllers_ e.g. for gas-pressure control to push microfluidic samples onto chips, pressure, and flow measurement with feedback control, sample holders with heating and stirring, and imaging of fast droplet generation processes with open-source microscopy and stroboscopic illumination.

This is an open, collaborative project by the [Wenzel Lab](https://wenzel-lab.github.io/en/) in Chile, and _your participation_ (comments, inputs, contributions) are explicitly welcome! Please submit your message as an issue in this repository to participate.

Follow us! [#twitter](https://twitter.com/WenzelLab), [#YouTube](https://www.youtube.com/@librehub), [#LinkedIn](https://www.linkedin.com/company/92802424), [#instagram](https://www.instagram.com/wenzellab/), [#Printables](https://www.printables.com/@WenzelLab), [#LIBREhub website](https://librehub.github.io), [#IIBM website](https://ingenieriabiologicaymedica.uc.cl/en/people/faculty/821-tobias-wenzel)

## Table of contents

- [Why Rio](#why-rio)
- [Getting Started](#getting-started)
- [Use Cases](#use-cases)
- [Read the Paper](#read-the-paper)
- [Modules Wish List](#modules-wish-list)
- [Contributing](#contributing)
- [License](#license)

## Why "Rio"

Our aim is to create a prototype of a _compact_ working station for microfluidic research that is based on _connectable_, _open_, modern, and _low-cost_ components (Rasberry Pi, Arduino, 3D printing, on-board components, open or at least accessible design software and operation software - python).

**Rio** serves as a platform to implement fully functional research-grade workstations with good specifications, such as fast reaction times and low-pressure fluctuations. It is modular so that parts of this platform can be repurposed and improved in the open-source hardware sense and easily combined, exchanged, or used independently in challenging environments.

## Getting Started

In order to implement a workstation, you must build the core board and any module of your interest. The user interface software will allow you to control and monitor the operations of the modules.

### Core Board

The core board consists of a Raspberry Pi 4B+ and a custom Pi HAT (hardware attached to the top). The Pi HAT is an extension board for bidirectional communication and power supply to the controllers. 

<table>
<tr>
    <td align="center"><b>Core Board</b></td>
</tr>
<tr>
    <td align="center"><img src="hardware-modules/rpi-hat/images/Pi-HAT.png" width=400 alt="Raspberry Pi HAT" /></td>
</tr>
<tr>
    <td align="center"><a href="hardware-modules/rpi-hat/"><br><b>Build the Pi HAT</b></a><br><br></td>
</tr>
</table>

### Modules

A _module_ commonly consists of a compact controller, sensors, and actuators, and operates with distinct power supply and data connections. The controllers convert physical data into digital data, manipulate the actuators, and supply energy to external components. 

<table>
<tr>
    <td align="center"><b>Strobe Imaging Module</b></td>
    <td align="center"><b>Pressure and Flow Control Module</b></td>
    <td align="center"><b>Heat and Stirring Module</b></td>
</tr>
<tr>
    <td align="center"><img src="hardware-modules/strobe-imaging/images/strobe-imaging-controller.png" width=75 alt="Strobe Imaging Controller" /></td>
    <td align="center"><img src="hardware-modules/pressure-flow-control/images/pressure-and-flow-controller.png" width=100 alt="Pressure and Flow Controller" /></td>
    <td align="center"><img src="hardware-modules/heating-stirring/images/heating-and-stirring-controller.png" width=80 alt="Heating and Stirring Controller" /></td>
</tr>
<tr>
    <td align="center"><a href="hardware-modules/strobe-imaging/"><br><b>Build the controller</b></a><br><br></td>
    <td align="center"><a href="hardware-modules/pressure-flow-control/"><br><b>Build the controller</b></a><br><br></td>
    <td align="center"><a href="hardware-modules/heating-stirring/"><br><b>Build the controller</b></a><br><br></td>
</tr>
</table>

### Software

The software follows a client-server architecture and allows users to control the physical hardware through a graphical interface. It runs on a Raspberry Pi (32-bit bullseye, or 64-bit operating system).

**Installation and Usage:**
- For detailed software installation and usage instructions, see [software/README.md](software/README.md)
- For Raspberry Pi deployment instructions, see [pi-deployment/README.md](pi-deployment/README.md)

**Features:**
- Real-time camera control with strobe synchronization
- Droplet detection with histogram visualization
- Flow and pressure control
- Temperature and stirring control
- Modern web-based user interface

## Use Cases

**Single-module solution:**
* Strobe-enhanced microscopy stage ([Repository](https://github.com/wenzel-lab/strobe-enhanced-microscopy-stage) | [Assembly Instructions](https://wenzel-lab.github.io/strobe-enhanced-microscopy-stage/))

**Three-modules solution:**
* Flow microscopy platform ([Repository](https://github.com/wenzel-lab/flow-microscopy-platform) | Assembly Instructions (Soon))

## Read the Paper

"Rio" has been employed in the article ["Plasmid Stability Analysis with Open-Source Droplet Microfluidics"](https://app.jove.com/t/67659/plasmid-stability-analysis-with-open-source-droplet-microfluidics), published in JoVE in December 2024. Please cite this article when using our hardware system.

DOI: [https://dx.doi.org/10.3791/67659](https://dx.doi.org/10.3791/67659)

## Modules Wish List

* High-pressure source module to replace large gas bottles with a small soda CO2 bottle, developed in this [sub-repository](https://github.com/wenzel-lab/rio-controller/tree/master/module-high-pressure-source)
* Support for small piezo pumps
* Smart cultivation sleeves for vials, smaller and with OD-tracking - the V2 of our current sample holders and strirrers
* Microfluidic droplet sorting workstation driven by the droplet workstation tools is described [here](https://github.com/wenzel-lab/droplet-sorter-master/tree/main) (This is being developed in a separate repository).

## Contributing

Feel free to dive in! [Open an issue](https://github.com/wenzel-lab/rio-controller/issues/new).
For interactions in our team and with the community applies the [GOSH Code of Conduct](https://openhardware.science/gosh-2017/gosh-code-of-conduct/). If you want to get involved in our research, please see the [website of our team](https://wenzel-lab.github.io/en/).

## License

**Hardware:** All source files located in the `hardware-modules` directories (including firmware, PCB designs, and documentation) and documentation are released under the [CERN-OHL-W-2.0](https://ohwr.org/cern_ohl_w_v2.txt) license.

**Software:** The source codes located in the `software` directory are released under the [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.en.html) license.

© Tobias Wenzel, Christie Nel, and Pierre Padilla-Huamantinco. This project is Open-Source Hardware - please cite and acknowledge us when using the hardware or sharing modifications.
