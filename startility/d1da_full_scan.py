"""
Startility - D1DA Full Command Scan
====================================
Scans ALL 256 D1DA command bytes in normal mode to find
hidden/undocumented commands, especially SET_SERIAL.

Known commands: 0x00-0x3B
Manufacturing might use higher command numbers for:
  - SET_SERIAL
  - SET_HARDWARE_PROPERTIES
  - WRITE_MANUFACTURING_DATA
"""

import hid
import time
import sys

WOOTING_VID      = 0x31E3
WOOTING_60HE_PID = 0x1312
D1DA = b"\xd1\xda"

# Known commands for reference
KNOWN_CMDS = {
    0x00: "PING", 0x01: "GET_VERSION", 0x02: "RESET_TO_BOOTLOADER",
    0x03: "GET_SERIAL", 0x04: "GET_RGB_PROFILE_COUNT",
    0x07: "RELOAD_PROFILE0", 0x08: "SAVE_RGB_PROFILE",
    0x09: "GET_DIGITAL_PROFILES_COUNT", 0x0A: "GET_ANALOG_PROFILES_COUNT",
    0x0B: "GET_CURRENT_KB_PROFILE_IDX", 0x0C: "GET_DIGITAL_PROFILE",
    0x0D: "GET_ANALOG_PROFILE_MAIN", 0x0E: "GET_ANALOG_CURVE_MAP1",
    0x0F: "GET_ANALOG_CURVE_MAP2", 0x10: "GET_NUMBER_OF_KEYS",
    0x11: "GET_MAIN_MAPPING", 0x12: "GET_FUNCTION_MAPPING",
    0x13: "GET_DEVICE_CONFIG", 0x14: "GET_ANALOG_VALUES",
    0x15: "KEYS_OFF", 0x16: "KEYS_ON",
    0x17: "ACTIVATE_PROFILE", 0x18: "GET_DKS_PROFILE",
    0x19: "DO_SOFT_RESET", 0x1D: "REFRESH_RGB_COLORS",
    0x1E: "WOOT_DEV_SINGLE_COLOR", 0x1F: "WOOT_DEV_RESET_COLOR",
    0x20: "WOOT_DEV_RESET_ALL", 0x21: "WOOT_DEV_INIT",
    0x23: "GET_RGB_COLOR_PART1", 0x24: "GET_RGB_COLOR_PART2",
    0x26: "RELOAD_PROFILE", 0x27: "GET_KEYBOARD_PROFILE",
    0x28: "GET_GAMEPAD_MAPPING", 0x29: "GET_GAMEPAD_PROFILE",
    0x2A: "SAVE_KEYBOARD_PROFILE", 0x2B: "RESET_FLASH",
    0x2C: "SET_RAW_SCANNING", 0x2D: "START_XINPUT_DETECTION",
    0x2E: "STOP_XINPUT_DETECTION", 0x2F: "SAVE_DKS_PROFILE",
    0x30: "GET_MAPPING_PROFILE", 0x31: "GET_ACTUATION_PROFILE",
    0x32: "GET_RGB_PROFILE_CORE", 0x33: "GET_GLOBAL_SETTINGS",
    0x34: "GET_AKC_PROFILE", 0x35: "SAVE_AKC_PROFILE",
    0x36: "GET_RAPID_TRIGGER_PROFILE", 0x37: "GET_PROFILE_METADATA",
    0x38: "IS_FLASH_CONNECTED", 0x39: "GET_RGB_LAYER",
    0x3A: "GET_FLASH_STATS", 0x3B: "GET_RGB_BINS",
}

# Skip these - they have side effects
SKIP_CMDS = {
    0x02,  # RESET_TO_BOOTLOADER
    0x19,  # DO_SOFT_RESET
    0x2B,  # RESET_FLASH
}


def open_device():
    devices = hid.enumerate(WOOTING_VID, WOOTING_60HE_PID)
    for dev in devices:
        if dev.get('usage_page') == 0xFF55:
            d = hid.device()
            d.open_path(dev['path'])
            d.set_nonblocking(0)
            return d
    return None


def send_cmd(dev, cmd_byte):
    payload = D1DA + bytes([cmd_byte])
    report = bytes([0x01]) + payload + b"\x00" * (8 - 1 - len(payload))
    try:
        dev.send_feature_report(report)
        time.sleep(0.05)
        resp = dev.read(64, timeout_ms=500)
        return bytes(resp) if resp else None
    except:
        return None


