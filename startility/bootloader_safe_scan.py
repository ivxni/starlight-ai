"""
Startility - Wooting Bootloader Safe Command Scan
==================================================
Safely scans bootloader commands, skipping known state-changing ones.
Handles disconnects gracefully and auto-reconnects.

Discovered protocol:
  Magic: DFDB (via Feature Report RID=0)
  Response: DFDB [status1] [status2] [data...]
  status1=FF status2=88 -> ACK with data
  status1=FF status2=33 -> idle (default)
  status1=FF status2=FF -> state change (flash mode?)

Known commands:
  0x00 = GET_INFO      -> 01 ff (version 1, ok)
  0x01 = GET_PROTOCOL  -> 02 02 (protocol v2.2)
  0x02 = PREPARE/ERASE -> enters flash mode (DANGEROUS)
  0x03 = (related to 0x02 state)
  0x04 = STATUS        -> 04
"""

import hid
import time
import struct
import sys

WOOTING_VID      = 0x31E3
WOOTING_BOOT_PID = 0x131F
DFDB = b"\xdf\xdb"

# Commands that change bootloader state - SKIP these
DANGEROUS_CMDS = {0x02, 0x03}


def open_bootloader():
    devices = hid.enumerate(WOOTING_VID, WOOTING_BOOT_PID)
    if not devices:
        return None
    dev = hid.device()
    dev.open_path(devices[0]['path'])
    dev.set_nonblocking(0)
    return dev


def safe_flush(dev):
    """Flush pending data, handle errors."""
    try:
        dev.set_nonblocking(1)
        for _ in range(10):
            try:
                if not dev.read(64):
                    break
            except:
                break
        dev.set_nonblocking(0)
    except:
        pass


def send_dfdb(dev, cmd_byte, extra=b""):
    """Send DFDB command via feature report RID=0."""
    payload = DFDB + bytes([cmd_byte]) + extra
    report = bytes([0x00]) + payload + b"\x00" * max(0, 8 - 1 - len(payload))
    
    try:
        dev.send_feature_report(report)
        time.sleep(0.05)
        resp = dev.read(64, timeout_ms=500)
        return bytes(resp) if resp else None
    except:
        return None


def classify_response(resp):
    """Classify bootloader response."""
    if not resp or len(resp) < 4:
        return "none", b""
    
    if resp[0] != 0xdf or resp[1] != 0xdb:
        return "non-dfdb", resp
    
    s1 = resp[2]  # general status
    s2 = resp[3]  # command status
    data = resp[4:].rstrip(b"\x00")
    
    if s1 == 0xFF and s2 == 0x33:
        return "idle", data
    elif s1 == 0xFF and s2 == 0x88:
        return "ack", data
    elif s1 == 0xFF and s2 == 0xFF:
        return "state_change", data
    else:
        return f"unknown_{s1:02x}_{s2:02x}", data


