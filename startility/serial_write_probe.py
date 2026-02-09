"""
Startility - Serial Write Command Probe
========================================
The 0xAA status commands (0x41-0x50) likely need data parameters.
These could be SET/WRITE commands for hardware properties.

Evidence:
  0x3F returns 0x16 (22 = Year from serial)
  0x48 returns 0x05 (5 = RevisionNumber from serial)
  0x41-0x44, 0x46-0x47, 0x4D-0x50 return 0xAA (needs params)

Strategy: Send each AA command with various data formats,
then check if serial or hardware properties changed.
"""

import hid
import time
import struct
import sys

WOOTING_VID      = 0x31E3
WOOTING_60HE_PID = 0x1312
D1DA = b"\xd1\xda"

# Current serial field values
CURRENT_SERIAL = {
    'supplier': 2,
    'year': 22,     # 0x16
    'week': 47,     # 0x2F
    'revision': 5,  # 0x05
    'prod_id': 2,   # 0x02
    'prod_num': 16911,  # 0x420F
    'stage': 0,
}

# Commands that returned AA (need parameters)
AA_CMDS = [0x3C, 0x41, 0x42, 0x43, 0x44, 0x46, 0x47, 0x4D, 0x4E, 0x4F, 0x50]

# Commands that returned FF (possible write ack)
FF_CMDS = [0x3F, 0x40]

# GET commands that read serial-related data
SERIAL_GETTERS = {
    0x3F: ('year?', 0x16),
    0x48: ('revision?', 0x05),
    0x3E: ('prod_id?', 0x02),
    0x45: ('prod_id2?', 0x02),
}


def open_device():
    devices = hid.enumerate(WOOTING_VID, WOOTING_60HE_PID)
    for dev in devices:
        if dev.get('usage_page') == 0xFF55:
            d = hid.device()
            d.open_path(dev['path'])
            d.set_nonblocking(0)
            return d, dev.get('serial_number', '')
    return None, ''


def send_feature_cmd(dev, cmd_byte, extra=b""):
    """Send via feature report RID=1 (small payload, 7 bytes max)."""
    payload = D1DA + bytes([cmd_byte]) + extra
    report = bytes([0x01]) + payload + b"\x00" * max(0, 8 - 1 - len(payload))
    try:
        dev.send_feature_report(report)
        time.sleep(0.05)
        resp = dev.read(64, timeout_ms=500)
        return bytes(resp) if resp else None
    except:
        return None


def send_output_cmd(dev, cmd_byte, data=b"", report_id=2):
    """Send via output report (larger payload)."""
    # Format: D1DA + CMD + size(2 bytes BE) + padding + data
    size = len(data)
    payload = D1DA + bytes([cmd_byte]) + struct.pack("!H", size) + b"\x00" + data
    buf = bytes([report_id]) + payload + b"\x00" * max(0, 63 - len(payload))
    buf = buf[:64]
    try:
        dev.write(buf)
        time.sleep(0.1)
        resp = dev.read(128, timeout_ms=500)
        return bytes(resp) if resp else None
    except:
        return None


def get_serial(dev):
    """Read current serial via GET_SERIAL."""
    resp = send_feature_cmd(dev, 0x03)
    if resp:
        for i in range(len(resp) - 1):
            if resp[i] == 0xd1 and resp[i+1] == 0xda:
                payload_len = resp[i+4] if i+4 < len(resp) else 0
                data = resp[i+6:i+6+payload_len]
                return data
    return None


def get_usb_serial(dev_obj):
    """Re-enumerate to get USB serial string."""
    try:
        dev_obj.close()
    except:
        pass
    time.sleep(0.5)
    devices = hid.enumerate(WOOTING_VID, WOOTING_60HE_PID)
    for d in devices:
        if d.get('usage_page') == 0xFF55:
            return d.get('serial_number', '')
    return ''


def parse_status(resp):
    """Get status byte from response."""
    if not resp:
        return None
    for i in range(len(resp) - 3):
        if resp[i] == 0xd1 and resp[i+1] == 0xda:
            return resp[i+3]
    return None


