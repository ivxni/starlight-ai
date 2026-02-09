"""
Startility - Wooting Bootloader Feature Report Command Scan
============================================================
Scans all DFDB command bytes via Feature Report RID=0.
The bootloader confirmed responding to DFDB via feature reports.

Response format:
  DFDB FF [status] [data...]
  status 33 = idle
  status 88 = acknowledged/has data
"""

import hid
import time
import struct
import sys

WOOTING_VID      = 0x31E3
WOOTING_BOOT_PID = 0x131F

DFDB = b"\xdf\xdb"
STATUS_IDLE = 0x33
STATUS_ACK  = 0x88


def open_bootloader():
    devices = hid.enumerate(WOOTING_VID, WOOTING_BOOT_PID)
    if not devices:
        print("[-] No bootloader device found!")
        sys.exit(1)
    
    dev = hid.device()
    dev.open_path(devices[0]['path'])
    dev.set_nonblocking(0)
    print(f"[+] Connected: {devices[0].get('product_string')} "
          f"(Serial: {devices[0].get('serial_number')})")
    return dev


def flush(dev):
    """Flush any pending data."""
    dev.set_nonblocking(1)
    while dev.read(64):
        pass
    dev.set_nonblocking(0)


def send_dfdb_feature(dev, cmd_byte, extra=b"", read_size=64, timeout=500):
    """Send DFDB + cmd via feature report RID=0, read response."""
    payload = DFDB + bytes([cmd_byte]) + extra
    # Feature report: [RID=0] [payload...] padded to 8 bytes
    report = bytes([0x00]) + payload + b"\x00" * max(0, 8 - 1 - len(payload))
    
    try:
        dev.send_feature_report(report)
    except Exception as e:
        return None, f"send error: {e}"
    
    time.sleep(0.05)
    
    try:
        resp = dev.read(read_size, timeout_ms=timeout)
        return bytes(resp) if resp else None, None
    except Exception as e:
        return None, f"read error: {e}"


def parse_response(resp):
    """Parse DFDB response."""
    if not resp or len(resp) < 4:
        return None, None, None
    
    if resp[0:2] != DFDB[:2] and resp[0:2] != b"\xdf\xdb":
        # Check if first two bytes match
        if resp[0] != 0xdf or resp[1] != 0xdb:
            return "non-dfdb", resp[0], resp[1:]
    
    status = resp[2] if len(resp) > 2 else None
    cmd_status = resp[3] if len(resp) > 3 else None
    data = resp[4:] if len(resp) > 4 else b""
    
    return status, cmd_status, data


def scan_all_commands(dev):
    """Scan all 256 command bytes."""
    print("\n" + "=" * 60)
    print("[*] DFDB Command Scan (Feature Report RID=0)")
    print("    Scanning 0x00 - 0xFF...")
    print("=" * 60 + "\n")
    
    results = {}
    
    for cmd in range(0x00, 0x100):
        flush(dev)
        resp, err = send_dfdb_feature(dev, cmd)
        
        if err:
            continue
        
        if resp:
            status, cmd_status, data = parse_response(resp)
            
            # Classify response
            if status == 0xFF and cmd_status == STATUS_IDLE:
                # Default idle - boring
                pass
            elif status == 0xFF and cmd_status == STATUS_ACK:
                # Acknowledged with data!
                data_trimmed = data.rstrip(b"\x00")
                results[cmd] = resp
                print(f"  [ACK] CMD 0x{cmd:02X}: status=0xFF,0x88 "
                      f"data={data_trimmed.hex() if data_trimmed else '(empty)'}")
            elif status != 0xFF or cmd_status not in (STATUS_IDLE, STATUS_ACK):
                # Unexpected response
                results[cmd] = resp
                print(f"  [???] CMD 0x{cmd:02X}: full={resp[:16].hex()}")
            # else: idle, skip
    
    return results


