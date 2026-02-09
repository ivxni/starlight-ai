"""
Startility - Firmware Flasher via CDP WebHID
=============================================
Flashes patched firmware through Wootility's WebHID connection.

Protocol (reverse-engineered):
  Feature Report (7 bytes): DFDB commands
  Output Report (64 bytes): Data streaming
  
  Sequence:
    1. PREPARE (CMD 0x02) - erase/prepare flash
    2. Stream firmware via output reports (64 bytes each)
    3. REBOOT (CMD 0x05)

The firmware region is 0x08007000-0x0802D83F (157,760 bytes).
The bootloader at 0x08000000-0x08006FFF is NEVER touched.
"""

import json
import sys
import os
import time
import websocket
import requests
from intelhex import IntelHex

PORT = 9222
PATCHED_FW = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'wooting_60he_arm_patched.fwr'
)


class CDP:
    def __init__(self):
        r = requests.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
        targets = r.json()
        page = next(t for t in targets if t.get('type') == 'page')
        self.ws = websocket.create_connection(
            page['webSocketDebuggerUrl'], timeout=60)
        self.mid = 0
    
    def ev(self, expr, timeout=30):
        self.mid += 1
        self.ws.send(json.dumps({
            'id': self.mid,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': expr,
                'returnByValue': True,
                'awaitPromise': True,
                'timeout': timeout * 1000,
            }
        }))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get('id') == self.mid:
                r = resp.get('result', {}).get('result', {})
                return r.get('value') if 'value' in r else r


def load_firmware(path):
    """Load firmware and convert to raw binary chunks."""
    ih = IntelHex(path)
    start = ih.minaddr()
    end = ih.maxaddr()
    binary = bytes(ih.tobinarray(start=start, size=end - start + 1))
    return binary, start, end