def parse_response(resp):
    """Parse D1DA response, return (cmd_echo, status, data)."""
    if not resp or len(resp) < 5:
        return None, None, b""
    
    # Find D1DA marker
    for i in range(len(resp) - 1):
        if resp[i] == 0xd1 and resp[i+1] == 0xda:
            cmd_echo = resp[i+2] if i+2 < len(resp) else None
            status = resp[i+3] if i+3 < len(resp) else None
            data_len = resp[i+4] if i+4 < len(resp) else 0
            data_start = i + 6  # skip D1DA(2)+cmd(1)+status(1)+len(1)+pad(1)
            data = resp[data_start:data_start+data_len] if data_len > 0 else b""
            return cmd_echo, status, data
    
    return None, None, b""


def main():
    print("=" * 60)
    print("  Startility - D1DA Full Command Scan")
    print("=" * 60)
    print()
    
    dev = open_device()
    if not dev:
        print("[-] No Wooting keyboard found!")
        sys.exit(1)
    print("[+] Connected to keyboard\n")
    
    print("[*] Scanning all 256 D1DA commands...")
    print("    (Skipping: RESET_TO_BOOTLOADER, SOFT_RESET, RESET_FLASH)")
    print("-" * 60)
    
    responding = {}
    unknown_responding = {}
    
    for cmd in range(0x00, 0x100):
        if cmd in SKIP_CMDS:
            continue
        
        resp = send_cmd(dev, cmd)
        
        if not resp:
            # Device might have disconnected
            time.sleep(0.5)
            try:
                dev.close()
            except:
                pass
            dev = open_device()
            if not dev:
                print(f"\n[!] Lost connection at CMD 0x{cmd:02X}!")
                print("    Keyboard may have reset. Reconnect and rerun.")
                sys.exit(1)
            continue
        
        cmd_echo, status, data = parse_response(resp)
        
        if status == 0x88:  # ACK with data
            data_trimmed = data.rstrip(b"\x00")
            name = KNOWN_CMDS.get(cmd, "???UNKNOWN???")
            
            responding[cmd] = (name, data_trimmed, resp)
            
            if cmd not in KNOWN_CMDS:
                unknown_responding[cmd] = (data_trimmed, resp)
                print(f"  [NEW!] 0x{cmd:02X}: status=ACK data={data_trimmed.hex() if data_trimmed else '(empty)'}")
                print(f"         Full: {resp[:20].hex()}")
            elif cmd <= 0x04 or cmd == 0x03:
                # Print key commands
                print(f"  [OK]   0x{cmd:02X} {name}: data={data_trimmed.hex() if data_trimmed else '(empty)'}")
        elif status is not None and status != 0x88:
            # Non-standard status
            name = KNOWN_CMDS.get(cmd, "???UNKNOWN???")
            if cmd not in KNOWN_CMDS:
                print(f"  [NEW?] 0x{cmd:02X}: status=0x{status:02X} resp={resp[:16].hex()}")
    
    print()
    print("=" * 60)
    print(f"  Scan Results: {len(responding)} responding commands")
    print(f"  Unknown/New:  {len(unknown_responding)} commands")
    print("=" * 60)
    
    if unknown_responding:
        print("\n[!] UNDOCUMENTED COMMANDS FOUND:")
        for cmd in sorted(unknown_responding.keys()):
            data, resp = unknown_responding[cmd]
            print(f"  0x{cmd:02X}: data={data.hex() if data else '(empty)'}")
            print(f"        raw={resp[:24].hex()}")
        
        # Check if any look like SET_SERIAL candidates
        print("\n[*] Analyzing undocumented commands for SET_SERIAL...")
        for cmd in sorted(unknown_responding.keys()):
            data, _ = unknown_responding[cmd]
            # SET_SERIAL would likely accept data and return ACK
            # Try sending with serial-like data
            serial_data = b"\x02\x00\x16\x2F\x05\x00\x02\x00\x0F\x42\x00"
            
            # Use output report for larger payload
            payload = D1DA + bytes([cmd]) + b"\x00\x0B" + b"\x00" + serial_data
            buf = bytes([0x02]) + payload + b"\x00" * (63 - len(payload))
            try:
                dev.write(buf)
                time.sleep(0.1)
                r = dev.read(64, timeout_ms=500)
                if r:
                    r = bytes(r)
                    print(f"  CMD 0x{cmd:02X} with serial data: {r[:20].hex()}")
            except:
                pass
    else:
        print("\n[i] No undocumented commands found beyond 0x3B.")
        print("    SET_SERIAL is not available via D1DA protocol.")
        print("    -> Proceeding to Plan B: Firmware binary patch")
    
    # Print all known responding commands summary
    print(f"\n[*] All {len(responding)} responding commands:")
    for cmd in sorted(responding.keys()):
        name, data, _ = responding[cmd]
        marker = "  " if cmd in KNOWN_CMDS else ">>"
        print(f"  {marker} 0x{cmd:02X} {name}: {data.hex() if data else '(empty)'}")
    
    dev.close()


if __name__ == "__main__":
    main()