def main():
    print("=" * 60)
    print("  Startility - Serial Write Command Probe")
    print("=" * 60)
    print()
    
    dev, usb_serial = open_device()
    if not dev:
        print("[-] No keyboard found!")
        sys.exit(1)
    
    print(f"[+] Connected (USB Serial: {usb_serial})")
    
    # Read current serial
    serial_before = get_serial(dev)
    print(f"[+] Current serial data: {serial_before.hex() if serial_before else 'N/A'}")
    
    # ── Phase 1: Read serial-related fields ──────────────────
    print("\n[*] Phase 1: Reading serial-related fields")
    print("-" * 60)
    
    for cmd, (name, expected) in SERIAL_GETTERS.items():
        resp = send_feature_cmd(dev, cmd)
        status = parse_status(resp)
        print(f"  CMD 0x{cmd:02X} ({name}): status=0x{status:02X} "
              f"resp={resp[4:12].hex() if resp else 'N/A'}")
    
    # ── Phase 2: Probe AA commands with serial data ──────────
    print("\n[*] Phase 2: Testing AA commands with data payloads")
    print("-" * 60)
    print("    Using SAFE read-only probes first...")
    
    # Try each AA command with the CURRENT serial bytes as data
    # This should be safe since we're writing back the same values
    serial_bytes = serial_before if serial_before else bytes(11)
    
    for cmd in AA_CMDS:
        # Try via feature report (small payload)
        for extra in [
            bytes([0x01]),           # Single byte
            bytes([0x00, 0x0B]),     # Length prefix + 11
            serial_bytes[:4],        # First 4 serial bytes
        ]:
            resp = send_feature_cmd(dev, cmd, extra=extra)
            status = parse_status(resp)
            if status and status != 0xAA:
                print(f"  [!] CMD 0x{cmd:02X} + {extra.hex():12s} -> "
                      f"status=0x{status:02X} (CHANGED from AA!)")
                if resp:
                    print(f"       Full: {resp[:20].hex()}")
        
        # Try via output report (larger payload with protobuf-style format)
        for data in [
            serial_bytes,  # Full serial data
            b"\x0a\x0b" + serial_bytes,  # Protobuf field 1, length 11
        ]:
            resp = send_output_cmd(dev, cmd, data=data)
            status = parse_status(resp)
            if status and status != 0xAA and status is not None:
                print(f"  [!] CMD 0x{cmd:02X} (output) + {data[:8].hex():16s} -> "
                      f"status=0x{status:02X}")
                if resp:
                    print(f"       Full: {resp[:20].hex()}")
    
    # ── Phase 3: Probe FF commands with data ─────────────────
    print("\n[*] Phase 3: Testing FF-status commands with data")
    print("-" * 60)
    
    for cmd in FF_CMDS:
        # Read current value first
        resp0 = send_feature_cmd(dev, cmd)
        print(f"  CMD 0x{cmd:02X} current: {resp0[4:12].hex() if resp0 else 'N/A'}")
        
        # Try sending same value back (safe)
        for extra in [
            bytes([0x16]),  # Year=22
            bytes([0x00]),
            bytes([0x01]),
            bytes([0xFF]),
        ]:
            resp = send_feature_cmd(dev, cmd, extra=extra)
            status = parse_status(resp)
            if resp:
                s = status if status is not None else 0
                print(f"    + {extra.hex()} -> status=0x{s:02X} "
                      f"resp={resp[4:12].hex()}")
    
    # ── Phase 4: Check if serial changed ─────────────────────
    print("\n[*] Phase 4: Checking if serial changed")
    print("-" * 60)
    
    serial_after = get_serial(dev)
    print(f"  Before: {serial_before.hex() if serial_before else 'N/A'}")
    print(f"  After:  {serial_after.hex() if serial_after else 'N/A'}")
    
    if serial_before != serial_after:
        print("  >> SERIAL DATA CHANGED! <<")
    else:
        print("  Serial data unchanged (as expected for safe probes)")
    
    # ── Phase 5: Try paired GET/SET pattern ──────────────────
    print("\n[*] Phase 5: Testing GET/SET command pairs")
    print("-" * 60)
    print("    Looking for SAVE/WRITE commands near known GETs...\n")
    
    # The protocol pattern: GET=even, SET=odd? Or GET first, SET after?
    # GET_SERIAL=0x03, maybe SET_SERIAL is nearby in manufacturing range
    # Test 0x3C-0x50 range with protobuf-encoded serial data
    
    # Build protobuf-like payload for SerialNumber
    # Field 1 (supplier): varint, key=0x08
    # Field 2 (year): varint, key=0x10  
    # Field 3 (week): varint, key=0x18
    # etc.
    proto_serial = (
        bytes([0x08]) + bytes([CURRENT_SERIAL['supplier']]) +    # field 1: supplier=2
        bytes([0x10]) + bytes([CURRENT_SERIAL['year']]) +         # field 2: year=22
        bytes([0x18]) + bytes([CURRENT_SERIAL['week']]) +         # field 3: week=47
        bytes([0x20]) + bytes([CURRENT_SERIAL['prod_num'] & 0x7F]) +  # field 4: product (varint)
        bytes([0x28]) + bytes([CURRENT_SERIAL['revision']]) +     # field 5: revision=5
        bytes([0x30]) + bytes([CURRENT_SERIAL['prod_id']]) +      # field 6: prod_id=2
        bytes([0x38]) + bytes([CURRENT_SERIAL['stage']])           # field 7: stage=0
    )
    
    # Wrap in HardwareProperties field 1
    hw_props = bytes([0x0a, len(proto_serial)]) + proto_serial
    
    print(f"  Protobuf serial: {proto_serial.hex()}")
    print(f"  HW properties:   {hw_props.hex()}")
    print()
    
    # Try sending protobuf data to AA commands via output report
    for cmd in [0x41, 0x42, 0x43, 0x44, 0x46, 0x47]:
        resp = send_output_cmd(dev, cmd, data=proto_serial)
        status = parse_status(resp)
        if status and status == 0x88:
            print(f"  [!!] CMD 0x{cmd:02X} ACCEPTED protobuf serial! "
                  f"status=0x{status:02X}")
            if resp:
                print(f"       resp={resp[:20].hex()}")
        elif status and status != 0xAA:
            print(f"  [?]  CMD 0x{cmd:02X}: status=0x{status:02X}")
    
    # Also try HW properties wrapper
    for cmd in [0x41, 0x42, 0x43, 0x44]:
        resp = send_output_cmd(dev, cmd, data=hw_props)
        status = parse_status(resp)
        if status and status == 0x88:
            print(f"  [!!] CMD 0x{cmd:02X} ACCEPTED hw_props! "
                  f"status=0x{status:02X}")
        elif status and status != 0xAA:
            print(f"  [?]  CMD 0x{cmd:02X} hw_props: status=0x{status:02X}")
    
    # Final serial check
    serial_final = get_serial(dev)
    print(f"\n  Final serial: {serial_final.hex() if serial_final else 'N/A'}")
    if serial_before != serial_final:
        print("  >> SERIAL CHANGED! WE FOUND THE WRITE COMMAND! <<")
    else:
        print("  Serial unchanged -> Need firmware patch approach")
    
    dev.close()


if __name__ == "__main__":
    main()
