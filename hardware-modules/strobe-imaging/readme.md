## Fast imaging module for microfluidic droplet generation

Imaging unit based on compact 3D printed microscope (https://gitlab.com/openflexure/openflexure-microscope), with Objective (10x?)

Depending on the load demand, it could operate on the Raspberri Pi computer of the central workstation unit, have it's own computer, and transfer images to a webserver

All versions aim for a userfriendly / self-tuning controll of a stroboscopic illumination (simple high-power LED controlled by Arduino style microcontroller, in turn controlled by the Raspberri Pi where images are processed / viewed and saved/ sent to server)


### Approach Nr.1 Integrated camera

Low-cost integrated use of Raspberri Pi Camera V2 and scripting to vary image size vs. frame rate.

Instruction examples:

https://hackaday.com/2019/08/10/660-fps-raspberry-pi-video-captures-the-moment-in-extreme-slo-mo/

https://gist.github.com/CarlosGS/b8462a8a1cb69f55d8356cbb0f3a4d63#gistcomment-2108157

https://blog.robertelder.org/recording-660-fps-on-raspberry-pi-camera/

https://github.com/Hermann-SW/Raspberry_v1_camera_global_external_shutter


### Approach Nr.2 USB3 camera

Use of high-speed camera and USB3 connection on the Raspberri Pi 4

E.g. Compact cameras from Allied Vision 

Camera Mako U-051B mono; 800x600 CMOS C-Mount 391fps 10bit-ADC 128MB-buffer; ca. 340 Euro net

Camera Mako U-029B mono; 640x480 CMOS C-Mount 550fps 10bit-ADC 128MB-buffer; ca. 300 Euro net

In the end we decided to use the camera Allied-Vision Mako U-029B with global shutter: 
https://www.1stvision.com/cameras/AVT/dataman/MakoU_TechMan_en.pdf,
https://www.spectratech.gr/en/product/43606/Allied-Vision_Mako_U-029B?path=54-40
