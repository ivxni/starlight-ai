"""
Startility - Wooting Bootloader Deep Protocol Probe
====================================================
Probes the bootloader using discovered DFDB magic prefix.
The bootloader responds with DFDB FF 33 as status.

Firmware info:
  - STM32 ARM (flash @ 0x08000000)
  - Bootloader: 0x08000000 - 0x08006FFF (28KB)
  - Main FW:    0x08007000+
  - Serial stored on EXTERNAL SPI flash (not internal)
"""

import hid
import time
import struct
import sys

WOOTING_VID      = 0x31E3
WOOTING_BOOT_PID = 0x131F

DFDB = b"\xdf\xdb"
BOOT_STATUS = bytes.fromhex("dfdbff33")


def open_bootloader():
    """Open the bootloader HID device."""
    devices = hid.enumerate(WOOTING_VID, WOOTING_BOOT_PID)
    if not devices:
        print("[-] No bootloader device! Plug keyboard in bootloader mode.")
        print("    (Hold Backspace+Fn while plugging, or use --enter-bootloader)")
        sys.exit(1)
    
    dev = hid.device()
    dev.open_path(devices[0]['path'])
    dev.set_nonblocking(0)
    print(f"[+] Connected to bootloader: {devices[0].get('product_string')}")
    print(f"    Serial: {devices[0].get('serial_number')}")
    return dev


def send_and_read(dev, data, report_id=0, timeout=500):
    """Send output report and read response."""
    buf = bytes([report_id]) + data
    # Pad to 64 bytes (common HID report size)
    buf = buf + b"\x00" * max(0, 65 - len(buf))
    buf = buf[:65]
    
    try:
        dev.write(buf)
    except Exception as e:
        return None, str(e)
    
    time.sleep(0.05)
    
    try:
        resp = dev.read(64, timeout_ms=timeout)
        return bytes(resp) if resp else None, None
    except Exception as e:
        return None, str(e)


def send_feature_and_read(dev, data, report_id=0, timeout=500):
    """Send feature report and read response."""
    buf = bytes([report_id]) + data
    buf = buf + b"\x00" * max(0, 8 - len(buf))
    
    try:
        dev.send_feature_report(buf)
    except Exception as e:
        return None, str(e)
    
    time.sleep(0.05)
    
    try:
        resp = dev.read(64, timeout_ms=timeout)
        return bytes(resp) if resp else None, None
    except Exception as e:
        return None, str(e)


def is_status_response(data):
    """Check if response is just the default DFDB status."""
    if data and len(data) >= 4:
        return data[:4] == BOOT_STATUS
    return False


def probe_dfdb_commands(dev):
    """Try DFDB magic + various command bytes."""
    print("\n[*] Phase 1: DFDB magic + command byte scan")
    print("    Testing commands 0x00 - 0xFF with DFDB prefix...\n")
    
    interesting = []
    
    for cmd in range(0x00, 0x40):  # First 64 commands
        payload = DFDB + bytes([cmd])
        resp, err = send_and_read(dev, payload)
        
        if resp and not is_status_response(resp) and any(b != 0 for b in resp):
            print(f"  [!] CMD 0x{cmd:02X}: {resp[:32].hex()}")
            interesting.append((cmd, resp))
        elif resp and is_status_response(resp):
            pass  # Default status, skip
    
    if not interesting:
        print("  (No non-default responses found with DFDB prefix)")
    
    return interesting


def probe_raw_commands(dev):
    """Try various raw command bytes without magic prefix."""
    print("\n[*] Phase 2: Raw command scan (no magic prefix)")
    print("    Testing single-byte commands 0x00 - 0xFF...\n")
    
    interesting = []
    
    for cmd in range(0x00, 0x100):
        payload = bytes([cmd])
        resp, err = send_and_read(dev, payload)
        
        if resp and not is_status_response(resp) and any(b != 0 for b in resp):
            print(f"  [!] RAW 0x{cmd:02X}: {resp[:32].hex()}")
            interesting.append((cmd, resp))
    
    if not interesting:
        print("  (No non-default responses found)")
    
    return interesting


def probe_stm32_hid_bootloader(dev):
    """Try STM32 HID Bootloader protocol (page write format)."""
    print("\n[*] Phase 3: STM32 HID Bootloader protocol")
    
    # STM32 HID bootloader typically:
    # - Receives 1024-byte pages: [addr_LE_4bytes] [data_1024bytes]
    # - Responds with status byte
    
    # Try reading by sending address-only packets
    for addr, name in [
        (0x08000000, "bootloader_start"),
        (0x08007000, "firmware_start"),
        (0x1FFF0000, "system_memory"),
        (0x1FFF7800, "OTP"),
        (0x1FFFC000, "option_bytes"),
    ]:
        addr_bytes = struct.pack("<I", addr)
        resp, err = send_and_read(dev, addr_bytes)
        if resp and not is_status_response(resp) and any(b != 0 for b in resp):
            print(f"  [!] Addr 0x{addr:08X} ({name}): {resp[:32].hex()}")
        else:
            pass


