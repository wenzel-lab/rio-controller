# Creating a Custom Raspberry Pi OS Image

This guide describes how to create a compact `.img` backup of a customized **Raspberry Pi OS Bullseye** installation using **GParted** and **Win32 Disk Imager**.

The procedure is based on the workflow described by HowToRaspberry, with additional notes for Windows 11.

## Overview

The workflow consists of:

1. Preparing the customized Raspberry Pi OS installation.
2. Creating a full backup of the SD card.
3. Shrinking the Linux `rootfs` partition using GParted.
4. Creating a compact `.img` file using Win32 Disk Imager.
5. Flashing and expanding the filesystem on a new SD card.

The resulting image contains the customized operating system while excluding most of the unused space on the original SD card.

---

## Requirements

### Hardware

- microSD card containing the customized Raspberry Pi OS installation.
- SD/microSD card reader.
- A second Linux system or Raspberry Pi for running GParted.
- Windows PC for running Win32 Disk Imager.

### Software

- GParted.
- [Win32 Disk Imager 1.0](https://win32diskimager.org/download/).
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/) for subsequently flashing the resulting `.img` file.

---

## 1. Prepare the Custom Operating System

Complete all desired configuration of the Raspberry Pi before creating the image.

This may include:

- Installing required packages.
- Installing custom software.
- Configuring services.
- Configuring hardware interfaces.
- Adding scripts and configuration files.
- Removing unnecessary files.
- Clearing temporary files or caches.

When finished, shut down the Raspberry Pi cleanly:

```bash
sudo shutdown -h now
```

Wait until the Raspberry Pi has completely shut down before removing the SD card.

---

## 2. Create a Full Backup

Before resizing any partitions, it is strongly recommended to create a complete backup of the original SD card.

Insert the SD card into the Windows computer and open **Win32 Disk Imager as Administrator**.

Select:

- **Image File:** destination for the backup.
- **Device:** drive letter corresponding to the SD card.

For example:

```text
CustomOS_FULL_BACKUP.img
```

Click **Read**.

> **Important:** Use **Read**, not **Write**. `Read` copies the SD card to an image file. `Write` writes an image to the SD card and can overwrite its contents.

Keep this full image as a recovery copy before modifying the partition layout.

---

## 3. Shrink the Root Filesystem

The main Linux partition should be reduced before creating the distributable image.

This operation must be performed while the customized `rootfs` partition is **not being used as the running root filesystem**.

Insert the SD card into another Linux computer or Raspberry Pi.

Install GParted if necessary:

```bash
sudo apt update
sudo apt install gparted
```

Search for the GParted appliaction or launch it from the command line:

```bash
sudo gparted
```

### Select the microSD Card

Carefully select the correct storage device. Verify its device name, capacity, and partition structure before making any changes.

A typical Raspberry Pi OS Bullseye microSD card contains approximately:

```text
microSD card
│
├── boot      FAT32
└── rootfs    ext4
```

The exact device names may appear as:

```text
/dev/sdX1    boot
/dev/sdX2    rootfs
```

or similar.

> **Warning:** Verify that the selected device is the microSD card before modifying any partitions. Selecting the wrong storage device can result in data loss.

### Resize `rootfs`

Select the **ext4 `rootfs` partition**.

Right-click and select:

**Resize/Move**

Reduce the partition by moving its **right boundary** toward the amount of space actually being used.

Do not reduce the partition to exactly the amount of used space. Leave sufficient free space for the operating system to boot and operate.

For example:

```text
Used space:        5.8 GB
New rootfs size:   7–8 GB
```

Do **not** resize the FAT32 boot partition unless there is a specific reason to do so.

Apply the pending operation using the green **Apply** button.

Wait for GParted to complete the filesystem and partition resize.

The resulting microSD card should resemble:

```text
microSD card
│
├── boot          ~256 MB
├── rootfs        ~8 GB
└── unallocated   remaining space
```

Shut down/eject the microSD card safely when finished.

---

## 4. Create the Compact Image

