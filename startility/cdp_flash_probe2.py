"""
Startility - Flash Protocol Deep Probe v2
==========================================
Now that we know feature reports work, probe the exact flash data format.
Tests larger feature reports, CMD 0x03 sequences, and output report after CMD 0x03.
"""

import json
import sys
import os
import time
import websocket
import requests

PORT = 9222


class CDP:
    def __init__(self):
        r = requests.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
        targets = r.json()
        page = next(t for t in targets if t.get('type') == 'page')
        self.ws = websocket.create_connection(
            page['webSocketDebuggerUrl'], timeout=30)
        self.mid = 0
        print(f"[+] Connected: {page.get('title')}")
    
    def ev(self, expr, timeout=15):
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
                if 'value' in r:
                    return r['value']
                return r
    
    def close(self):
        self.ws.close()


def main():
    print("=" * 60)
    print("  Flash Protocol Deep Probe v2")
    print("=" * 60)
    
    cdp = CDP()
    
    # Check if we're in bootloader mode already
    devs = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({
                pid: d.productId, name: d.productName, opened: d.opened
            }));
        })()
    """)
    print(f"\n[*] Devices: {devs}")
    
    boot_found = any(d.get('pid') == 0x131F for d in devs)
    
    if not boot_found:
        print("\n[!] Not in bootloader mode. Sending RESET_TO_BOOTLOADER...")
        cdp.ev("""
            (async () => {
                const devices = await navigator.hid.getDevices();
                const dev = devices.find(d => d.opened && d.vendorId === 0x31E3);
                if (dev) {
                    const cmd = new Uint8Array([0xd1, 0xda, 0x02, 0, 0, 0, 0]);
                    await dev.sendFeatureReport(0x01, cmd);
                }
            })()
        """)
        print("    Waiting 5s...")
        time.sleep(5)
    
    # Open bootloader
    print("\n[*] Opening bootloader...")
    result = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return {error: 'no bootloader'};
            if (!boot.opened) await boot.open();
            
            // Get report sizes from descriptor
            const col = boot.collections[0];
            return {
                opened: boot.opened,
                featureReportId: col.featureReports[0]?.reportId,
                outputReportId: col.outputReports[0]?.reportId,
                inputReportId: col.inputReports[0]?.reportId,
                // Report items details
                featureItems: col.featureReports[0]?.items?.map(i => ({
                    usageMin: i.usageMinimum, usageMax: i.usageMaximum,
                    reportSize: i.reportSize, reportCount: i.reportCount,
                    logMin: i.logicalMinimum, logMax: i.logicalMaximum
                })),
                outputItems: col.outputReports[0]?.items?.map(i => ({
                    usageMin: i.usageMinimum, usageMax: i.usageMaximum,
                    reportSize: i.reportSize, reportCount: i.reportCount,
                    logMin: i.logicalMinimum, logMax: i.logicalMaximum
                })),
                inputItems: col.inputReports[0]?.items?.map(i => ({
                    usageMin: i.usageMinimum, usageMax: i.usageMaximum,
                    reportSize: i.reportSize, reportCount: i.reportCount,
                    logMin: i.logicalMinimum, logMax: i.logicalMaximum
                })),
            };
        })()
    """)
    print(f"  {json.dumps(result, indent=2)}")
    
    # Helper: send DFDB feature command and read response
    def dfdb_cmd(cmd, extra_bytes="[]", size=7):
        r = cdp.ev(f"""
            (async () => {{
                const devices = await navigator.hid.getDevices();
                const boot = devices.find(d => d.productId === 0x131F && d.opened);
                if (!boot) return {{error: 'no boot'}};
                
                const extra = {extra_bytes};
                const payload = new Uint8Array({size});
                payload[0] = 0xdf; payload[1] = 0xdb; payload[2] = {cmd};
                for (let i = 0; i < extra.length; i++) payload[3+i] = extra[i];
                
                await boot.sendFeatureReport(0x00, payload);
                
                return new Promise((resolve) => {{
                    const h = (e) => {{
                        boot.removeEventListener('inputreport', h);
                        const d = new Uint8Array(e.data.buffer);
                        resolve(Array.from(d.slice(0,16)).map(b => b.toString(16).padStart(2,'0')).join(''));
                    }};
                    boot.addEventListener('inputreport', h);
                    setTimeout(() => {{ boot.removeEventListener('inputreport', h); resolve('TIMEOUT'); }}, 800);
                }});
            }})()
        """, timeout=10)
        return r
    
    def send_output(data_js, size=64):
        """Send output report and check for response."""
        r = cdp.ev(f"""
            (async () => {{
                const devices = await navigator.hid.getDevices();
                const boot = devices.find(d => d.productId === 0x131F && d.opened);
                if (!boot) return {{error: 'no boot'}};
                
                const payload = new Uint8Array({size});
                const data = {data_js};
                for (let i = 0; i < data.length && i < {size}; i++) payload[i] = data[i];
                
                try {{
                    await boot.sendReport(0x00, payload);
                }} catch(e) {{
                    return {{sendError: e.message}};
                }}
                
                return new Promise((resolve) => {{
                    const h = (e) => {{
                        boot.removeEventListener('inputreport', h);
                        const d = new Uint8Array(e.data.buffer);
                        resolve({{resp: Array.from(d.slice(0,16)).map(b => b.toString(16).padStart(2,'0')).join('')}});
                    }};
                    boot.addEventListener('inputreport', h);
                    setTimeout(() => {{ boot.removeEventListener('inputreport', h); resolve({{noResp: true}}); }}, 500);
                }});
            }})()
        """, timeout=10)
        return r

    # ── Phase 1: Report size test ──────────────────────────
    print("\n[*] Phase 1: Feature report size test")
    print("-" * 50)
    
    for size in [7, 8, 32, 63, 64, 128, 256]:
        r = cdp.ev(f"""
            (async () => {{
                const devices = await navigator.hid.getDevices();
                const boot = devices.find(d => d.productId === 0x131F && d.opened);
                if (!boot) return 'no boot';
                
                const payload = new Uint8Array({size});
                payload[0] = 0xdf; payload[1] = 0xdb; payload[2] = 0x00; // GET_INFO
                
                try {{
                    await boot.sendFeatureReport(0x00, payload);
                    return new Promise((resolve) => {{
                        const h = (e) => {{
                            boot.removeEventListener('inputreport', h);
                            const d = new Uint8Array(e.data.buffer);
                            resolve('OK resp=' + Array.from(d.slice(0,8)).map(b => b.toString(16).padStart(2,'0')).join(''));
                        }};
                        boot.addEventListener('inputreport', h);
                        setTimeout(() => {{ boot.removeEventListener('inputreport', h); resolve('timeout'); }}, 500);
                    }});
                }} catch(e) {{
                    return 'ERR: ' + e.message;
                }}
            }})()
        """, timeout=10)
        print(f"  Size {size:4d}: {r}")
    
    # ── Phase 2: PREPARE + data via feature report ─────────
    print("\n[*] Phase 2: PREPARE + data write via large feature report")
    print("-" * 50)
    
    print("  Sending PREPARE (0x02)...")
    r = dfdb_cmd(0x02)
    print(f"    PREPARE: {r}")
    
    # Try CMD 0x03 with address in larger feature report
    # Address 0x08007000 = first firmware byte
    for size in [7, 32, 64]:
        extra = "[0x00, 0x70, 0x00, 0x08]"  # 0x08007000 LE
        r2 = cdp.ev(f"""
            (async () => {{
                const devices = await navigator.hid.getDevices();
                const boot = devices.find(d => d.productId === 0x131F && d.opened);
                if (!boot) return 'no boot';
                
                const payload = new Uint8Array({size});
                payload[0] = 0xdf; payload[1] = 0xdb; payload[2] = 0x03;
                // Address LE: 0x08007000
                payload[3] = 0x00; payload[4] = 0x70; payload[5] = 0x00; payload[6] = 0x08;
                // Fill rest with test data
                for (let i = 7; i < {size}; i++) payload[i] = i & 0xFF;
                
                try {{
                    await boot.sendFeatureReport(0x00, payload);
                    return new Promise((resolve) => {{
                        const h = (e) => {{
                            boot.removeEventListener('inputreport', h);
                            const d = new Uint8Array(e.data.buffer);
                            resolve('OK resp=' + Array.from(d.slice(0,8)).map(b => b.toString(16).padStart(2,'0')).join(''));
                        }};
                        boot.addEventListener('inputreport', h);
                        setTimeout(() => {{ boot.removeEventListener('inputreport', h); resolve('timeout'); }}, 500);
                    }});
                }} catch(e) {{
                    return 'ERR: ' + e.message;
                }}
            }})()
        """, timeout=10)
        print(f"  CMD 0x03 size={size}: {r2}")
    
    # Check status
    r = dfdb_cmd(0x04)
    print(f"  STATUS: {r}")
    
    # ── Phase 3: Output report after CMD 0x03 ─────────────
    print("\n[*] Phase 3: Output report data after CMD 0x03 feature report")
    print("-" * 50)
    
    # First send CMD 0x03 via feature to set up write
    dfdb_cmd(0x03, "[0x00, 0x70, 0x00, 0x08]")
    time.sleep(0.1)
    
    # Then try output reports
    for size in [32, 64]:
        r = send_output("[0x00, 0x70, 0x00, 0x08, 0xAA, 0xBB, 0xCC, 0xDD]", size)
        print(f"  Output size={size} after CMD 0x03: {r}")
    
    # Check status
    r = dfdb_cmd(0x04)
    print(f"  STATUS: {r}")
    
    # ── Phase 4: Try receiveFeatureReport ──────────────────
    print("\n[*] Phase 4: receiveFeatureReport test")
    print("-" * 50)
    
    r = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F && d.opened);
            if (!boot) return 'no boot';
            
            // Send GET_INFO first
            const cmd = new Uint8Array([0xdf, 0xdb, 0x00, 0, 0, 0, 0]);
            await boot.sendFeatureReport(0x00, cmd);
            
            try {
                const report = await boot.receiveFeatureReport(0x00);
                const data = new Uint8Array(report.data.buffer);
                return 'Feature response: ' + Array.from(data.slice(0,16)).map(b => b.toString(16).padStart(2,'0')).join('');
            } catch(e) {
                return 'ERR: ' + e.message;
            }
        })()
    """)
    print(f"  receiveFeatureReport: {r}")
    
    # ── Phase 5: Reboot ───────────────────────────────────
    print("\n[*] Sending REBOOT (0x05)...")
    try:
        dfdb_cmd(0x05)
    except:
        pass
    print("    Keyboard should reboot now.")
    
    cdp.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