def probe_intel_hex(dev):
    """Try sending Intel HEX records to the bootloader."""
    print("\n[*] Phase 4: Intel HEX record test")
    
    # The first line of the firmware: :020000040800F2
    hex_records = [
        b":020000040800F2\r\n",
        b":020000040800F2",
        b"\x02\x00\x00\x04\x08\x00",  # Binary equivalent
    ]
    
    for i, record in enumerate(hex_records):
        resp, err = send_and_read(dev, record)
        if resp and not is_status_response(resp) and any(b != 0 for b in resp):
            print(f"  [!] HEX record {i}: {resp[:32].hex()}")
        elif resp and is_status_response(resp):
            print(f"  [i] HEX record {i}: Got DFDB status (might have accepted it)")


def probe_two_byte_magic(dev):
    """Try various 2-byte magic prefixes."""
    print("\n[*] Phase 5: Two-byte magic prefix scan")
    
    # Test common magic prefixes similar to D1DA and DFDB
    magics = [
        b"\xd0\xda", b"\xd1\xda", b"\xd2\xda", b"\xdf\xdb",
        b"\xdb\xdf", b"\xda\xd1", b"\xff\xdb", b"\xdf\xff",
        b"\xd0\xd0", b"\xda\xda", b"\xdb\xdb", b"\xdc\xdc",
        b"\xab\xcd", b"\x55\xaa", b"\xaa\x55", b"\xfe\xed",
        b"\xca\xfe", b"\xde\xad", b"\xbe\xef",
        b"WR",  # "Wooting Restore"
        b"WB",  # "Wooting Bootloader"
        b"WF",  # "Wooting Flash"
    ]
    
    for magic in magics:
        for cmd in [0x00, 0x01, 0x02, 0x03, 0x10, 0xFF]:
            payload = magic + bytes([cmd])
            resp, err = send_and_read(dev, payload)
            if resp and not is_status_response(resp) and any(b != 0 for b in resp):
                print(f"  [!] Magic {magic.hex()} + CMD 0x{cmd:02X}: {resp[:32].hex()}")


def probe_chunked_data(dev):
    """Try sending data in various chunk formats."""
    print("\n[*] Phase 6: Chunked data format test")
    
    # Try sending a "start" command followed by data
    # Format: [length_16be] [data...]
    test_data = b"\x00\x10" + b"\x41" * 16  # 16 bytes of 'A'
    resp, err = send_and_read(dev, test_data)
    if resp and not is_status_response(resp) and any(b != 0 for b in resp):
        print(f"  [!] Chunked 16B: {resp[:32].hex()}")
    
    # Format: [cmd] [addr_32le] [length_16le] [data...]
    test_data2 = (bytes([0x01]) + struct.pack("<I", 0x08007000) + 
                  struct.pack("<H", 16) + b"\x41" * 16)
    resp, err = send_and_read(dev, test_data2)
    if resp and not is_status_response(resp) and any(b != 0 for b in resp):
        print(f"  [!] CMD+Addr+Data: {resp[:32].hex()}")


def probe_feature_reports(dev):
    """Probe various feature report IDs and sizes."""
    print("\n[*] Phase 7: Feature report exploration")
    
    for rid in range(0, 8):
        for size in [8, 16, 32, 64]:
            try:
                result = dev.get_feature_report(rid, size + 1)
                if result and any(b != 0 for b in result[1:]):
                    print(f"  [!] Feature Report ID={rid} Size={size}: "
                          f"{bytes(result[:min(32, len(result))]).hex()}")
            except:
                pass
    
    # Try setting feature reports with DFDB
    for rid in range(0, 4):
        payload = bytes([rid]) + DFDB + bytes([0x00]) + b"\x00" * 4
        try:
            dev.send_feature_report(payload)
            resp = dev.read(64, timeout_ms=300)
            if resp and any(b != 0 for b in resp):
                rdata = bytes(resp)
                if not is_status_response(rdata):
                    print(f"  [!] Feature Set RID={rid} DFDB response: {rdata[:32].hex()}")
        except:
            pass


def main():
    print("=" * 60)
    print("  Startility - Bootloader Deep Protocol Probe")
    print("=" * 60)
    print()
    
    dev = open_bootloader()
    
    try:
        # Clear any pending data
        while True:
            d = dev.read(64, timeout_ms=100)
            if not d:
                break
        
        probe_dfdb_commands(dev)
        probe_raw_commands(dev)
        probe_stm32_hid_bootloader(dev)
        probe_intel_hex(dev)
        probe_two_byte_magic(dev)
        probe_chunked_data(dev)
        probe_feature_reports(dev)
        
        print("\n" + "=" * 60)
        print("  Probe Complete")
        print("=" * 60)
        
    finally:
        dev.close()


if __name__ == "__main__":
    main()
