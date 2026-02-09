"""
Startility - Wooting 60HE Serial Spoofer
=========================================
All-in-one tool to change the USB serial number of a Wooting 60HE (ARM).

Usage:
  python spoof.py                  Generate random serial & prepare flash
  python spoof.py A03B2519W041H28437   Use specific serial & prepare flash
  python spoof.py --check          Just show current serial

Process:
  1. Generate or use provided serial number
  2. Patch original firmware with new serial
  3. Swap firmware into Wootility's app.asar
  4. User runs Wootility > Help > Troubleshoot (with internet off)
  5. Restore original app.asar after flash
"""

import os
import sys
import random
import string
import struct
import subprocess
import shutil
import time

try:
    from intelhex import IntelHex
except ImportError:
    print("[-] Missing dependency: intelhex")
    print("    Run: pip install intelhex")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────
WOOTILITY_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "wootility")
ASAR_PATH = os.path.join(WOOTILITY_DIR, "resources", "app.asar")
ASAR_BAK  = ASAR_PATH + ".bak"

EXTRACT_DIR = os.path.join(os.environ.get("TEMP", "."), "wootility-src")
FW_REL_PATH = os.path.join("dist", "fw", "wooting_60_he_arm.fwr")
FW_ORIG     = os.path.join(EXTRACT_DIR, FW_REL_PATH)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Firmware constants ──────────────────────────────────────────
SERIAL_FMT_ADDR = 0x0802C538
SERIAL_FMT_ORIG = b"A%02uB%02u%02uW%02u%s%01u%s%s%c%05lu\x00"
SERIAL_FMT_SIZE = len(SERIAL_FMT_ORIG)  # 38 bytes


def generate_serial():
    """Generate a random but realistic Wooting serial number.
    Format: A{supplier:02d}B{year:02d}{week:02d}W{rev:03d}H{num:05d}
    Example: A03B2519W041H28437
    """
    supplier = random.randint(1, 9)
    year     = random.randint(20, 26)
    week     = random.randint(1, 52)
    rev      = random.randint(1, 99)
    prod_num = random.randint(10000, 99999)
    serial   = f"A{supplier:02d}B{year:02d}{week:02d}W{rev:03d}H{prod_num:05d}"
    return serial


def check_current_serial():
    """Read and display the current USB serial from the keyboard."""
    try:
        import hid
    except ImportError:
        print("[-] Missing dependency: hid")
        print("    Run: pip install hidapi")
        return None

    devs = hid.enumerate(0x31E3, 0x1312)
    if not devs:
        print("[-] No Wooting 60HE found. Is the keyboard plugged in?")
        return None

    serial = devs[0].get("serial_number", "")
    print(f"    Current serial: {serial}")
    return serial