def main():
    print("=" * 60)
    print("  Startility - Firmware Flasher")
    print("=" * 60)
    
    if not os.path.exists(PATCHED_FW):
        print(f"[-] Patched firmware not found: {PATCHED_FW}")
        sys.exit(1)
    
    # Load firmware
    binary, fw_start, fw_end = load_firmware(PATCHED_FW)
    fw_size = len(binary)
    chunk_size = 64
    num_chunks = (fw_size + chunk_size - 1) // chunk_size
    
    print(f"[+] Firmware: {PATCHED_FW}")
    print(f"    Range: 0x{fw_start:08X} - 0x{fw_end:08X}")
    print(f"    Size: {fw_size:,} bytes")
    print(f"    Chunks: {num_chunks} x {chunk_size} bytes")
    
    # Connect CDP
    print("\n[*] Connecting to Wootility...")
    cdp = CDP()
    
    # Check current devices
    devs = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({pid: d.productId, name: d.productName, opened: d.opened}));
        })()
    """)
    print(f"    Devices: {devs}")
    
    in_bootloader = any(d.get('pid') == 0x131F for d in (devs or []))
    
    if not in_bootloader:
        # Enter bootloader mode
        print("\n[*] Entering bootloader mode...")
        cdp.ev("""
            (async () => {
                const devices = await navigator.hid.getDevices();
                const dev = devices.find(d => d.opened && d.vendorId === 0x31E3 && d.productId === 0x1312);
                if (!dev) throw new Error('No keyboard found');
                // D1DA + RESET_TO_BOOTLOADER
                await dev.sendFeatureReport(0x01, new Uint8Array([0xd1, 0xda, 0x02, 0, 0, 0, 0]));
            })()
        """)
        
        print("    Waiting for bootloader (8s)...")
        time.sleep(8)
    
    # Open bootloader device
    print("\n[*] Opening bootloader...")
    result = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return {error: 'Bootloader not found! Plug keyboard with Backspace+Fn held'};
            if (!boot.opened) await boot.open();
            return {ok: true, name: boot.productName};
        })()
    """)
    if not result or result.get('error'):
        print(f"    [-] {result}")
        sys.exit(1)
    print(f"    [+] {result}")
    
    # GET_INFO
    info = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F && d.opened);
            await boot.sendFeatureReport(0x00, new Uint8Array([0xdf, 0xdb, 0x00, 0,0,0,0]));
            return new Promise(r => {
                const h = e => { boot.removeEventListener('inputreport', h);
                    r(Array.from(new Uint8Array(e.data.buffer).slice(0,8)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); };
                boot.addEventListener('inputreport', h);
                setTimeout(() => { boot.removeEventListener('inputreport', h); r('timeout'); }, 1000);
            });
        })()
    """)
    print(f"    GET_INFO: {info}")
    
    # Upload firmware data as base64 to browser context
    import base64
    fw_b64 = base64.b64encode(binary).decode('ascii')
    
    print(f"\n[*] Uploading firmware to browser ({fw_size:,} bytes)...")
    cdp.ev(f"""
        (() => {{
            const b64 = '{fw_b64}';
            const raw = atob(b64);
            window.__fw_data = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) window.__fw_data[i] = raw.charCodeAt(i);
            return window.__fw_data.length;
        }})()
    """)
    print("    Done.")
    
    # PREPARE
    print("\n[*] PREPARE (CMD 0x02) - entering flash mode...")
    r = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            await boot.sendFeatureReport(0x00, new Uint8Array([0xdf, 0xdb, 0x02, 0,0,0,0]));
            return new Promise(r => {
                const h = e => { boot.removeEventListener('inputreport', h);
                    r(Array.from(new Uint8Array(e.data.buffer).slice(0,8)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); };
                boot.addEventListener('inputreport', h);
                setTimeout(() => { boot.removeEventListener('inputreport', h); r('timeout'); }, 1000);
            });
        })()
    """)
    print(f"    Response: {r}")
    
    time.sleep(0.5)
    
    # FLASH - stream data via output reports
    print(f"\n[*] FLASHING {num_chunks} chunks...")
    print("    ", end="", flush=True)
    
    # Send in batches to avoid overwhelming CDP
    batch_size = 100
    for batch_start in range(0, num_chunks, batch_size):
        batch_end = min(batch_start + batch_size, num_chunks)
        
        result = cdp.ev(f"""
            (async () => {{
                const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
                if (!boot) return {{error: 'device lost'}};
                
                const fw = window.__fw_data;
                const chunkSize = {chunk_size};
                let sent = 0;
                
                for (let i = {batch_start}; i < {batch_end}; i++) {{
                    const offset = i * chunkSize;
                    const chunk = new Uint8Array(chunkSize);
                    const remaining = Math.min(chunkSize, fw.length - offset);
                    for (let j = 0; j < remaining; j++) chunk[j] = fw[offset + j];
                    
                    await boot.sendReport(0x00, chunk);
                    sent++;
                    
                    // Small delay every 10 chunks to not overwhelm USB
                    if (sent % 10 === 0) await new Promise(r => setTimeout(r, 1));
                }}
                
                return {{sent: sent, range: '{batch_start}-{batch_end}'}};
            }})()
        """, timeout=30)
        
        if result and result.get('error'):
            print(f"\n    [-] Error: {result}")
            break
        
        pct = min(100, int((batch_end / num_chunks) * 100))
        print(f"\r    Progress: {batch_end}/{num_chunks} ({pct}%)", end="", flush=True)
    
    print()
    
    # Check STATUS
    time.sleep(0.5)
    status = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            if (!boot) return 'device lost';
            await boot.sendFeatureReport(0x00, new Uint8Array([0xdf, 0xdb, 0x04, 0,0,0,0]));
            return new Promise(r => {
                const h = e => { boot.removeEventListener('inputreport', h);
                    r(Array.from(new Uint8Array(e.data.buffer).slice(0,8)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); };
                boot.addEventListener('inputreport', h);
                setTimeout(() => { boot.removeEventListener('inputreport', h); r('timeout'); }, 1000);
            });
        })()
    """)
    print(f"\n[*] STATUS after flash: {status}")
    
    # REBOOT
    print("\n[*] REBOOT (CMD 0x05)...")
    try:
        cdp.ev("""
            (async () => {
                const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
                if (boot) {
                    await boot.sendFeatureReport(0x00, new Uint8Array([0xdf, 0xdb, 0x05, 0,0,0,0]));
                }
            })()
        """, timeout=5)
    except:
        pass
    
    print("    Keyboard rebooting...")
    print("\n[*] Wait 5 seconds, then check:")
    print("    1. Does keyboard work? (type something)")
    print("    2. Check serial: Get-CimInstance Win32_PnPEntity | Where { $_.Name -like '*Wooting*' }")
    print("    3. If keyboard doesn't boot -> hold Backspace+Fn and replug to enter bootloader")
    
    print(f"\n{'=' * 60}")
    print("  FLASH COMPLETE")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
