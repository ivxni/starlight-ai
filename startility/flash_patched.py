"""
Startility - Complete Flash Tool
=================================
1. Patches firmware with custom serial
2. Replaces firmware in Wootility app.asar
3. User flashes via Wootility's built-in updater

Usage:
  python flash_patched.py NEW_SERIAL
  python flash_patched.py A01C2450W003J54321

The serial should be alphanumeric, max 37 chars.
For realistic look, use format: A##B####W###X#####
"""

import sys
import os
import json
import shutil
import subprocess
import tempfile
from intelhex import IntelHex

# Paths
WOOTILITY_RESOURCES = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    'Programs', 'wootility', 'resources'
)
ASAR_PATH = os.path.join(WOOTILITY_RESOURCES, 'app.asar')
ASAR_BACKUP = os.path.join(WOOTILITY_RESOURCES, 'app.asar.bak')

FW_NAME = 'wooting_60_he_arm'
FW_REL_PATH = f'dist/fw/{FW_NAME}.fwr'
FW_JSON_REL_PATH = f'dist/fw/{FW_NAME}.json'

# Patch constants
SERIAL_FMT_ADDR = 0x0802C538
SERIAL_FMT_ORIG = b"A%02uB%02u%02uW%02u%s%01u%s%s%c%05lu\x00"
SERIAL_FMT_SIZE = len(SERIAL_FMT_ORIG)  # 38 bytes


def patch_firmware(fw_path, new_serial, output_path):
    """Patch firmware with new serial string."""
    ih = IntelHex(fw_path)
    base = ih.minaddr()
    binary = bytes(ih.tobinarray(start=base, size=ih.maxaddr() - base + 1))
    
    # Verify format string exists
    fmt_offset = SERIAL_FMT_ADDR - base
    actual = binary[fmt_offset:fmt_offset + SERIAL_FMT_SIZE]
    if actual != SERIAL_FMT_ORIG:
        print(f"[-] Format string mismatch at 0x{SERIAL_FMT_ADDR:08X}!")
        print(f"    Expected: {SERIAL_FMT_ORIG.hex()}")
        print(f"    Actual:   {actual.hex()}")
        return False
    
    # Create patch: literal serial + null padding
    new_bytes = new_serial.encode('ascii') + b'\x00'
    new_bytes += b'\x00' * (SERIAL_FMT_SIZE - len(new_bytes))
    
    # Apply patch
    for i, b in enumerate(new_bytes):
        ih[SERIAL_FMT_ADDR + i] = b
    
    ih.write_hex_file(output_path)
    
    # Verify
    ih2 = IntelHex(output_path)
    readback = bytes([ih2[SERIAL_FMT_ADDR + i] for i in range(len(new_serial) + 1)])
    expected = new_serial.encode('ascii') + b'\x00'
    if readback != expected:
        print(f"[-] Verification failed!")
        return False
    
    return True


