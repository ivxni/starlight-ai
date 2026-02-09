"""
Startility - Wooting 60HE Firmware Serial Patcher
==================================================
Patches the firmware binary to report a custom USB serial number.

Strategy:
  1. Parse Intel HEX firmware (.fwr)
  2. Find USB device descriptor (VID/PID pattern)
  3. Find USB string descriptors ("Wooting" manufacturer string)
  4. Locate serial string generation code
  5. Patch to use a hardcoded custom serial
  6. Write patched Intel HEX for flashing via bootloader

The serial string "A02B2247W052H16911" is dynamically generated from
SPI flash data. We patch the firmware to bypass SPI read and use our
custom serial directly.
"""

import sys
import struct
import os
from intelhex import IntelHex

FW_PATH = os.path.join(os.environ.get('TEMP', '/tmp'),
                       'wootility-src', 'dist', 'fw', 'wooting_60_he_arm.fwr')

# STM32 flash base
FLASH_BASE = 0x08000000
FW_START = 0x08007000  # Firmware starts here (bootloader below)


def load_firmware(path):
    """Load Intel HEX firmware file."""
    print(f"[*] Loading firmware: {path}")
    ih = IntelHex(path)
    
    start = ih.minaddr()
    end = ih.maxaddr()
    size = end - start + 1
    
    print(f"    Address range: 0x{start:08X} - 0x{end:08X}")
    print(f"    Size: {size:,} bytes ({size/1024:.1f} KB)")
    
    # Convert to binary
    binary = ih.tobinarray(start=start, size=size)
    return ih, bytes(binary), start


def search_pattern(data, pattern, name="pattern"):
    """Search for a byte pattern in data."""
    results = []
    idx = 0
    while True:
        idx = data.find(pattern, idx)
        if idx < 0:
            break
        results.append(idx)
        idx += 1
    return results


def find_usb_descriptors(binary, base_addr):
    """Find USB device descriptor and string descriptors."""
    print("\n[*] Searching for USB descriptors...")
    
    # USB Device Descriptor: 12 01 00 02 ... E3 31 12 13
    # Length=18(0x12), Type=1(Device), USB=2.00, ...
    # VID=0x31E3 (E3 31 LE), PID=0x1312 (12 13 LE)
    
    vid_le = struct.pack("<H", 0x31E3)  # E3 31
    pid_le = struct.pack("<H", 0x1312)  # 12 13
    
    # Search for VID+PID together
    vidpid = vid_le + pid_le
    locs = search_pattern(binary, vidpid)
    print(f"    VID:PID (31E3:1312) found at {len(locs)} location(s)")
    
    for loc in locs:
        addr = base_addr + loc
        # Device descriptor starts 8 bytes before VID
        desc_start = loc - 8
        if desc_start >= 0:
            desc = binary[desc_start:desc_start + 18]
            if len(desc) >= 18 and desc[0] == 0x12 and desc[1] == 0x01:
                print(f"    [!] USB Device Descriptor at 0x{addr-8:08X}:")
                print(f"        Length: {desc[0]}")
                print(f"        Type:   {desc[1]} (Device)")
                print(f"        USB:    {desc[3]}.{desc[2]}")
                print(f"        Class:  {desc[4]:02X}/{desc[5]:02X}/{desc[6]:02X}")
                print(f"        MaxPkt: {desc[7]}")
                print(f"        VID:    0x{struct.unpack_from('<H', desc, 8)[0]:04X}")
                print(f"        PID:    0x{struct.unpack_from('<H', desc, 10)[0]:04X}")
                print(f"        bcdDev: {desc[13]}.{desc[12]}")
                print(f"        iManuf: {desc[14]} (string index)")
                print(f"        iProd:  {desc[15]} (string index)")
                print(f"        iSer:   {desc[16]} (string index)")
                print(f"        nConf:  {desc[17]}")
                
                return desc_start, desc
            else:
                # VID/PID found but not at expected offset in device descriptor
                # Show context
                ctx_start = max(0, loc - 16)
                ctx = binary[ctx_start:loc + 16]
                print(f"    VID/PID at offset {loc} (0x{addr:08X}), context:")
                print(f"        {ctx.hex()}")
    
    return None, None


