"""
Startility - Wooting Serial Reset Tool
=======================================
Attempts to reset the external SPI flash via RESET_FLASH (0x2B).
This may erase the serial number along with other stored data.

RECOVERY: If anything goes wrong, Wootility can reflash the firmware
and the keyboard should recover (serial may be empty/default).

Flow:
  1. Read current serial (GET_SERIAL)
  2. Check flash status (IS_FLASH_CONNECTED, GET_FLASH_STATS)
  3. Send RESET_FLASH
  4. Wait and reconnect
  5. Read serial again to see if it changed
"""

import hid
import time
import sys

WOOTING_VID      = 0x31E3
WOOTING_60HE_PID = 0x1312
D1DA = b"\xd1\xda"

CMD_GET_SERIAL              = 0x03
CMD_GET_DEVICE_CONFIG       = 0x13
CMD_DO_SOFT_RESET           = 0x19
CMD_RESET_FLASH             = 0x2B
CMD_IS_FLASH_CHIP_CONNECTED = 0x38
CMD_GET_FLASH_STATS         = 0x3A


def find_control():
    """Find the control interface (Usage Page 0xFF55)."""
    devices = hid.enumerate(WOOTING_VID, WOOTING_60HE_PID)
    for dev in devices:
        if dev.get('usage_page') == 0xFF55:
            return dev
    return None


def open_device():
    """Open the Wooting control interface."""
    info = find_control()
    if not info:
        return None, None
    dev = hid.device()
    dev.open_path(info['path'])
    dev.set_nonblocking(0)
    return dev, info


def send_cmd(dev, cmd_byte):
    """Send D1DA command via feature report RID=1, return response."""
    payload = D1DA + bytes([cmd_byte])
    report = bytes([0x01]) + payload + b"\x00" * (8 - 1 - len(payload))
    
    try:
        dev.send_feature_report(report)
        time.sleep(0.1)
        resp = dev.read(64, timeout_ms=2000)
        return bytes(resp) if resp else None
    except Exception as e:
        return None


def parse_serial_response(resp):
    """Parse GET_SERIAL response and extract serial fields."""
    if not resp or len(resp) < 10:
        return None
    
    # Response: [RID] [D1DA] [CMD] [88] [len] [00] [payload]
    idx = 0
    for i in range(len(resp) - 1):
        if resp[i] == 0xd1 and resp[i+1] == 0xda:
            idx = i
            break
    
    # Skip D1DA(2) + CMD(1) + header(1) + len(1) + pad(1)
    payload_start = idx + 6
    if payload_start >= len(resp):
        return None
    
    payload_len = resp[idx + 4]
    payload = resp[payload_start:payload_start + payload_len]
    return payload


def decode_serial_string(payload):
    """Try to reconstruct the serial string from binary payload."""
    if not payload or len(payload) < 11:
        return f"(raw: {payload.hex() if payload else 'empty'})"
    
    # Known layout from analysis:
    # [0-1] SupplierNumber u16LE
    # [2]   Year u8
    # [3]   WeekNumber u8
    # [4-5] RevisionNumber u16LE
    # [6-7] ProductId u16LE
    # [8-9] ProductNumber u16LE
    # [10]  Stage u8
    import struct
    
    try:
        supplier = struct.unpack_from("<H", payload, 0)[0]
        year = payload[2]
        week = payload[3]
        rev = struct.unpack_from("<H", payload, 4)[0]
        prod_id = struct.unpack_from("<H", payload, 6)[0]
        prod_num = struct.unpack_from("<H", payload, 8)[0]
        stage = payload[10] if len(payload) > 10 else 0
        
        # Reconstruct serial string
        stage_letter = chr(ord('A') + stage) if stage < 26 else '?'
        prod_id_letter = chr(ord('A') + prod_id) if prod_id < 26 else '?'
        
        serial = (f"{stage_letter}{supplier:02d}{prod_id_letter}"
                  f"{year:02d}{week:02d}"
                  f"W{rev:03d}"
                  f"H{prod_num}")
        
        return serial
    except:
        return f"(raw: {payload.hex()})"


