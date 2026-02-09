"""
Startility - CDP WebHID Firmware Flasher
=========================================
Flashes patched firmware via Chrome DevTools Protocol -> WebHID.

1. Sends RESET_TO_BOOTLOADER via opened D1DA device
2. Waits for bootloader device (PID 0x131F)  
3. Probes DFDB flash data format
4. Streams firmware data
5. Reboots keyboard

Requirements: Wootility running with --remote-debugging-port=9222
"""

import json
import sys
import os
import time
import struct
import websocket
import requests
from intelhex import IntelHex

PORT = 9222
WOOTING_VID = 0x31E3
NORMAL_PID = 0x1312
BOOT_PID = 0x131F

PATCHED_FW = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'wooting_60he_arm_patched.fwr'
)


class CDPSession:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.msg_id = 0
    
    def evaluate(self, expr, timeout=15):
        self.msg_id += 1
        self.ws.send(json.dumps({
            'id': self.msg_id,
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
            if resp.get('id') == self.msg_id:
                result = resp.get('result', {}).get('result', {})
                if result.get('type') == 'undefined':
                    return None
                if 'value' in result:
                    return result['value']
                if result.get('subtype') == 'error':
                    desc = result.get('description', 'unknown error')
                    raise Exception(f"JS error: {desc}")
                return result
    
    def close(self):
        self.ws.close()


def connect_cdp():
    """Connect to Wootility's renderer via CDP."""
    r = requests.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
    targets = r.json()
    
    for t in targets:
        if t.get('type') == 'page':
            ws_url = t['webSocketDebuggerUrl']
            print(f"[+] Connected: {t.get('title')}")
            return CDPSession(ws_url)
    
    raise Exception("No page target found")


def enter_bootloader(cdp):
    """Send RESET_TO_BOOTLOADER via D1DA on the opened device."""
    print("\n[*] Sending RESET_TO_BOOTLOADER (D1DA 0x02)...")
    
    result = cdp.evaluate("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            // Find the opened control device
            const dev = devices.find(d => d.opened && d.vendorId === 0x31E3);
            if (!dev) return {error: 'no opened device'};
            
            try {
                // D1DA + RESET_TO_BOOTLOADER (0x02) via Feature Report ID 0
                const cmd = new Uint8Array([0xd1, 0xda, 0x02, 0, 0, 0, 0]);
                await dev.sendFeatureReport(0x00, cmd);
                return {ok: true, sent: 'D1DA 02 via feature report 0'};
            } catch(e) {
                // Try with report ID 1
                try {
                    const cmd = new Uint8Array([0xd1, 0xda, 0x02, 0, 0, 0, 0]);
                    await dev.sendFeatureReport(0x01, cmd);
                    return {ok: true, sent: 'D1DA 02 via feature report 1'};
                } catch(e2) {
                    return {error: e.message + ' / ' + e2.message};
                }
            }
        })()
    """)
    print(f"    Result: {result}")
    return result and result.get('ok')


def wait_for_bootloader(cdp, timeout=10):
    """Wait for bootloader device (PID 0x131F) to appear."""
    print(f"\n[*] Waiting for bootloader device (PID 0x131F, {timeout}s)...")
    
    for i in range(timeout * 2):
        time.sleep(0.5)
        
        devs = cdp.evaluate("""
            (async () => {
                const devices = await navigator.hid.getDevices();
                return devices.map(d => ({
                    vid: d.vendorId,
                    pid: d.productId,
                    name: d.productName, 
                    opened: d.opened,
                    collections: d.collections.length
                }));
            })()
        """)
        
        if devs:
            boot_devs = [d for d in devs if d.get('pid') == BOOT_PID]
            if boot_devs:
                print(f"    [+] Bootloader found: {boot_devs[0]}")
                return True
    
    print("    [-] Bootloader not found")
    return False


def open_bootloader(cdp):
    """Open the bootloader HID device."""
    print("\n[*] Opening bootloader device...")
    
    result = cdp.evaluate("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return {error: 'bootloader not found'};
            
            if (!boot.opened) {
                await boot.open();
            }
            
            return {
                opened: boot.opened,
                name: boot.productName,
                collections: boot.collections.map(c => ({
                    usagePage: c.usagePage,
                    usage: c.usage,
                    inputReports: c.inputReports.map(r => ({id: r.reportId, items: r.items?.length})),
                    outputReports: c.outputReports.map(r => ({id: r.reportId, items: r.items?.length})),
                    featureReports: c.featureReports.map(r => ({id: r.reportId, items: r.items?.length})),
                }))
            };
        })()
    """)
    print(f"    Result: {json.dumps(result, indent=2)}")
    return result and result.get('opened')


def dfdb_command(cdp, cmd, extra_hex=""):
    """Send DFDB command via feature report and read response."""
    result = cdp.evaluate(f"""
        (async () => {{
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F && d.opened);
            if (!boot) return {{error: 'no opened bootloader'}};
            
            const extra = Uint8Array.from('{extra_hex}'.match(/.{{1,2}}/g)?.map(b => parseInt(b, 16)) || []);
            const payload = new Uint8Array(7);
            payload[0] = 0xdf;
            payload[1] = 0xdb;
            payload[2] = {cmd};
            for (let i = 0; i < extra.length && i < 4; i++) payload[3+i] = extra[i];
            
            await boot.sendFeatureReport(0x00, payload);
            
            // Read response via input report event
            return new Promise((resolve) => {{
                const handler = (e) => {{
                    boot.removeEventListener('inputreport', handler);
                    const data = new Uint8Array(e.data.buffer);
                    resolve({{
                        reportId: e.reportId,
                        data: Array.from(data).map(b => b.toString(16).padStart(2,'0')).join('')
                    }});
                }};
                boot.addEventListener('inputreport', handler);
                setTimeout(() => {{
                    boot.removeEventListener('inputreport', handler);
                    resolve({{timeout: true}});
                }}, 1000);
            }});
        }})()
    """, timeout=15)
    return result


def probe_flash_protocol(cdp):
    """Test flash write data formats after PREPARE."""
    print("\n[*] Probing flash write protocol...")
    
    # First, get bootloader info
    print("  CMD 0x00 (GET_INFO):")
    r = dfdb_command(cdp, 0x00)
    print(f"    {r}")
    
    print("  CMD 0x01 (GET_PROTOCOL):")
    r = dfdb_command(cdp, 0x01) 
    print(f"    {r}")
    
    print("  CMD 0x04 (STATUS):")
    r = dfdb_command(cdp, 0x04)
    print(f"    {r}")
    
    # PREPARE - enter flash mode
    print("\n  CMD 0x02 (PREPARE - entering flash mode):")
    r = dfdb_command(cdp, 0x02)
    print(f"    {r}")
    
    # Check status after prepare
    print("  CMD 0x04 (STATUS after PREPARE):")
    r = dfdb_command(cdp, 0x04)
    print(f"    {r}")
    
    # Try sending data via output report with various formats
    print("\n  Testing data write formats...")
    
    # Format A: DFDB + CMD 0x03 + address + data via output report
    test_formats = [
        ("DFDB+03+addr+data (output)", """
            const payload = new Uint8Array(64);
            payload[0] = 0xdf; payload[1] = 0xdb; payload[2] = 0x03;
            // address 0x08007000 LE
            payload[3] = 0x00; payload[4] = 0x70; payload[5] = 0x00; payload[6] = 0x08;
            // first 57 bytes of dummy data
            for (let i = 7; i < 64; i++) payload[i] = 0xAA;
            await boot.sendReport(0x00, payload);
        """),
        ("Raw addr+data (output RID=0)", """
            const payload = new Uint8Array(64);
            // address 0x08007000 LE
            payload[0] = 0x00; payload[1] = 0x70; payload[2] = 0x00; payload[3] = 0x08;
            // data
            for (let i = 4; i < 64; i++) payload[i] = 0xBB;
            await boot.sendReport(0x00, payload);
        """),
        ("DFDB+03+data (feature)", """
            const payload = new Uint8Array(7);
            payload[0] = 0xdf; payload[1] = 0xdb; payload[2] = 0x03;
            payload[3] = 0x00; payload[4] = 0x70; payload[5] = 0x00; payload[6] = 0x08;
            await boot.sendFeatureReport(0x00, payload);
        """),
    ]
    
    for name, code in test_formats:
        result = cdp.evaluate(f"""
            (async () => {{
                const devices = await navigator.hid.getDevices();
                const boot = devices.find(d => d.productId === 0x131F && d.opened);
                if (!boot) return {{error: 'no boot device'}};
                
                try {{
                    {code}
                    
                    // Read response
                    return new Promise((resolve) => {{
                        const handler = (e) => {{
                            boot.removeEventListener('inputreport', handler);
                            const data = new Uint8Array(e.data.buffer);
                            resolve({{
                                ok: true,
                                format: '{name}',
                                reportId: e.reportId,
                                resp: Array.from(data.slice(0,16)).map(b => b.toString(16).padStart(2,'0')).join('')
                            }});
                        }};
                        boot.addEventListener('inputreport', handler);
                        setTimeout(() => {{
                            boot.removeEventListener('inputreport', handler);
                            resolve({{format: '{name}', timeout: true}});
                        }}, 500);
                    }});
                }} catch(e) {{
                    return {{format: '{name}', error: e.message}};
                }}
            }})()
        """, timeout=10)
        print(f"    {name}: {result}")
    
    # Check status after writes
    print("\n  CMD 0x04 (STATUS after writes):")
    r = dfdb_command(cdp, 0x04)
    print(f"    {r}")
    
    return True


def main():
    print("=" * 60)
    print("  Startility - CDP WebHID Flash Protocol Probe")
    print("=" * 60)
    
    if not os.path.exists(PATCHED_FW):
        print(f"[-] Patched firmware not found: {PATCHED_FW}")
        sys.exit(1)
    
    try:
        cdp = connect_cdp()
    except Exception as e:
        print(f"[-] Cannot connect to CDP: {e}")
        print("    Launch Wootility with: --remote-debugging-port=9222 --remote-allow-origins=*")
        sys.exit(1)
    
    # Step 1: Enter bootloader
    if not enter_bootloader(cdp):
        print("[-] Failed to enter bootloader!")
        sys.exit(1)
    
    time.sleep(3)  # Wait for mode switch
    
    # Step 2: Wait for bootloader device
    if not wait_for_bootloader(cdp, timeout=15):
        print("[-] Bootloader device not found!")
        print("    Try manually: hold Backspace + Fn")
        sys.exit(1)
    
    # Step 3: Open bootloader
    if not open_bootloader(cdp):
        print("[-] Failed to open bootloader device!")
        sys.exit(1)
    
    # Step 4: Probe flash protocol
    probe_flash_protocol(cdp)
    
    print(f"\n{'=' * 60}")
    print("  Probe complete - check responses above")
    print(f"{'=' * 60}")
    
    cdp.close()


if __name__ == "__main__":
    main()