def find_string_descriptors(binary, base_addr):
    """Search for USB string descriptors in firmware."""
    print("\n[*] Searching for USB string descriptors...")
    
    # USB String Descriptor: [length] [0x03] [UTF-16LE chars...]
    # "Wooting" in UTF-16LE: 57 00 6F 00 6F 00 74 00 69 00 6E 00 67 00
    wooting_utf16 = "Wooting".encode('utf-16-le')
    
    locs = search_pattern(binary, wooting_utf16)
    print(f"    'Wooting' (UTF-16LE) found at {len(locs)} location(s)")
    
    for loc in locs:
        addr = base_addr + loc
        # String descriptor starts 2 bytes before the text
        sd_start = loc - 2
        if sd_start >= 0:
            sd_len = binary[sd_start]
            sd_type = binary[sd_start + 1]
            if sd_type == 0x03:
                sd_text = binary[sd_start + 2:sd_start + sd_len]
                try:
                    text = sd_text.decode('utf-16-le')
                except:
                    text = sd_text.hex()
                print(f"    [!] String Descriptor at 0x{base_addr + sd_start:08X}:")
                print(f"        Length: {sd_len}")
                print(f"        Type:   0x03 (String)")
                print(f"        Text:   '{text}'")
                return sd_start
            else:
                print(f"    'Wooting' at 0x{addr:08X} (not in string descriptor)")
    
    # Also search for raw ASCII "Wooting"
    ascii_locs = search_pattern(binary, b"Wooting")
    print(f"    'Wooting' (ASCII) found at {len(ascii_locs)} location(s)")
    for loc in ascii_locs:
        if loc not in [l - 2 for l in locs]:  # Skip UTF-16 matches
            addr = base_addr + loc
            ctx = binary[loc:min(loc + 40, len(binary))]
            print(f"    ASCII at 0x{addr:08X}: {ctx}")
    
    return None


def find_serial_format(binary, base_addr):
    """Search for serial number format strings and related patterns."""
    print("\n[*] Searching for serial-related patterns...")
    
    # Search for format string patterns
    patterns = [
        (b"%02d", "format %02d"),
        (b"%d", "format %d"),
        (b"%03d", "format %03d"),
        (b"%s", "format %s"),
        (b"%c", "format %c"),
        (b"A02B", "serial prefix ASCII"),
        (b"A\x000\x002\x00B\x00", "serial prefix UTF-16"),
        (b"\x02\x00\x16\x2f", "serial raw bytes (supplier+year+week)"),
        (b"serial", "serial keyword"),
        (b"Serial", "Serial keyword"),
        (b"SERIAL", "SERIAL keyword"),
    ]
    
    for pattern, name in patterns:
        locs = search_pattern(binary, pattern)
        if locs:
            for loc in locs[:3]:  # Show first 3
                addr = base_addr + loc
                ctx = binary[max(0, loc-4):min(loc + len(pattern) + 20, len(binary))]
                print(f"    '{name}' at 0x{addr:08X}: ...{ctx[:32].hex()}...")


def find_serial_string_buffer(binary, base_addr):
    """Look for the actual serial string in firmware data sections."""
    print("\n[*] Searching for serial string buffer location...")
    
    # The serial "A02B2247W052H16911" as UTF-16LE
    serial_utf16 = "A02B2247W052H16911".encode('utf-16-le')
    locs = search_pattern(binary, serial_utf16)
    if locs:
        print(f"    [!!!] Serial string found at {len(locs)} location(s)!")
        for loc in locs:
            print(f"         0x{base_addr + loc:08X}")
        return locs[0]
    
    # Try partial matches
    for partial in ["A02B2247", "W052H", "16911"]:
        for encoding in ['utf-16-le', 'ascii']:
            data = partial.encode(encoding)
            locs = search_pattern(binary, data)
            if locs:
                print(f"    Partial '{partial}' ({encoding}) at {len(locs)} loc(s): "
                      f"0x{base_addr + locs[0]:08X}")
    
    return None


def create_usb_string_descriptor(text):
    """Create a USB String Descriptor from text."""
    encoded = text.encode('utf-16-le')
    length = 2 + len(encoded)
    return bytes([length, 0x03]) + encoded


