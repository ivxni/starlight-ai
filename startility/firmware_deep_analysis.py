"""
Startility - Deep Firmware Analysis
====================================
Find the serial generation code and USB descriptor handling.
"""

import struct
import os
from intelhex import IntelHex

FW_PATH = os.path.join(os.environ.get('TEMP', '/tmp'),
                       'wootility-src', 'dist', 'fw', 'wooting_60_he_arm.fwr')


def load_fw():
    ih = IntelHex(FW_PATH)
    start = ih.minaddr()
    end = ih.maxaddr()
    binary = ih.tobinarray(start=start, size=end - start + 1)
    return bytes(binary), start


def hex_ascii_dump(data, base_addr, offset, width=48):
    """Print hex + ASCII dump of a region."""
    for i in range(0, width, 16):
        chunk = data[offset + i:offset + i + 16]
        addr = base_addr + offset + i
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {addr:08X}: {hex_str:<48s} {ascii_str}")


def main():
    binary, base = load_fw()
    
    # ============================================================
    # 1. Format string at 0x0802C54B
    # ============================================================
    print("=" * 70)
    print(" 1. Serial format string region (0x0802C540 - 0x0802C5B0)")
    print("=" * 70)
    offset = 0x0802C540 - base
    hex_ascii_dump(binary, base, offset, 112)
    
    # Decode the format string
    fmt_offset = 0x0802C54B - base
    fmt_end = binary.index(0, fmt_offset)
    fmt_str = binary[fmt_offset:fmt_end]
    print(f"\n  Format string at 0x0802C54B: '{fmt_str.decode('ascii')}'")
    print(f"  Length: {len(fmt_str)} bytes (+1 null = {len(fmt_str)+1})")
    
    # ============================================================
    # 2. Wooting string region 
    # ============================================================
    print("\n" + "=" * 70)
    print(" 2. Product string region (0x0802C620 - 0x0802C680)")
    print("=" * 70)
    offset = 0x0802C620 - base
    hex_ascii_dump(binary, base, offset, 112)
    
    # ============================================================
    # 3. Find ALL format strings with % to map serial generation
    # ============================================================
    print("\n" + "=" * 70)
    print(" 3. All format strings containing % in data section")
    print("=" * 70)
    
    # Data section is roughly the upper part of firmware
    data_start = 0x08028000 - base  # approximate
    idx = data_start
    while idx < len(binary) - 1:
        if binary[idx] == 0x25:  # '%'
            # Find the start of this string (walk back to null or non-printable)
            str_start = idx
            while str_start > 0 and binary[str_start - 1] >= 0x20 and binary[str_start - 1] < 0x7F:
                str_start -= 1
            # Find end
            str_end = idx
            while str_end < len(binary) and binary[str_end] != 0:
                str_end += 1
            
            s = binary[str_start:str_end]
            if len(s) > 2 and len(s) < 80:
                try:
                    text = s.decode('ascii')
                    addr = base + str_start
                    if '%' in text and 'serial' not in text.lower():
                        # Show all format strings, filter later
                        pass
                    if any(c in text for c in ['serial', 'Serial', 'usb', 'USB', 
                                                 'desc', 'string', 'vid', 'pid',
                                                 'product', 'manuf', '%02u', '%05']):
                        print(f"  0x{addr:08X}: '{text}'")
                except:
                    pass
            idx = str_end + 1
        else:
            idx += 1
    
    # ============================================================
    # 4. Search for stage letters and serial-related ASCII strings
    # ============================================================
    print("\n" + "=" * 70)
    print(" 4. Serial/stage related strings")
    print("=" * 70)
    
    for pattern in [b"stage", b"Stage", b"serial", b"Serial",
                    b"supplier", b"Supplier", b"revision", b"Revision",
                    b"product_n", b"Product_n", b"hardware",
                    b"hw_prop", b"spi_flash", b"SPI",
                    b"usb_desc", b"USB_desc", b"usbd_", b"USBD_",
                    b"iSerial", b"iProduct", b"iManufact",
                    b"string_desc", b"STR_DESC"]:
        idx = 0
        while True:
            idx = binary.find(pattern, idx)
            if idx < 0:
                break
            # Get context
            s_start = idx
            while s_start > 0 and binary[s_start - 1] >= 0x20:
                s_start -= 1
            s_end = idx + len(pattern)
            while s_end < len(binary) and binary[s_end] >= 0x20 and binary[s_end] < 0x7F:
                s_end += 1
            text = binary[s_start:s_end]
            try:
                print(f"  0x{base + s_start:08X}: '{text.decode('ascii')}'")
            except:
                print(f"  0x{base + s_start:08X}: {text.hex()}")
            idx += len(pattern)
    
    # ============================================================
    # 5. Find references to the format string address in code
    # ============================================================
    print("\n" + "=" * 70)
    print(" 5. Code references to serial format string")
    print("=" * 70)
    
    # On ARM Thumb, a string reference is typically loaded via:
    #   LDR Rx, [PC, #offset]  -> loads a pointer from literal pool
    #   The literal pool entry contains the actual address
    
    fmt_addr = 0x0802C54B
    fmt_addr_le = struct.pack("<I", fmt_addr)
    
    locs = []
    idx = 0
    while True:
        idx = binary.find(fmt_addr_le, idx)
        if idx < 0:
            break
        addr = base + idx
        print(f"  Literal pool reference at 0x{addr:08X}")
        # Show surrounding code (look back for the LDR instruction)
        ctx_start = max(0, idx - 32)
        hex_ascii_dump(binary, base, ctx_start, 64)
        locs.append(idx)
        idx += 4
    
    if not locs:
        print("  No direct references found.")
        print("  Trying nearby addresses (compiler may use different alignment)...")
        for try_addr in range(fmt_addr - 4, fmt_addr + 5):
            addr_le = struct.pack("<I", try_addr)
            idx = 0
            while True:
                idx = binary.find(addr_le, idx)
                if idx < 0:
                    break
                print(f"  Reference to 0x{try_addr:08X} at offset 0x{base + idx:08X}")
                ctx_start = max(0, idx - 32)
                hex_ascii_dump(binary, base, ctx_start, 64)
                idx += 4
    
    # Also look for Wooting string references
    wooting_addr = 0x0802C638
    print(f"\n  References to 'Wooting' string (0x{wooting_addr:08X}):")
    for try_addr in range(wooting_addr - 2, wooting_addr + 3):
        addr_le = struct.pack("<I", try_addr)
        idx = 0
        while True:
            idx = binary.find(addr_le, idx)
            if idx < 0:
                break
            loc_addr = base + idx
            print(f"  -> 0x{loc_addr:08X} (ref to 0x{try_addr:08X})")
            ctx_start = max(0, idx - 16)
            hex_ascii_dump(binary, base, ctx_start, 48)
            idx += 4
    
    # ============================================================
    # 6. Look for USB VID/PID in different formats
    # ============================================================
    print("\n" + "=" * 70)
    print(" 6. USB VID/PID search (various encodings)")
    print("=" * 70)
    
    # Try various representations
    for vid, pid, desc in [(0x31E3, 0x1312, "normal"),
                            (0x31E3, 0x131F, "bootloader")]:
        for name, pattern in [
            (f"VID:PID LE", struct.pack("<HH", vid, pid)),
            (f"VID LE only", struct.pack("<H", vid)),
            (f"PID LE only", struct.pack("<H", pid)),
        ]:
            locs = []
            idx = 0
            while True:
                idx = binary.find(pattern, idx)
                if idx < 0:
                    break
                locs.append(base + idx)
                idx += 1
            if locs and len(locs) < 10:
                print(f"  {name} ({desc}) 0x{vid:04X}:0x{pid:04X}: "
                      f"{', '.join(f'0x{a:08X}' for a in locs)}")
    
    # ============================================================
    # 7. Examine the %c at 0x0801DFEC (in code section)
    # ============================================================
    print("\n" + "=" * 70)
    print(" 7. Code around %c reference (0x0801DFE0)")
    print("=" * 70)
    offset = 0x0801DFE0 - base
    hex_ascii_dump(binary, base, offset, 64)
    
    # ============================================================
    # 8. Look for snprintf/sprintf patterns near format string
    # ============================================================
    print("\n" + "=" * 70)
    print(" 8. Scanning for BL (branch-link) near format string refs")
    print("=" * 70)
    
    # ARM Thumb BL is 4-byte instruction: 11110... followed by 11...
    # We look for function calls in the code that might be near
    # where the format string pointer is loaded
    
    # The format string is likely used by a serial generation function
    # Let's look for all references to addresses in the 0x0802C54x range
    print("  Searching for pointers to 0x0802C540-0x0802C560 range...")
    for target in range(0x0802C540, 0x0802C560):
        target_le = struct.pack("<I", target)
        idx = 0
        while True:
            idx = binary.find(target_le, idx)
            if idx < 0:
                break
            addr = base + idx
            # Only show if it's in a reasonable literal pool location 
            # (code section, word-aligned)
            if idx % 4 == 0 and idx < (0x08028000 - base):
                print(f"  0x{addr:08X}: ptr -> 0x{target:08X}")
                # Show code context before this literal
                ctx_start = max(0, idx - 48)
                hex_ascii_dump(binary, base, ctx_start, 80)
                print()
            idx += 4


if __name__ == "__main__":
    main()