def detailed_probe(dev, cmd_byte):
    """Probe a specific command with various data payloads."""
    print(f"\n[*] Detailed probe for CMD 0x{cmd_byte:02X}")
    
    # Try with different extra data bytes
    for extra_len in range(0, 5):
        for val in [0x00, 0x01, 0xFF]:
            extra = bytes([val]) * extra_len if extra_len > 0 else b""
            flush(dev)
            resp, err = send_dfdb_feature(dev, cmd_byte, extra=extra)
            
            if resp:
                data_trimmed = resp.rstrip(b"\x00")
                if len(data_trimmed) > 4:  # More than just header
                    print(f"  Extra={extra.hex() if extra else 'none':12s} -> "
                          f"{data_trimmed.hex()}")


def probe_flash_read(dev):
    """Try to read flash via bootloader using discovered commands."""
    print("\n" + "=" * 60)
    print("[*] Flash Read Attempt")
    print("=" * 60 + "\n")
    
    # Try sending addresses with various command bytes
    # Use commands that gave ACK responses
    for cmd in [0x00, 0x01, 0x02, 0x03]:
        for addr in [0x08000000, 0x08007000, 0x20000000]:
            addr_bytes = struct.pack("<I", addr)
            flush(dev)
            resp, err = send_dfdb_feature(dev, cmd, extra=addr_bytes)
            
            if resp:
                _, cmd_status, data = parse_response(resp)
                data_trimmed = data.rstrip(b"\x00") if data else b""
                if cmd_status == STATUS_ACK and data_trimmed:
                    print(f"  CMD 0x{cmd:02X} @ 0x{addr:08X}: {data_trimmed.hex()}")


def probe_write_serial_path(dev):
    """Explore if we can write to external SPI flash (serial storage)."""
    print("\n" + "=" * 60)
    print("[*] SPI Flash / Serial Write Path Exploration")
    print("=" * 60 + "\n")
    
    # Try D1DA commands through the bootloader feature report
    # Maybe the bootloader forwards some D1DA commands
    d1da_cmds = [
        (0x00, "PING"),
        (0x01, "GET_VERSION"),
        (0x03, "GET_SERIAL"),
        (0x13, "GET_DEVICE_CONFIG"),
        (0x2B, "RESET_FLASH"),
        (0x38, "IS_FLASH_CONNECTED"),
        (0x3A, "GET_FLASH_STATS"),
    ]
    
    for cmd, name in d1da_cmds:
        # Try via DFDB
        flush(dev)
        resp, err = send_dfdb_feature(dev, cmd)
        if resp:
            _, cmd_status, data = parse_response(resp)
            data_trimmed = data.rstrip(b"\x00") if data else b""
            if cmd_status == STATUS_ACK:
                print(f"  DFDB+{name} (0x{cmd:02X}): ACK data={data_trimmed.hex()}")
        
        # Try via D1DA through feature report
        payload = b"\xd1\xda" + bytes([cmd])
        report = bytes([0x00]) + payload + b"\x00" * max(0, 7 - len(payload))
        try:
            dev.send_feature_report(report)
            time.sleep(0.05)
            resp2 = dev.read(64, timeout_ms=300)
            if resp2:
                resp2 = bytes(resp2)
                r_trimmed = resp2.rstrip(b"\x00")
                if r_trimmed and r_trimmed != DFDB + b"\xff\x33":
                    print(f"  D1DA+{name} (0x{cmd:02X}): {r_trimmed.hex()}")
        except:
            pass


def main():
    print("=" * 60)
    print("  Startility - Bootloader Feature Scan")
    print("=" * 60)
    print()
    
    dev = open_bootloader()
    
    try:
        flush(dev)
        
        # Phase 1: Scan all commands
        results = scan_all_commands(dev)
        
        print(f"\n[+] Found {len(results)} non-idle responses")
        
        # Phase 2: Detailed probe of interesting commands
        if results:
            for cmd in sorted(results.keys()):
                detailed_probe(dev, cmd)
        
        # Phase 3: Flash read attempts
        probe_flash_read(dev)
        
        # Phase 4: SPI flash / serial exploration
        probe_write_serial_path(dev)
        
        print("\n" + "=" * 60)
        print("  Scan Complete")
        print("=" * 60)
        
    finally:
        dev.close()


if __name__ == "__main__":
    main()