def main():
    print("=" * 60)
    print("  Startility - Safe Bootloader Command Scan")
    print("=" * 60)
    print()
    
    dev = open_bootloader()
    if not dev:
        print("[-] No bootloader device!")
        sys.exit(1)
    print("[+] Connected to bootloader\n")
    
    # ── Phase 1: Full command scan (skip dangerous) ──────────
    print("[*] Phase 1: Command scan 0x00-0xFF (skipping 0x02,0x03)")
    print("-" * 60)
    
    found = {}
    
    for cmd in range(0x00, 0x100):
        if cmd in DANGEROUS_CMDS:
            continue
        
        safe_flush(dev)
        resp = send_dfdb(dev, cmd)
        
        if resp is None:
            # Device might have disconnected - try reconnect
            print(f"\n[!] Lost connection at CMD 0x{cmd:02X}, reconnecting...")
            try:
                dev.close()
            except:
                pass
            time.sleep(1)
            dev = open_bootloader()
            if not dev:
                print("[-] Reconnect failed! Replug keyboard in bootloader mode.")
                sys.exit(1)
            print("[+] Reconnected\n")
            continue
        
        rtype, data = classify_response(resp)
        
        if rtype == "ack":
            found[cmd] = ("ack", data, resp)
            print(f"  [ACK]  0x{cmd:02X}: data={data.hex() if data else '(empty)'}")
        elif rtype == "state_change":
            found[cmd] = ("state", data, resp)
            print(f"  [STATE] 0x{cmd:02X}: data={data.hex() if data else '(empty)'} "
                  f"(state change!)")
        elif rtype not in ("idle", "none"):
            found[cmd] = (rtype, data, resp)
            print(f"  [{rtype}] 0x{cmd:02X}: {resp[:16].hex()}")
    
    print(f"\n[+] Found {len(found)} responding commands\n")
    
    # ── Phase 2: Detailed probe of ACK commands ──────────────
    if found:
        print("[*] Phase 2: Detailed probe of responding commands")
        print("-" * 60)
        
        for cmd in sorted(found.keys()):
            rtype, _, _ = found[cmd]
            if rtype != "ack":
                continue
            
            print(f"\n  CMD 0x{cmd:02X} with varying data:")
            
            # Try with 1-4 extra bytes
            for extra in [
                b"\x00", b"\x01", b"\xff",
                b"\x00\x00", b"\x01\x00", b"\x00\x01",
                b"\x00\x00\x00\x00",
                b"\x00\x00\x00\x08",  # 0x08000000 LE
                b"\x00\x70\x00\x08",  # 0x08007000 LE
            ]:
                safe_flush(dev)
                resp = send_dfdb(dev, cmd, extra=extra)
                if resp:
                    rtype2, data2 = classify_response(resp)
                    if rtype2 == "ack" and data2:
                        print(f"    +{extra.hex():12s} -> {data2.hex()}")
                    elif rtype2 == "state_change":
                        print(f"    +{extra.hex():12s} -> STATE CHANGE! "
                              f"{resp[:12].hex()}")
                        # Reconnect if needed
                        break
    
    # ── Phase 3: Try to read flash regions ───────────────────
    print("\n[*] Phase 3: Flash read via ACK commands + address")
    print("-" * 60)
    
    addresses = [
        (0x08000000, "bootloader"),
        (0x08007000, "firmware"),
        (0x08060000, "upper flash"),
        (0x0807F000, "flash end"),
        (0x1FFF0000, "system mem"),
        (0x1FFF7800, "OTP area"),
        (0x20000000, "SRAM"),
    ]
    
    for cmd in sorted(found.keys()):
        rtype, _, _ = found[cmd]
        if rtype != "ack":
            continue
        
        for addr, name in addresses:
            addr_le = struct.pack("<I", addr)
            safe_flush(dev)
            resp = send_dfdb(dev, cmd, extra=addr_le)
            if resp:
                rtype2, data2 = classify_response(resp)
                if rtype2 == "ack" and data2 and len(data2) > 1:
                    print(f"  CMD 0x{cmd:02X} @ 0x{addr:08X} ({name}): "
                          f"{data2.hex()}")
    
    # ── Phase 4: Larger feature report test ──────────────────
    print("\n[*] Phase 4: Larger payload test")
    print("-" * 60)
    
    # The feature report is 7 bytes data. But maybe we can use output
    # reports for larger data transfers to the bootloader.
    # Try output report with DFDB prefix
    for rid in [0, 1, 2, 3]:
        for cmd in [0x00, 0x01, 0x04]:
            payload = DFDB + bytes([cmd]) + b"\x00" * 59
            buf = bytes([rid]) + payload
            buf = buf[:65]
            try:
                dev.write(buf)
                time.sleep(0.1)
                resp = dev.read(64, timeout_ms=300)
                if resp:
                    resp = bytes(resp)
                    rtype, data = classify_response(resp)
                    if rtype not in ("idle", "none"):
                        print(f"  Output RID={rid} CMD=0x{cmd:02X}: "
                              f"[{rtype}] {data.hex() if data else ''}")
            except:
                pass
    
    print("\n" + "=" * 60)
    print("  Scan Complete")
    print("=" * 60)
    
    # Summary
    print("\n[*] Command Summary:")
    print("  0x00 = GET_INFO (version/status)")
    print("  0x01 = GET_PROTOCOL (protocol version)")
    print("  0x02 = PREPARE (state change - SKIP)")
    print("  0x03 = (state change related - SKIP)")
    print("  0x04 = STATUS/ECHO")
    for cmd in sorted(found.keys()):
        if cmd > 0x04:
            rtype, data, _ = found[cmd]
            print(f"  0x{cmd:02X} = [{rtype}] data={data.hex() if data else '?'}")
    
    dev.close()


if __name__ == "__main__":
    main()