def modify_wootility(new_serial, patched_fw_path):
    """Replace firmware in Wootility asar archive."""
    
    if not os.path.exists(ASAR_PATH):
        print(f"[-] Wootility not found: {ASAR_PATH}")
        return False
    
    # Create temp extraction directory
    extract_dir = os.path.join(tempfile.gettempdir(), 'wootility-patch')
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    # Backup original asar
    if not os.path.exists(ASAR_BACKUP):
        print(f"[*] Backing up: {ASAR_PATH}")
        print(f"    To: {ASAR_BACKUP}")
        shutil.copy2(ASAR_PATH, ASAR_BACKUP)
        print(f"    Backup created.")
    else:
        print(f"[*] Backup already exists: {ASAR_BACKUP}")
    
    # Extract asar
    print(f"\n[*] Extracting app.asar...")
    result = subprocess.run(
        f'asar extract "{ASAR_PATH}" "{extract_dir}"',
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print(f"[-] Extract failed: {result.stderr}")
        return False
    print(f"    Extracted to: {extract_dir}")
    
    # Replace firmware file
    fw_dest = os.path.join(extract_dir, FW_REL_PATH.replace('/', os.sep))
    if not os.path.exists(fw_dest):
        print(f"[-] Original firmware not found in asar: {fw_dest}")
        return False
    
    print(f"\n[*] Replacing firmware...")
    print(f"    Original: {fw_dest}")
    print(f"    Patched:  {patched_fw_path}")
    
    orig_size = os.path.getsize(fw_dest)
    shutil.copy2(patched_fw_path, fw_dest)
    new_size = os.path.getsize(fw_dest)
    print(f"    Size: {orig_size:,} -> {new_size:,} bytes")
    
    # Bump firmware version in metadata to trigger update
    json_path = os.path.join(extract_dir, FW_JSON_REL_PATH.replace('/', os.sep))
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            meta = json.load(f)
        
        old_ver = meta.get('version', '?')
        # Bump patch version
        parts = old_ver.split('.')
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            new_ver = '.'.join(parts)
        else:
            new_ver = old_ver + '.1'
        
        meta['version'] = new_ver
        meta['title'] = f'Serial Update ({new_serial[:8]}...)'
        meta['description'] = f'Custom firmware with serial: {new_serial}'
        
        with open(json_path, 'w') as f:
            json.dump(meta, f)
        
        print(f"\n[*] Updated metadata:")
        print(f"    Version: {old_ver} -> {new_ver}")
        print(f"    Title:   {meta['title']}")
    
    # Repack asar
    print(f"\n[*] Repacking app.asar...")
    result = subprocess.run(
        f'asar pack "{extract_dir}" "{ASAR_PATH}"',
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print(f"[-] Repack failed: {result.stderr}")
        # Restore backup
        shutil.copy2(ASAR_BACKUP, ASAR_PATH)
        print(f"[!] Restored backup.")
        return False
    
    new_asar_size = os.path.getsize(ASAR_PATH)
    print(f"    Repacked: {new_asar_size:,} bytes")
    
    # Cleanup
    shutil.rmtree(extract_dir, ignore_errors=True)
    
    return True


def restore_wootility():
    """Restore original Wootility asar from backup."""
    if os.path.exists(ASAR_BACKUP):
        shutil.copy2(ASAR_BACKUP, ASAR_PATH)
        print(f"[+] Restored original app.asar from backup")
        return True
    else:
        print(f"[-] No backup found at {ASAR_BACKUP}")
        return False


def main():
    print("=" * 60)
    print("  Startility - Flash Tool v1.0")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print(f"\n  Usage:")
        print(f"    python {sys.argv[0]} NEW_SERIAL")
        print(f"    python {sys.argv[0]} A01C2450W003J54321")
        print(f"    python {sys.argv[0]} --restore  (restore original Wootility)")
        print(f"\n  The serial should be alphanumeric, max 37 chars.")
        sys.exit(1)
    
    if sys.argv[1] == '--restore':
        restore_wootility()
        sys.exit(0)
    
    new_serial = sys.argv[1]
    
    # Validate serial
    if not all(c.isalnum() for c in new_serial):
        print(f"\n[-] Serial must be alphanumeric: '{new_serial}'")
        sys.exit(1)
    
    if len(new_serial) > 37:
        print(f"\n[-] Serial too long ({len(new_serial)} chars, max 37)")
        sys.exit(1)
    
    if len(new_serial) < 5:
        print(f"\n[-] Serial too short ({len(new_serial)} chars, min 5)")
        sys.exit(1)
    
    print(f"\n[+] New serial: {new_serial}")
    
    # Step 1: Find original firmware
    extract_dir = os.path.join(tempfile.gettempdir(), 'wootility-src')
    orig_fw = os.path.join(extract_dir, FW_REL_PATH.replace('/', os.sep))
    
    if not os.path.exists(orig_fw):
        print(f"\n[*] Extracting firmware from Wootility...")
        if os.path.exists(ASAR_BACKUP):
            src = ASAR_BACKUP  # Use backup if available
        else:
            src = ASAR_PATH
        
        result = subprocess.run(
            f'asar extract "{src}" "{extract_dir}"',
            capture_output=True, text=True, shell=True
        )
        if result.returncode != 0:
            print(f"[-] Failed to extract: {result.stderr}")
            sys.exit(1)
    
    print(f"[+] Original firmware: {orig_fw}")
    
    # Step 2: Patch firmware
    patched_fw = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'wooting_60he_arm_patched.fwr'
    )
    
    print(f"\n[*] Patching firmware...")
    if not patch_firmware(orig_fw, new_serial, patched_fw):
        print(f"[-] Patching failed!")
        sys.exit(1)
    print(f"[+] Patched: {patched_fw}")
    
    # Step 3: Replace in Wootility
    print(f"\n[*] Modifying Wootility...")
    if not modify_wootility(new_serial, patched_fw):
        print(f"[-] Wootility modification failed!")
        sys.exit(1)
    
    # Done
    print(f"\n{'=' * 60}")
    print(f"  READY TO FLASH")
    print(f"{'=' * 60}")
    print(f"  Serial: {new_serial}")
    print(f"  ")
    print(f"  Steps:")
    print(f"  1. Close Wootility if running")
    print(f"  2. Open Wootility")
    print(f"  3. Connect keyboard")
    print(f"  4. Go to firmware update")
    print(f"  5. It should show version bump -> flash it")
    print(f"  6. After flash, check USB serial in Device Manager")
    print(f"  ")
    print(f"  To restore original Wootility:")
    print(f"    python {sys.argv[0]} --restore")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