def patch_serial_in_descriptor_table(ih, binary, base_addr, 
                                      old_serial, new_serial):
    """Patch serial string descriptor in the firmware."""
    print(f"\n[*] Patching serial: '{old_serial}' -> '{new_serial}'")
    
    if len(new_serial) > len(old_serial):
        print(f"[-] New serial ({len(new_serial)} chars) must be <= "
              f"old serial ({len(old_serial)} chars)")
        # Pad with spaces? Or truncate?
        new_serial = new_serial[:len(old_serial)]
        print(f"    Truncated to: '{new_serial}'")
    
    # Pad new serial to same length as old
    new_serial_padded = new_serial.ljust(len(old_serial), '\x00')
    
    old_desc = create_usb_string_descriptor(old_serial)
    new_desc = create_usb_string_descriptor(new_serial_padded)
    
    # Ensure same length
    if len(new_desc) < len(old_desc):
        new_desc = new_desc + b'\x00' * (len(old_desc) - len(new_desc))
    
    # Update length byte to reflect actual string (not padding)
    new_desc_real = create_usb_string_descriptor(new_serial)
    new_desc = bytes([new_desc_real[0]]) + new_desc[1:]
    
    return old_desc, new_desc


def analyze_and_patch(fw_path, new_serial=None, output_path=None):
    """Main analysis and patching flow."""
    ih, binary, base_addr = load_firmware(fw_path)
    
    # Analysis
    desc_offset, desc_data = find_usb_descriptors(binary, base_addr)
    str_offset = find_string_descriptors(binary, base_addr)
    find_serial_format(binary, base_addr)
    serial_loc = find_serial_string_buffer(binary, base_addr)
    
    if desc_data:
        serial_str_idx = desc_data[16]
        print(f"\n[+] Serial string index in device descriptor: {serial_str_idx}")
        
        # Find string descriptor table
        # Usually string descriptors are sequential in memory
        if str_offset is not None:
            print(f"[+] First string descriptor at offset 0x{str_offset:X}")
            print(f"    Looking for descriptor #{serial_str_idx}...")
            
            # Walk string descriptors from the found location
            # Go backwards to find descriptor #0 (language ID)
            # Then forward to find serial index
    
    print("\n" + "=" * 60)
    print("  ANALYSIS SUMMARY")
    print("=" * 60)
    
    if serial_loc is not None:
        print(f"\n[+] Serial string found in firmware at offset 0x{serial_loc:X}")
        print(f"    Address: 0x{base_addr + serial_loc:08X}")
        print("    This can be directly patched!")
        
        if new_serial and output_path:
            # Patch the serial
            old_utf16 = "A02B2247W052H16911".encode('utf-16-le')
            new_utf16 = new_serial.encode('utf-16-le')
            
            # Pad to same length
            if len(new_utf16) < len(old_utf16):
                new_utf16 += b'\x00' * (len(old_utf16) - len(new_utf16))
            elif len(new_utf16) > len(old_utf16):
                new_utf16 = new_utf16[:len(old_utf16)]
            
            # Patch in IntelHex
            patch_addr = base_addr + serial_loc
            for i, b in enumerate(new_utf16):
                ih[patch_addr + i] = b
            
            ih.write_hex_file(output_path)
            print(f"\n[+] Patched firmware written to: {output_path}")
            print(f"    Flash via bootloader to apply.")
    else:
        print("\n[!] Serial string NOT found as static data in firmware.")
        print("    The serial is generated dynamically at runtime.")
        print("    We need to patch the CODE that generates it.")
        print()
        print("    Approach: Find and patch the serial formatting function")
        print("    to return a hardcoded string instead of reading SPI flash.")


def main():
    print("=" * 60)
    print("  Startility - Firmware Serial Patcher")
    print("=" * 60)
    print()
    
    fw_path = FW_PATH
    if len(sys.argv) > 1:
        fw_path = sys.argv[1]
    
    if not os.path.exists(fw_path):
        print(f"[-] Firmware not found: {fw_path}")
        print("    Extract Wootility first or provide path as argument.")
        sys.exit(1)
    
    new_serial = None
    output_path = None
    
    if len(sys.argv) > 2:
        new_serial = sys.argv[2]
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "wooting_60he_arm_patched.fwr"
        )
    
    analyze_and_patch(fw_path, new_serial, output_path)


if __name__ == "__main__":
    main()
