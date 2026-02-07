# Starlink Device Spoofing Setup

## Overview
This guide makes your Arduino Leonardo appear as a **Logitech G Pro X Superlight** to the system.

---

## Step 1: Locate Arduino AVR Core

Open this folder:
```
C:\Users\<YourUsername>\AppData\Local\Arduino15\packages\arduino\hardware\avr\
```

Find the version folder (e.g., `1.8.6`) and open it.

---

## Step 2: Backup Original Files

Before modifying, backup these files:
- `boards.txt`
- `cores\arduino\USBCore.h`
- `cores\arduino\USBDesc.h`

---

## Step 3: Modify boards.txt

Open `boards.txt` and find the Leonardo section (search for `leonardo.name=`).

**Replace the Leonardo USB settings with:**

```
leonardo.vid.0=0x046D
leonardo.pid.0=0xC094
leonardo.vid.1=0x046D
leonardo.pid.1=0xC094
leonardo.vid.2=0x046D
leonardo.pid.2=0xC094
leonardo.vid.3=0x046D
leonardo.pid.3=0xC094

leonardo.build.vid=0x046D
leonardo.build.pid=0xC094
leonardo.build.usb_manufacturer="Logitech"
leonardo.build.usb_product="PRO X SUPERLIGHT"
```

**Full Leonardo section should look like:**

```
##############################################################
leonardo.name=Arduino Leonardo

leonardo.vid.0=0x046D
leonardo.pid.0=0xC094
leonardo.vid.1=0x046D
leonardo.pid.1=0xC094
leonardo.vid.2=0x046D
leonardo.pid.2=0xC094
leonardo.vid.3=0x046D
leonardo.pid.3=0xC094

leonardo.upload.tool=avrdude
leonardo.upload.protocol=avr109
leonardo.upload.maximum_size=28672
leonardo.upload.maximum_data_size=2560
leonardo.upload.speed=57600
leonardo.upload.disable_flushing=true
leonardo.upload.use_1200bps_touch=true
leonardo.upload.wait_for_upload_port=true

leonardo.bootloader.tool=avrdude
leonardo.bootloader.low_fuses=0xff
leonardo.bootloader.high_fuses=0xd8
leonardo.bootloader.extended_fuses=0xcb
leonardo.bootloader.file=caterina/Caterina-Leonardo.hex
leonardo.bootloader.unlock_bits=0x3F
leonardo.bootloader.lock_bits=0x2F

leonardo.build.mcu=atmega32u4
leonardo.build.f_cpu=16000000L
leonardo.build.vid=0x046D
leonardo.build.pid=0xC094
leonardo.build.usb_manufacturer="Logitech"
leonardo.build.usb_product="PRO X SUPERLIGHT"
leonardo.build.board=AVR_LEONARDO
leonardo.build.core=arduino
leonardo.build.variant=leonardo
leonardo.build.extra_flags={build.usb_flags}
```

---

## Step 4: Modify USB Descriptor (Optional but Recommended)

For complete spoofing, edit `cores\arduino\USBCore.cpp`.

Find the `STRING_PRODUCT` and `STRING_MANUFACTURER` defines or the string descriptor section.

This varies by Arduino core version. The `boards.txt` changes usually suffice.

---

## Step 5: Verify Spoofing

After flashing, check in Device Manager:
1. Open Device Manager
2. Find "Mice and other pointing devices"
3. Should show "PRO X SUPERLIGHT" or "HID-compliant mouse"

Or use PowerShell:
```powershell
Get-PnpDevice -Class Mouse | Select-Object FriendlyName, InstanceId
```

---

## Alternative VID/PIDs (if Logitech is flagged)

### Razer DeathAdder V3
```
VID: 0x1532
PID: 0x00B6
Manufacturer: "Razer"
Product: "Razer DeathAdder V3"
```

### Zowie EC2
```
VID: 0x3057
PID: 0x0001
Manufacturer: "Zowie"
Product: "ZOWIE EC2"
```

### SteelSeries Prime
```
VID: 0x1038
PID: 0x1866
Manufacturer: "SteelSeries"
Product: "SteelSeries Prime"
```

### Finalmouse UltralightX
```
VID: 0x361D
PID: 0x0100
Manufacturer: "Finalmouse"
Product: "UltralightX"
```

---

## Troubleshooting

### Can't upload after spoofing
1. Double-tap reset button on Leonardo
2. Quickly select the new COM port
3. Upload within 8 seconds

### Device not recognized
- Check VID/PID format (must be 0x prefix)
- Ensure quotes around manufacturer/product strings
- Restart Arduino IDE after changes

### Windows driver issues
After first flash with new VID/PID, Windows may install generic HID driver.
This is normal and actually desired - it means it looks like a real mouse.

---

## Security Notes

- Using real VID/PIDs from other manufacturers is in a legal gray area
- For personal/testing use only
- The VID/PID doesn't guarantee undetectability - behavioral analysis can still flag abnormal patterns
- Our firmware includes advanced humanization to address behavioral detection
