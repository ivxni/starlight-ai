"""
Startility - Wooting 60HE (ARM) HID Communication Tool
=======================================================
Uses the D1DA protocol to communicate with Wooting keyboards.
Based on reverse-engineered protocol from libwootility.

Supports:
  - Reading serial number
  - Reading firmware version
  - Reading device config
  - Entering bootloader mode
  - Exploring bootloader protocol for flash read/write
"""

import hid
import struct
import time
import sys

# ── Wooting USB IDs ──────────────────────────────────────────────
WOOTING_VID        = 0x31E3
WOOTING_60HE_PID   = 0x1312   # Normal mode
WOOTING_BOOT_PID   = 0x131F   # Bootloader mode

# ── D1DA Protocol ────────────────────────────────────────────────
D1DA = b"\xd1\xda"

# Feature report commands (sent via D1DA prefix)
CMD_PING                    = 0x00
CMD_GET_VERSION             = 0x01
CMD_RESET_TO_BOOTLOADER     = 0x02
CMD_GET_SERIAL              = 0x03
CMD_GET_RGB_PROFILE_COUNT   = 0x04
CMD_RELOAD_PROFILE0         = 0x07
CMD_SAVE_RGB_PROFILE        = 0x08
CMD_GET_DEVICE_CONFIG       = 0x13
CMD_DO_SOFT_RESET           = 0x19
CMD_RESET_FLASH             = 0x2B
CMD_GET_GLOBAL_SETTINGS     = 0x33
CMD_IS_FLASH_CHIP_CONNECTED = 0x38
CMD_GET_FLASH_STATS         = 0x3A
CMD_GET_RGB_BINS            = 0x3B

# Commands that return a response
HAS_RESPONSE = [
    CMD_PING, CMD_GET_VERSION, CMD_GET_SERIAL,
    CMD_SAVE_RGB_PROFILE, CMD_GET_DEVICE_CONFIG,
    CMD_DO_SOFT_RESET, CMD_IS_FLASH_CHIP_CONNECTED,
    CMD_GET_FLASH_STATS, CMD_GET_RGB_BINS,
]

# ── HID Interface Matching ───────────────────────────────────────
# The Wooting 60HE ARM exposes 5 USB interfaces (MI_00..MI_04)
# The control interface uses usage_page=0xFF55 (vendor-specific)
# which supports the D1DA feature report protocol.
CONTROL_USAGE_PAGE = 0xFF55


def find_wooting_devices():
    """List all Wooting HID devices."""
    devices = hid.enumerate(WOOTING_VID, 0)
    return devices


def find_control_interface(pid=WOOTING_60HE_PID):
    """Find the vendor-specific control HID interface for D1DA protocol."""
    devices = hid.enumerate(WOOTING_VID, pid)
    
    # Try usage_page match first
    for dev in devices:
        if dev.get('usage_page') == CONTROL_USAGE_PAGE:
            return dev
    
    # Fallback: try interface 0 (MI_00) which is typically vendor-defined
    for dev in devices:
        if dev.get('interface_number') == 0:
            return dev
    
    # Last resort: first device
    if devices:
        return devices[0]
    
    return None


def find_bootloader_interface():
    """Find the bootloader HID interface (PID 131F)."""
    devices = hid.enumerate(WOOTING_VID, WOOTING_BOOT_PID)
    if devices:
        return devices[0]
    return None


