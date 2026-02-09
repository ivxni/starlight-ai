"""
Startility - Flash v2 - Try all data formats
=============================================
Tests different flash protocols to find the correct one.

Approach: Write first 1024 bytes of firmware, reboot, and check
if the keyboard still boots. If it bricks (boots to bootloader),
the data was written. If it works fine, data was ignored.

Formats to try:
  A: CMD 0x03 (set addr) + output reports (raw data)
  B: CMD 0x03 with 4-byte data chunks (feature reports only)
  C: Output reports with [addr_LE + data] per report
  D: CMD 0x03 with large feature reports (>7 bytes data)
"""

import json, sys, os, time, base64, struct
import websocket, requests
from intelhex import IntelHex

PORT = 9222
PATCHED_FW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'wooting_60he_arm_patched.fwr')


class CDP:
    def __init__(self):
        r = requests.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
        page = next(t for t in r.json() if t.get('type') == 'page')
        self.ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=60)
        self.mid = 0
    
    def ev(self, expr, timeout=30):
        self.mid += 1
        self.ws.send(json.dumps({
            'id': self.mid, 'method': 'Runtime.evaluate',
            'params': {'expression': expr, 'returnByValue': True,
                       'awaitPromise': True, 'timeout': timeout * 1000}}))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get('id') == self.mid:
                r = resp.get('result', {}).get('result', {})
                return r.get('value') if 'value' in r else r


def dfdb_resp(cdp, cmd, extra="[]", feat_size=7):
    """Send DFDB feature command and return response hex."""
    return cdp.ev(f"""
        (async () => {{
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            if (!boot) return 'NO_BOOT';
            const p = new Uint8Array({feat_size});
            p[0]=0xdf; p[1]=0xdb; p[2]={cmd};
            const ex = {extra};
            for(let i=0;i<ex.length;i++) p[3+i]=ex[i];
            await boot.sendFeatureReport(0x00, p);
            return new Promise(r => {{
                const h=e=>{{ boot.removeEventListener('inputreport',h);
                    r(Array.from(new Uint8Array(e.data.buffer).slice(0,12)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); }};
                boot.addEventListener('inputreport',h);
                setTimeout(()=>{{ boot.removeEventListener('inputreport',h); r('TIMEOUT'); }}, 1000);
            }});
        }})()
    """, timeout=10)