def ensure_extracted():
    """Make sure we have the extracted Wootility source with original firmware."""
    if os.path.exists(FW_ORIG):
        # Verify it's the original (has format string, not a hardcoded serial)
        ih = IntelHex(FW_ORIG)
        check = bytes([ih[SERIAL_FMT_ADDR + i] for i in range(10)])
        if check.startswith(b"A%02uB"):
            return True
        else:
            print("[!] Extracted firmware is already patched. Re-extracting...")

    if not os.path.exists(ASAR_BAK):
        if not os.path.exists(ASAR_PATH):
            print("[-] Wootility not found!")
            print(f"    Expected at: {ASAR_PATH}")
            return False
        # Create backup of original asar
        print("[*] Creating backup of original app.asar...")
        shutil.copy2(ASAR_PATH, ASAR_BAK)

    print("[*] Extracting Wootility app.asar...")
    result = subprocess.run(
        ["npx", "asar", "extract", ASAR_BAK, EXTRACT_DIR],
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print(f"[-] Extraction failed: {result.stderr}")
        return False

    if not os.path.exists(FW_ORIG):
        print(f"[-] Firmware not found after extraction: {FW_ORIG}")
        return False

    return True


def patch_firmware(new_serial):
    """Patch the firmware with the new serial string."""
    print(f"[*] Loading original firmware...")
    ih = IntelHex(FW_ORIG)

    # Verify original format string is present
    orig_bytes = bytes([ih[SERIAL_FMT_ADDR + i] for i in range(SERIAL_FMT_SIZE)])
    if not orig_bytes.startswith(b"A%02uB"):
        # Maybe it was patched before - re-extract
        print("[!] Firmware format string not found - re-extracting from backup...")
        if os.path.exists(ASAR_BAK):
            subprocess.run(
                ["npx", "asar", "extract", ASAR_BAK, EXTRACT_DIR],
                capture_output=True, text=True, shell=True
            )
            ih = IntelHex(FW_ORIG)
            orig_bytes = bytes([ih[SERIAL_FMT_ADDR + i] for i in range(SERIAL_FMT_SIZE)])

    if not orig_bytes.startswith(b"A%02uB"):
        print("[-] Cannot find original format string in firmware!")
        print(f"    At 0x{SERIAL_FMT_ADDR:08X}: {orig_bytes[:20].hex()}")
        return None

    # Create patched serial bytes (null-terminated, padded to original size)
    serial_bytes = new_serial.encode("ascii") + b"\x00"
    serial_bytes += b"\x00" * (SERIAL_FMT_SIZE - len(serial_bytes))

    # Write patch
    for i, b in enumerate(serial_bytes):
        ih[SERIAL_FMT_ADDR + i] = b

    # Save patched firmware over the extracted one
    ih.write_hex_file(FW_ORIG)

    # Verify
    ih2 = IntelHex(FW_ORIG)
    readback = bytes([ih2[SERIAL_FMT_ADDR + i] for i in range(len(new_serial))])
    if readback == new_serial.encode("ascii"):
        print(f"    Patch verified OK")
        return True
    else:
        print(f"[-] Patch verification failed!")
        return None


def install_to_wootility():
    """Pack the patched firmware back into Wootility's app.asar."""
    print("[*] Repacking app.asar with patched firmware...")

    # Make sure we have a backup
    if not os.path.exists(ASAR_BAK):
        if os.path.exists(ASAR_PATH):
            shutil.copy2(ASAR_PATH, ASAR_BAK)

    result = subprocess.run(
        ["npx", "asar", "pack", EXTRACT_DIR, ASAR_PATH],
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print(f"[-] Repacking failed: {result.stderr}")
        return False

    print(f"    app.asar updated")
    return True


def restore_wootility():
    """Restore original app.asar from backup."""
    if os.path.exists(ASAR_BAK):
        shutil.copy2(ASAR_BAK, ASAR_PATH)
        print("[+] Original app.asar restored")
        return True
    else:
        print("[-] No backup found to restore!")
        return False


def wait_for_flash():
    """Wait for the user to complete the Wootility flash process."""
    print()
    print("=" * 60)
    print("  READY TO FLASH")
    print("=" * 60)
    print()
    print("  1. DISCONNECT FROM INTERNET (WiFi off / cable out)")
    print("  2. Open Wootility")
    print("  3. Go to: Help > Troubleshoot")
    print("  4. Click the restore/reset option")
    print("  5. Wait for 'Update Complete'")
    print("  6. Come back here and press ENTER")
    print()

    # Auto-launch Wootility
    wootility_exe = os.path.join(WOOTILITY_DIR, "Wootility.exe")
    if os.path.exists(wootility_exe):
        launch = input("Launch Wootility now? [Y/n]: ").strip().lower()
        if launch != "n":
            subprocess.Popen([wootility_exe], shell=True)
            print("    Wootility launched. Follow the steps above.")

    print()
    input(">>> Press ENTER after flash is complete... ")


def main():
    print()
    print("=" * 60)
    print("   Startility - Wooting 60HE Serial Spoofer")
    print("=" * 60)
    print()

    # ── Check-only mode ────────────────────────────────────────
    if "--check" in sys.argv:
        check_current_serial()
        return

    # ── Restore mode ───────────────────────────────────────────
    if "--restore" in sys.argv:
        restore_wootility()
        return

    # ── Show current serial ────────────────────────────────────
    print("[1/6] Current keyboard state")
    old_serial = check_current_serial()

    # ── Determine new serial ───────────────────────────────────
    print()
    print("[2/6] Generating new serial")

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        new_serial = sys.argv[1]
        print(f"    Using provided: {new_serial}")
    else:
        new_serial = generate_serial()
        print(f"    Generated:      {new_serial}")

    # Validate
    if len(new_serial) > 37:
        print(f"[-] Serial too long ({len(new_serial)} chars, max 37)")
        sys.exit(1)
    if not all(c.isalnum() for c in new_serial):
        print(f"[-] Serial must be alphanumeric")
        sys.exit(1)

    if old_serial == new_serial:
        print("[!] New serial is same as current - generating another one")
        new_serial = generate_serial()
        print(f"    Generated:      {new_serial}")

    # ── Extract & verify firmware ──────────────────────────────
    print()
    print("[3/6] Preparing firmware")
    if not ensure_extracted():
        sys.exit(1)

    # ── Patch firmware ─────────────────────────────────────────
    print()
    print("[4/6] Patching firmware")
    print(f"    Serial: {old_serial or '?'} -> {new_serial}")
    if not patch_firmware(new_serial):
        sys.exit(1)

    # ── Install into Wootility ─────────────────────────────────
    print()
    print("[5/6] Installing into Wootility")
    if not install_to_wootility():
        sys.exit(1)

    # ── Flash via Wootility ────────────────────────────────────
    print()
    print("[6/6] Flashing")
    wait_for_flash()

    # ── Restore & verify ───────────────────────────────────────
    print()
    print("[*] Closing Wootility and restoring original app.asar...")
    time.sleep(2)

    # Try to close Wootility
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "Wootility.exe"],
            capture_output=True, shell=True
        )
        time.sleep(2)
    except:
        pass

    restore_wootility()

    # Re-extract clean firmware for next run
    print("[*] Re-extracting clean firmware for next spoof...")
    subprocess.run(
        ["npx", "asar", "extract", ASAR_BAK, EXTRACT_DIR],
        capture_output=True, text=True, shell=True
    )

    # Verify new serial
    print()
    print("[*] Verifying new serial...")
    time.sleep(2)
    new_actual = check_current_serial()

    print()
    print("=" * 60)
    if new_actual == new_serial:
        print(f"  SUCCESS!")
    elif new_actual and new_actual != old_serial:
        print(f"  SERIAL CHANGED (different from expected)")
    else:
        print(f"  SERIAL MAY NOT HAVE CHANGED")
        print(f"  Try unplugging and replugging the keyboard")
    print()
    print(f"  Before: {old_serial or '?'}")
    print(f"  Target: {new_serial}")
    print(f"  After:  {new_actual or '?'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