Insert the resized microSD card into the Windows computer.

Start **Win32 Disk Imager as Administrator**.

Select a filename for the distributable image and make sure ".img" is included at the end of the filename. For example:

```text
CustomOS_v1.0.img
```

Select the correct microSD card under **Device**.

Enable:

```text
☑ Read Only Allocated Partitions
```

Then click:

**Read**

This option is important because it prevents Win32 Disk Imager from copying the large unallocated region at the end of the SD card. In our test, generating a 7 GB image took approximately about 12 minutes.

For example:

```text
32 GB microSD card
│
├── boot           0.25 GB
├── rootfs         8 GB
└── unallocated   ~21 GB
        │
        ▼
Read Only Allocated Partitions
        │
        ▼
CustomOS_v1.0.img  ~8 GB
```

The exact image size depends on the partition layout.

---

## 5. Windows 11: Win32 Disk Imager Does Not Start

On Windows 11, Win32 Disk Imager may fail to launch when certain virtual or mounted drives are present. In our test, this occurred with the virtual drive created by Google Drive for desktop.

A typical symptom is:

1. Run Win32 Disk Imager as Administrator.
2. Windows displays the User Account Control (UAC) confirmation.
3. Select **Yes**.
4. Nothing happens and the Win32 Disk Imager window never appears.

Windows Event Viewer may report a crash involving:

```text
Application:       Win32DiskImager.exe
Faulting module:   ntdll.dll
Exception code:    0xc00000fd
```

### Google Drive Conflict

In the tested setup, the problem was caused by the virtual drive mounted by **Google Drive for desktop**.

The solution was:

1. Close **Google Drive for desktop**.
2. Verify that its virtual drive is no longer mounted.
3. Start Win32 Disk Imager as Administrator.
4. Insert/access the SD card.
5. Perform the required read operation.

Other virtual, network, or mounted drives may potentially cause similar problems.

> If Win32 Disk Imager suddenly stops launching, check mounted virtual drives before reinstalling the application or changing Windows compatibility settings.

---

## 6. Test the Image

A distributable image should always be tested on a different SD card before the original customized SD card is modified or discarded.

Flash:

```text
CustomOS_v1.0.img
```

onto another microSD card using Raspberry Pi Imager or your preferred imaging software.

Insert the new card into the Raspberry Pi and verify that:

- The Raspberry Pi boots successfully.
- Required services start.
- Custom software is present.
- Hardware interfaces work.
- Network configuration works as expected.
- User applications function correctly.

---

## 7. Expand the Filesystem

The flashed SD card initially retains the smaller `rootfs` partition used when the image was created.

After successfully booting the cloned system, run:

```bash
sudo raspi-config
```

Use the filesystem expansion option, typically available under:

```text
Advanced Options
```

Then reboot:

```bash
sudo reboot
```

After rebooting, verify the available filesystem space:

```bash
df -h
```

The root filesystem should now use the available capacity of the new SD card.

---

## Recommended Image Management

Maintain at least two versions of the image:

```text
CustomOS_FULL_BACKUP.img
```

A complete sector-level backup of the original SD card. Keep this as the recovery/master image.

```text
CustomOS_v1.0.img
```

The resized image intended for testing, distribution, or flashing onto additional SD cards.

A versioned naming convention is useful for subsequent releases:

```text
CustomOS_v1.0.img
CustomOS_v1.1.img
CustomOS_v1.2.img
```

Optionally include the operating-system version and architecture:

```text
CustomOS_Bullseye_armhf_v1.0.img
```

---

## References

The resizing and imaging procedure is based on:

**HowToRaspberry — "How to Make Your Own Raspberry Pi .img Files"**  
[https://www.howtoraspberry.com/2020/12/how-to-make-your-own-raspberry-pi-img-files/](https://www.howtoraspberry.com/2020/12/how-to-make-your-own-raspberry-pi-img-files/)

Additional information about Win32 Disk Imager:

**Win32 Disk Imager**  
[https://win32diskimager.org/](https://win32diskimager.org/)