class WootingDevice:
    """Communicates with a Wooting keyboard via D1DA HID protocol."""
    
    def __init__(self, device_info=None):
        self.dev = hid.device()
        self.device_info = device_info
        self._opened = False
    
    def open(self, device_info=None):
        """Open the HID device."""
        info = device_info or self.device_info
        if info is None:
            info = find_control_interface()
        if info is None:
            raise RuntimeError("No Wooting keyboard found!")
        
        self.device_info = info
        self.dev.open_path(info['path'])
        self.dev.set_nonblocking(0)  # blocking reads
        self._opened = True
        print(f"[+] Connected to: {info.get('product_string', 'Unknown')}")
        print(f"    Path: {info['path']}")
        print(f"    Serial: {info.get('serial_number', 'N/A')}")
        print(f"    Interface: {info.get('interface_number', '?')}")
        print(f"    Usage Page: 0x{info.get('usage_page', 0):04X}")
    
    def close(self):
        """Close the HID device."""
        if self._opened:
            self.dev.close()
            self._opened = False
    
    def send_feature(self, cmd_byte, extra_data=b""):
        """Send a D1DA feature report command and read response.
        
        The Wooting control interface (Usage Page 0xFF55) uses:
          Report ID 1: Feature report (7 bytes data), Input/Output (32 bytes)
          Report IDs 2-6: Input/Output only (62, 254, 510, 1022, 2046 bytes)
        
        Protocol: Send D1DA+cmd as feature report ID 1, response comes as input report.
        """
        payload = D1DA + bytes([cmd_byte]) + extra_data
        
        # Try multiple approaches to find what works on Windows
        response = None
        
        # Approach 1: Feature report with Report ID 1 (7 bytes data)
        report = bytes([0x01]) + payload
        report = report + b"\x00" * max(0, 8 - len(report))  # pad to 1+7=8 bytes
        try:
            self.dev.send_feature_report(report)
            response = self.dev.read(33, timeout_ms=1000)
            if response:
                return bytes(response)
        except Exception as e:
            print(f"    [attempt 1 - feature report ID 1] {e}")
        
        # Approach 2: Output report with Report ID 2 (for larger payloads)
        report2 = bytes([0x02]) + payload
        report2 = report2 + b"\x00" * max(0, 63 - len(report2))
        try:
            self.dev.write(report2)
            response = self.dev.read(64, timeout_ms=1000)
            if response:
                return bytes(response)
        except Exception as e:
            print(f"    [attempt 2 - output report ID 2] {e}")
        
        # Approach 3: Feature report with Report ID 0 (Linux-style)
        report0 = bytes([0x00]) + payload
        report0 = report0 + b"\x00" * max(0, 8 - len(report0))
        try:
            self.dev.send_feature_report(report0)
            response = self.dev.read(33, timeout_ms=1000)
            if response:
                return bytes(response)
        except Exception as e:
            print(f"    [attempt 3 - feature report ID 0] {e}")
        
        # Approach 4: Output report with Report ID 1
        report1out = bytes([0x01]) + payload
        report1out = report1out + b"\x00" * max(0, 33 - len(report1out))
        try:
            self.dev.write(report1out)
            response = self.dev.read(33, timeout_ms=1000)
            if response:
                return bytes(response)
        except Exception as e:
            print(f"    [attempt 4 - output report ID 1] {e}")
        
        return None
    
    def send_output_report(self, report_id, payload):
        """Send an output report (used for larger data transfers)."""
        report = bytes([report_id]) + payload
        try:
            self.dev.write(report)
        except Exception as e:
            print(f"[-] write failed: {e}")
            return False
        return True
    
    def read_response(self, size=64, timeout_ms=2000):
        """Read a response from the device."""
        try:
            data = self.dev.read(size, timeout_ms=timeout_ms)
            return bytes(data) if data else None
        except Exception as e:
            print(f"[-] read failed: {e}")
            return None
    
    # ── Protocol Commands ────────────────────────────────────────
    
    def ping(self):
        """Send a ping command."""
        print("[*] Sending PING...")
        resp = self.send_feature(CMD_PING)
        if resp:
            print(f"[+] PING response: {resp.hex()}")
        return resp
    
    def get_version(self):
        """Get firmware version."""
        print("[*] Getting firmware version...")
        resp = self.send_feature(CMD_GET_VERSION)
        if resp:
            print(f"[+] Version response ({len(resp)} bytes): {resp.hex()}")
            # Try to decode as text
            try:
                text = resp.rstrip(b'\x00').decode('utf-8', errors='replace')
                print(f"    Text: {text}")
            except:
                pass
        return resp
    
    def get_serial(self):
        """Get the serial number from the keyboard."""
        print("[*] Getting serial number...")
        resp = self.send_feature(CMD_GET_SERIAL)
        if resp:
            print(f"[+] Serial response ({len(resp)} bytes): {resp.hex()}")
            # Try to decode as text
            try:
                text = resp.rstrip(b'\x00').decode('utf-8', errors='replace')
                print(f"    Text: {text}")
            except:
                pass
            # Try to find ASCII serial string in response
            ascii_chars = []
            for b in resp:
                if 0x20 <= b < 0x7F:
                    ascii_chars.append(chr(b))
                elif ascii_chars:
                    break
            if ascii_chars:
                serial_str = ''.join(ascii_chars)
                print(f"    Extracted serial: {serial_str}")
        return resp
    
    def get_device_config(self):
        """Get device configuration."""
        print("[*] Getting device config...")
        resp = self.send_feature(CMD_GET_DEVICE_CONFIG)
        if resp:
            print(f"[+] Config response ({len(resp)} bytes): {resp.hex()}")
        return resp
    
    def get_flash_stats(self):
        """Get flash statistics."""
        print("[*] Getting flash stats...")
        resp = self.send_feature(CMD_GET_FLASH_STATS)
        if resp:
            print(f"[+] Flash stats ({len(resp)} bytes): {resp.hex()}")
        return resp
    
    def is_flash_connected(self):
        """Check if external flash chip is connected."""
        print("[*] Checking flash chip...")
        resp = self.send_feature(CMD_IS_FLASH_CHIP_CONNECTED)
        if resp:
            print(f"[+] Flash connected response: {resp.hex()}")
        return resp
    
    def get_global_settings(self):
        """Get global settings."""
        print("[*] Getting global settings...")
        resp = self.send_feature(CMD_GET_GLOBAL_SETTINGS)
        if resp:
            print(f"[+] Global settings ({len(resp)} bytes): {resp.hex()}")
        return resp
    
    def reset_to_bootloader(self):
        """Enter bootloader mode. WARNING: keyboard will disconnect!"""
        print("[!] Sending RESET_TO_BOOTLOADER...")
        print("    The keyboard will disconnect and re-enumerate as PID 131F.")
        self.send_feature(CMD_RESET_TO_BOOTLOADER)
        print("[+] Command sent. Keyboard entering bootloader mode.")
    
    def soft_reset(self):
        """Soft reset the keyboard."""
        print("[*] Sending soft reset...")
        resp = self.send_feature(CMD_DO_SOFT_RESET)
        if resp:
            print(f"[+] Soft reset response: {resp.hex()}")
        return resp
    
    def reset_flash(self):
        """Reset all flash data. WARNING: This erases all config!"""
        print("[!] Sending RESET_FLASH...")
        self.send_feature(CMD_RESET_FLASH)
        print("[+] Flash reset command sent.")
    
    def get_rgb_bins(self):
        """Get RGB bin data (hardware calibration)."""
        print("[*] Getting RGB bins...")
        resp = self.send_feature(CMD_GET_RGB_BINS)
        if resp:
            print(f"[+] RGB bins ({len(resp)} bytes): {resp.hex()}")
        return resp


