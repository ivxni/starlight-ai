"""
Startility - Definitive Firmware Flasher
==========================================
Protocol reverse-engineered from Wootility source:

1. CMD 6 + 0xFFAAFFBB  (ERASE flash with magic key)
2. CMD 2 + num_chunks   (PREPARE with chunk count)
3. For each 256-byte chunk:
   a. Send 256 bytes via 4x64B output reports (RID 0)
   b. CMD 3 + chunk_index (CONFIRM chunk written)
4. CRC verify (optional)
5. CMD 5 (REBOOT)

Feature reports: RID=0, [DF DB CMD param_LE32]
Output reports:  RID=0, [64 bytes raw firmware data]
"""

import hid
import time
import sys
import os
import struct
from intelhex import IntelHex

WOOTING_VID = 0x31E3
BOOT_PID = 0x131F
NORMAL_PID = 0x1312
DFDB = b"\xdf\xdb"
ERASE_KEY = 0xFFAAFFBB
CHUNK_SIZE = 256
OUTPUT_SIZE = 64

PATCHED_FW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'wooting_60he_arm_patched.fwr')


def open_bootloader():
    for d in hid.enumerate(WOOTING_VID, BOOT_PID):
        dev = hid.device()
        dev.open_path(d['path'])
        dev.set_nonblocking(0)
        return dev
    return None


def send_dfdb_cmd(dev, cmd, param=None):
    """Send DFDB command via feature report, return response."""
    payload = DFDB + bytes([cmd])
    if param is not None:
        payload += struct.pack("<I", param & 0xFFFFFFFF)
    else:
        payload += b"\x00" * 4
    report = bytes([0x00]) + payload
    report += b"\x00" * max(0, 8 - len(report))
    dev.send_feature_report(report)
    time.sleep(0.03)
    resp = dev.read(64, timeout_ms=1000)
    return bytes(resp) if resp else None


def send_output(dev, data_64):
    """Send 64 bytes via output report with RID 0."""
    report = bytes([0x00]) + data_64
    if len(report) < 65:
        report += b"\x00" * (65 - len(report))
    dev.write(report)


def main():
    print("=" * 60)
    print("  Startility - Definitive Flasher")
    print("  Protocol: ERASE -> PREPARE -> DATA+CONFIRM -> REBOOT")
    print("=" * 60)

    if not os.path.exists(PATCHED_FW):
        print(f"[-] Patched firmware not found: {PATCHED_FW}")
        sys.exit(1)

    ih = IntelHex(PATCHED_FW)
    binary = bytes(ih.tobinarray(start=ih.minaddr(),
                                  size=ih.maxaddr() - ih.minaddr() + 1))
    print(f"\n[+] Firmware: {len(binary):,} bytes")
    print(f"    Range: 0x{ih.minaddr():08X} - 0x{ih.maxaddr():08X}")

    if len(binary) % CHUNK_SIZE != 0:
        pad = CHUNK_SIZE - (len(binary) % CHUNK_SIZE)
        binary += b"\xff" * pad
        print(f"    Padded: {len(binary):,} bytes (+{pad})")

    num_chunks = len(binary) // CHUNK_SIZE
    print(f"    Chunks: {num_chunks} x {CHUNK_SIZE}B")

    print("\n[*] Connecting to bootloader...")
    dev = open_bootloader()
    if not dev:
        print("[-] No bootloader found!")
        sys.exit(1)

    resp = send_dfdb_cmd(dev, 0x00)
    if resp:
        print(f"[+] Connected: {resp[:8].hex()}")

    # Step 1: ERASE
    print(f"\n[*] Step 1: ERASE (CMD 6 + 0x{ERASE_KEY:08X})")
    resp = send_dfdb_cmd(dev, 0x06, ERASE_KEY)
    print(f"    Response: {resp[:8].hex() if resp else 'none'}")
    time.sleep(0.5)

    # Step 2: PREPARE
    print(f"\n[*] Step 2: PREPARE (CMD 2 + {num_chunks} chunks)")
    resp = send_dfdb_cmd(dev, 0x02, num_chunks)
    print(f"    Response: {resp[:8].hex() if resp else 'none'}")
    time.sleep(0.3)

    # Step 3: Flash
    print(f"\n[*] Step 3: Flashing {num_chunks} chunks...")
    t_start = time.time()

    for i in range(num_chunks):
        chunk = binary[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        for j in range(CHUNK_SIZE // OUTPUT_SIZE):
            sub = chunk[j * OUTPUT_SIZE: (j + 1) * OUTPUT_SIZE]
            send_output(dev, sub)

        send_dfdb_cmd(dev, 0x03, i)

        if (i + 1) % 50 == 0 or i == num_chunks - 1:
            elapsed = time.time() - t_start
            pct = (i + 1) / num_chunks * 100
            rate = (i + 1) * CHUNK_SIZE / elapsed / 1024 if elapsed > 0 else 0
            eta = (num_chunks - i - 1) / ((i + 1) / elapsed) if elapsed > 0 else 0
            print(f"\r    {i+1}/{num_chunks} ({pct:.0f}%) "
                  f"[{elapsed:.1f}s, {rate:.1f} KB/s, ETA {eta:.0f}s]",
                  end="", flush=True)

    elapsed = time.time() - t_start
    print(f"\n    Done: {len(binary):,} bytes in {elapsed:.1f}s")

    # Step 4: Status
    print("\n[*] Step 4: Status check")
    resp = send_dfdb_cmd(dev, 0x04)
    print(f"    STATUS: {resp[:8].hex() if resp else 'none'}")

    # Step 5: Reboot
    print("\n[*] Step 5: Rebooting...")
    try:
        dev.send_feature_report(b"\x00" + DFDB + b"\x05\x00\x00\x00\x00")
    except:
        pass
    try:
        dev.close()
    except:
        pass

    print("\n[+] Flash complete! Checking serial in 8 seconds...")
    time.sleep(8)

    for d in hid.enumerate(WOOTING_VID, NORMAL_PID):
        if d['serial_number']:
            print(f"\n    *** SERIAL: {d['serial_number']} ***")
            break
    else:
        print("    Keyboard not found yet - check manually:")
        print('    Get-PnpDevice | Where { $_.InstanceId -like "*31E3*1312*" }')


if __name__ == "__main__":
    main()