def main():
    print("=" * 60)
    print("  Startility - Serial Reset Tool")
    print("=" * 60)
    print()
    
    # ── Step 1: Connect and read current state ───────────────
    print("[*] Step 1: Connecting to keyboard...")
    dev, info = open_device()
    if not dev:
        print("[-] No Wooting keyboard found in normal mode!")
        print("    Make sure the keyboard is plugged in and NOT in bootloader mode.")
        sys.exit(1)
    
    usb_serial = info.get('serial_number', 'N/A')
    print(f"[+] Connected: {info.get('product_string')}")
    print(f"    USB Serial: {usb_serial}")
    
    # ── Step 2: Read current serial via D1DA ─────────────────
    print("\n[*] Step 2: Reading serial via D1DA protocol...")
    resp = send_cmd(dev, CMD_GET_SERIAL)
    if resp:
        payload = parse_serial_response(resp)
        if payload:
            decoded = decode_serial_string(payload)
            print(f"    Raw payload: {payload.hex()}")
            print(f"    Decoded:     {decoded}")
        else:
            print(f"    Response: {resp[:20].hex()}")
    
    # ── Step 3: Check flash status ───────────────────────────
    print("\n[*] Step 3: Checking flash status...")
    resp_flash = send_cmd(dev, CMD_IS_FLASH_CHIP_CONNECTED)
    if resp_flash:
        print(f"    Flash connected: {resp_flash[:12].hex()}")
    
    resp_stats = send_cmd(dev, CMD_GET_FLASH_STATS)
    if resp_stats:
        print(f"    Flash stats:     {resp_stats[:12].hex()}")
    
    # ── Step 4: Confirm with user ────────────────────────────
    print()
    print("=" * 60)
    print("  WARNING: RESET_FLASH will erase stored data!")
    print("  This includes: profiles, settings, possibly serial")
    print("  Recovery: Wootility can reflash firmware if needed")
    print("=" * 60)
    print()
    
    confirm = input("Type 'RESET' to proceed with flash reset: ").strip()
    if confirm != "RESET":
        print("[*] Cancelled.")
        dev.close()
        return
    
    # ── Step 5: Send RESET_FLASH ─────────────────────────────
    print("\n[!] Sending RESET_FLASH (0x2B)...")
    resp_reset = send_cmd(dev, CMD_RESET_FLASH)
    if resp_reset:
        print(f"    Response: {resp_reset[:16].hex()}")
    else:
        print("    No response (keyboard may have reset)")
    
    # ── Step 6: Send soft reset ──────────────────────────────
    print("\n[*] Sending soft reset...")
    try:
        send_cmd(dev, CMD_DO_SOFT_RESET)
    except:
        pass
    
    try:
        dev.close()
    except:
        pass
    
    # ── Step 7: Wait and reconnect ───────────────────────────
    print("\n[*] Waiting 5 seconds for keyboard to restart...")
    time.sleep(5)
    
    print("[*] Reconnecting...")
    dev2, info2 = open_device()
    if not dev2:
        print("[-] Keyboard not found after reset!")
        print("    Try unplugging and replugging.")
        print("    If keyboard doesn't work, use Wootility to reflash firmware.")
        return
    
    new_usb_serial = info2.get('serial_number', 'N/A')
    print(f"[+] Reconnected!")
    print(f"    USB Serial: {new_usb_serial}")
    
    # ── Step 8: Read serial again ────────────────────────────
    print("\n[*] Reading serial after reset...")
    resp2 = send_cmd(dev2, CMD_GET_SERIAL)
    if resp2:
        payload2 = parse_serial_response(resp2)
        if payload2:
            decoded2 = decode_serial_string(payload2)
            print(f"    Raw payload: {payload2.hex()}")
            print(f"    Decoded:     {decoded2}")
        else:
            print(f"    Response: {resp2[:20].hex()}")
    
    # ── Summary ──────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  RESULT")
    print("=" * 60)
    print(f"  Before: {usb_serial}")
    print(f"  After:  {new_usb_serial}")
    
    if usb_serial != new_usb_serial:
        print("  >> SERIAL CHANGED! <<")
    else:
        print("  >> Serial unchanged - need Plan B (firmware patch)")
    
    dev2.close()


if __name__ == "__main__":
    main()