class WootingBootloader:
    """Communicates with the Wooting bootloader (PID 131F)."""
    
    def __init__(self):
        self.dev = hid.device()
        self._opened = False
    
    def open(self, device_info=None):
        """Open the bootloader HID device."""
        info = device_info or find_bootloader_interface()
        if info is None:
            raise RuntimeError("No Wooting bootloader found! Is the keyboard in bootloader mode?")
        
        self.dev.open_path(info['path'])
        self.dev.set_nonblocking(0)
        self._opened = True
        print(f"[+] Connected to bootloader")
        print(f"    Path: {info['path']}")
        print(f"    Serial: {info.get('serial_number', 'N/A')}")
    
    def close(self):
        if self._opened:
            self.dev.close()
            self._opened = False
    
    def probe_reports(self):
        """Probe the bootloader by sending various report IDs to discover protocol."""
        print("[*] Probing bootloader protocol...")
        
        # Try sending feature reports with different report IDs
        for report_id in range(0, 16):
            try:
                # Try to get a feature report
                data = bytes([report_id]) + b"\x00" * 63
                result = self.dev.get_feature_report(report_id, 65)
                if result:
                    print(f"    Report ID {report_id}: {bytes(result[:32]).hex()}...")
            except Exception as e:
                pass
        
        # Try sending/reading output reports
        for report_id in [0, 1, 2]:
            try:
                probe = bytes([report_id]) + b"\x00" * 63
                self.dev.write(probe)
                resp = self.dev.read(64, timeout_ms=500)
                if resp:
                    print(f"    Output Report {report_id} response: {bytes(resp[:32]).hex()}...")
            except Exception as e:
                pass
    
    def send_raw(self, data, read_size=64, timeout_ms=1000):
        """Send raw data and read response."""
        try:
            self.dev.write(data)
            resp = self.dev.read(read_size, timeout_ms=timeout_ms)
            return bytes(resp) if resp else None
        except Exception as e:
            print(f"[-] Error: {e}")
            return None


# ── Main CLI ─────────────────────────────────────────────────────

def print_all_devices():
    """Print all Wooting HID devices found."""
    devices = find_wooting_devices()
    if not devices:
        print("[-] No Wooting devices found!")
        return
    
    print(f"[+] Found {len(devices)} Wooting HID interface(s):\n")
    for i, dev in enumerate(devices):
        pid = dev.get('product_id', 0)
        mode = "BOOTLOADER" if pid == WOOTING_BOOT_PID else "NORMAL"
        print(f"  [{i}] {mode} - PID: 0x{pid:04X}")
        print(f"      Product:   {dev.get('product_string', 'N/A')}")
        print(f"      Serial:    {dev.get('serial_number', 'N/A')}")
        print(f"      Interface: MI_{dev.get('interface_number', '?'):02d}")
        print(f"      Usage:     Page=0x{dev.get('usage_page', 0):04X} "
              f"Usage=0x{dev.get('usage', 0):04X}")
        print(f"      Path:      {dev['path']}")
        print()


def main():
    print("=" * 60)
    print("  Startility - Wooting 60HE Serial Tool")
    print("=" * 60)
    print()
    
    # List all devices
    print_all_devices()
    
    # Try to connect to control interface
    ctrl = find_control_interface()
    if ctrl is None:
        # Check for bootloader
        boot = find_bootloader_interface()
        if boot:
            print("[!] Keyboard is in BOOTLOADER mode (PID 131F)")
            print("    Use bootloader commands or reconnect in normal mode.")
        else:
            print("[-] No Wooting keyboard found. Is it plugged in?")
        return
    
    print("-" * 60)
    dev = WootingDevice(ctrl)
    try:
        dev.open()
        print()
        
        # Run diagnostics
        dev.ping()
        print()
        dev.get_version()
        print()
        dev.get_serial()
        print()
        dev.get_device_config()
        print()
        dev.is_flash_connected()
        print()
        dev.get_flash_stats()
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        dev.close()


if __name__ == "__main__":
    main()