def main():
    print("=" * 60)
    print("  Flash v2 - Protocol Discovery")
    print("=" * 60)
    
    # Load firmware
    ih = IntelHex(PATCHED_FW)
    binary = bytes(ih.tobinarray(start=ih.minaddr(), size=ih.maxaddr()-ih.minaddr()+1))
    fw_b64 = base64.b64encode(binary).decode()
    
    cdp = CDP()
    
    # Ensure bootloader mode
    devs = cdp.ev("""(async()=>{const d=await navigator.hid.getDevices();return d.map(x=>({pid:x.productId,opened:x.opened}))})()""")
    if not any(d.get('pid') == 0x131F for d in (devs or [])):
        print("[*] Entering bootloader...")
        cdp.ev("""(async()=>{const d=(await navigator.hid.getDevices()).find(x=>x.opened&&x.productId===0x1312);if(d)await d.sendFeatureReport(0x01,new Uint8Array([0xd1,0xda,0x02,0,0,0,0]))})()""")
        time.sleep(8)
    
    # Open bootloader
    cdp.ev("""(async()=>{const d=(await navigator.hid.getDevices()).find(x=>x.productId===0x131F);if(d&&!d.opened)await d.open()})()""")
    time.sleep(0.5)
    
    info = dfdb_resp(cdp, 0x00)
    print(f"[+] GET_INFO: {info}")
    
    # Upload firmware to browser
    cdp.ev(f"""(()=>{{const r=atob('{fw_b64}');window.__fw=new Uint8Array(r.length);for(let i=0;i<r.length;i++)window.__fw[i]=r.charCodeAt(i);return window.__fw.length}})()""")
    
    # ── Test A: PREPARE + CMD 0x03 (set addr) + output reports ──
    print("\n[A] PREPARE -> CMD 0x03 (addr) -> Output Reports")
    print("-" * 50)
    
    r = dfdb_resp(cdp, 0x02)
    print(f"  PREPARE: {r}")
    time.sleep(0.3)
    
    # Set address via CMD 0x03
    r = dfdb_resp(cdp, 0x03, "[0x00, 0x70, 0x00, 0x08]")  # 0x08007000 LE
    print(f"  CMD 0x03 (addr 0x08007000): {r}")
    time.sleep(0.1)
    
    # Send 16 output reports (1024 bytes) of real firmware
    result = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            for (let i = 0; i < 16; i++) {
                const chunk = new Uint8Array(64);
                for (let j = 0; j < 64; j++) chunk[j] = window.__fw[i * 64 + j];
                await boot.sendReport(0x00, chunk);
            }
            return 'sent 16 chunks';
        })()
    """, timeout=10)
    print(f"  Output reports: {result}")
    
    r = dfdb_resp(cdp, 0x04)
    print(f"  STATUS: {r}")
    
    # ── Test B: CMD 0x03 with data in feature report ──
    print("\n[B] CMD 0x03 with firmware data in feature report")
    print("-" * 50)
    
    # Re-PREPARE
    r = dfdb_resp(cdp, 0x02)
    print(f"  PREPARE: {r}")
    time.sleep(0.3)
    
    # Send 4 bytes at a time via CMD 0x03 feature reports
    result = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            const responses = [];
            
            for (let i = 0; i < 4; i++) {
                const p = new Uint8Array(7);
                p[0] = 0xdf; p[1] = 0xdb; p[2] = 0x03;
                for (let j = 0; j < 4; j++) p[3+j] = window.__fw[i * 4 + j];
                
                await boot.sendFeatureReport(0x00, p);
                
                const resp = await new Promise(r => {
                    const h = e => { boot.removeEventListener('inputreport', h);
                        r(Array.from(new Uint8Array(e.data.buffer).slice(0,8)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); };
                    boot.addEventListener('inputreport', h);
                    setTimeout(() => { boot.removeEventListener('inputreport', h); r('TIMEOUT'); }, 500);
                });
                responses.push(resp);
            }
            return responses;
        })()
    """, timeout=15)
    print(f"  CMD 0x03 x4 responses: {result}")
    
    r = dfdb_resp(cdp, 0x04)
    print(f"  STATUS: {r}")
    
    # ── Test C: Output reports with [addr + data] format ──
    print("\n[C] Output reports with embedded address")
    print("-" * 50)
    
    r = dfdb_resp(cdp, 0x02)
    print(f"  PREPARE: {r}")
    time.sleep(0.3)
    
    result = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            
            // Format: [addr_LE_4] [data_60]
            for (let i = 0; i < 16; i++) {
                const chunk = new Uint8Array(64);
                const addr = 0x08007000 + i * 60;
                chunk[0] = addr & 0xFF;
                chunk[1] = (addr >> 8) & 0xFF;
                chunk[2] = (addr >> 16) & 0xFF;
                chunk[3] = (addr >> 24) & 0xFF;
                for (let j = 0; j < 60; j++) chunk[4+j] = window.__fw[i * 60 + j];
                await boot.sendReport(0x00, chunk);
            }
            return 'sent 16 addr+data chunks';
        })()
    """, timeout=10)
    print(f"  Output: {result}")
    
    r = dfdb_resp(cdp, 0x04)
    print(f"  STATUS: {r}")
    
    # ── Test D: Large feature reports (64 bytes) ──
    print("\n[D] Large feature reports (CMD 0x03 + 61 bytes data)")
    print("-" * 50)
    
    r = dfdb_resp(cdp, 0x02)
    print(f"  PREPARE: {r}")
    time.sleep(0.3)
    
    result = cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            const responses = [];
            
            for (let i = 0; i < 4; i++) {
                const p = new Uint8Array(64);
                p[0] = 0xdf; p[1] = 0xdb; p[2] = 0x03;
                for (let j = 0; j < 61; j++) p[3+j] = window.__fw[i * 61 + j];
                
                await boot.sendFeatureReport(0x00, p);
                
                const resp = await new Promise(r => {
                    const h = e => { boot.removeEventListener('inputreport', h);
                        r(Array.from(new Uint8Array(e.data.buffer).slice(0,8)).map(b=>b.toString(16).padStart(2,'0')).join(' ')); };
                    boot.addEventListener('inputreport', h);
                    setTimeout(() => { boot.removeEventListener('inputreport', h); r('TIMEOUT'); }, 500);
                });
                responses.push(resp);
            }
            return responses;
        })()
    """, timeout=15)
    print(f"  Responses: {result}")
    
    r = dfdb_resp(cdp, 0x04)
    print(f"  STATUS: {r}")
    
    # ── Test E: PREPARE + CMD 0x03 addr + output + CMD 0x03 commit ──
    print("\n[E] PREPARE -> CMD 0x03 addr -> output data -> CMD 0x03 commit")  
    print("-" * 50)
    
    r = dfdb_resp(cdp, 0x02)
    print(f"  PREPARE: {r}")
    time.sleep(0.3)
    
    # Set address
    r = dfdb_resp(cdp, 0x03, "[0x00, 0x70, 0x00, 0x08]")
    print(f"  CMD 0x03 set addr: {r}")
    
    # Data
    cdp.ev("""
        (async () => {
            const boot = (await navigator.hid.getDevices()).find(d => d.productId === 0x131F && d.opened);
            for (let i = 0; i < 16; i++) {
                const c = new Uint8Array(64);
                for (let j = 0; j < 64; j++) c[j] = window.__fw[i*64+j];
                await boot.sendReport(0x00, c);
            }
        })()
    """, timeout=10)
    print(f"  Sent 16 output reports")
    
    # Commit with CMD 0x03 (no extra data = commit?)
    r = dfdb_resp(cdp, 0x03)
    print(f"  CMD 0x03 commit: {r}")
    
    r = dfdb_resp(cdp, 0x04)
    print(f"  STATUS: {r}")
    
    # ── REBOOT ──
    print("\n[*] Rebooting...")
    try:
        dfdb_resp(cdp, 0x05)
    except:
        pass
    
    print("    Check keyboard and serial after 5 seconds.")
    print("    If keyboard works + old serial -> flash didn't write")
    print("    If keyboard bricks -> data WAS written (wrong format)")


if __name__ == "__main__":
    main()
