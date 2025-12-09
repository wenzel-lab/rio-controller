# "Rio controller" the modular microfluidics controller [![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

This repository contains the free and *open-source* design and documentation for the *brain of a microfluidics workstation* to enable *high-throughput droplet microfluidic* biological assays. The design contains an electronics board "hat" that plugs onto a Raspberry Pi single-board computer and interfaces with our *compact* *modules* e.g. for gas-pressure control to push microfluidic samples onto chips, pressure, and flow measurement with feedback control, sample holders with heating and stirring, and imaging of fast droplet generation processes with open-source microscopy and stroboscopic illumination

Our aim is to create a prototype of a *compact* working station that is based on *connectable*, *open*, modern, and *low-cost* components (Rasberry Pi, Arduino, 3D printing, on-board components, open or at least accessible design software and operation software - python). This workstation is aimed to be fully functional research-grade equipment with good specifications, such as fast reaction times and low-pressure fluctuations. It is modular so that parts of the workstation can be repurposed and improved in the open-source hardware sense and easily combined, exchanged, or used independently in challenging environments such as an anaerobic chamber.

This is an open, collaborative project by the Wenzel Lab in Chile, and *your participation* (comments, inputs, contributions) are explicitly welcome! Please submit your message as an issue in this repository to participate.

> **Please Note:** This technical index is very much under construction and is at present an incomplete summary of the various documents that exist elsewhere in the Open Microfluidics Workstation repositories on GitHub and elsewhere.

Follow us! [#twitter](https://twitter.com/WenzelLab), [#YouTube](https://www.youtube.com/@librehub), [#LinkedIn](https://www.linkedin.com/company/92802424), [#instagram](https://www.instagram.com/wenzellab/), [#Printables](https://www.printables.com/@WenzelLab), [#LIBREhub website](https://librehub.github.io), [#IIBM website](https://ingenieriabiologicaymedica.uc.cl/en/people/faculty/821-tobias-wenzel)


<!--- ## Table of Contents --->

<!--- ## Background --->

## Usage

* Installation instructions
    * [Software installation](https://github.com/wenzel-lab/moldular-microfluidics-workstation-controller/wiki/Install-the-Software)
* Our modules are used in our [flow-microscopy-platform, see repostiory for documentation and instructions](https://github.com/wenzel-lab/flow-microscopy-platform)
* And it also powers our [strobe-enhanced microscopy stage](https://wenzel-lab.github.io/strobe-enhanced-microscopy-stage/) see also [it's repository](https://github.com/wenzel-lab/strobe-enhanced-microscopy-stage) 

## Design files and source code

* Hardware designs
    * [Hardware modules](hardware-modules/) - All hardware module designs including:
        * [Heating and stirring module](hardware-modules/heating-stirring/)
        * [Pressure and flow control module](hardware-modules/pressure-flow-control/)
        * [Strobe imaging module](hardware-modules/strobe-imaging/)
        * [Raspberry Pi HAT extension board](hardware-modules/rpi-hat/)
 
* Software source code
    * [Microfluidics workstation server](software/) - Modern refactored software running on the built-in Raspberry Pi with web application for the user interface. See [software/README.md](software/README.md) for installation and usage instructions.

### Modules Wish List
* High-pressure source module to replace large gas bottles with a small soda CO2 bottle, developed in this [sub-repository](https://github.com/wenzel-lab/moldular-microfluidics-workstation-controller/tree/master/module-high-pressure-source)
* Support for small piezo pumps
* Smart cultivation sleeves for vials, smaller and with OD-tracking - the V2 of our current sample holders and strirrers
* Microfluidic droplet sorting workstation driven by the droplet workstation tools is described [here](https://github.com/wenzel-lab/droplet-sorter-master/tree/main) (This is being developed in a separate repository).
  
## Contribute

Feel free to dive in! [Open an issue](https://github.com/wenzel-lab/moldular-microfluidics-workstation-controller/issues/new).
For interactions in our team and with the community applies the [GOSH Code of Conduct](https://openhardware.science/gosh-2017/gosh-code-of-conduct/).

## License

[CERN OHL 2W](LICENSE) © Tobias Wenzel, Christie Nel, and Pierre Padilla-Huamantinco. This project is Open-Source Hardware - please acknowledge us when using the hardware or sharing modifications.
