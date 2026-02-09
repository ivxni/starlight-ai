"""
Flash firmware via WebHID through Wootility's CDP.
This uses the browser's WebHID API instead of Python hidapi,
which may handle output reports differently on Windows.
"""
import json
import time
import urllib.request
import websocket
import base64
import os

FIRMWARE_PATH = r"C:\Users\angel\AppData\Local\Temp\wootility-src\dist\fw\wooting_60_he_arm.fwr"

def get_ws_url():
    data = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
    targets = json.loads(data)
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    return None

msg_counter = 0

def cdp_eval(ws, expr, timeout=15):
    global msg_counter
    msg_counter += 1
    msg_id = msg_counter
    ws.send(json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "awaitPromise": True,
            "returnByValue": True,
            "timeout": timeout * 1000
        }
    }))
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id:
                result = resp.get("result", {}).get("result", {})
                exc = resp.get("result", {}).get("exceptionDetails")
                if exc:
                    return f"EXCEPTION: {exc.get('text', '')} - {result.get('description', '')}"
                return result.get("value", result.get("description", str(result)))
        except websocket.WebSocketTimeoutException:
            continue
    return "TIMEOUT"

def main():
    # Load firmware
    if not os.path.exists(FIRMWARE_PATH):
        print(f"[-] Firmware not found: {FIRMWARE_PATH}")
        # Try to find any .fwr file
        fwr_dir = r"C:\Users\angel\Desktop\starlight-ai\startility"
        for f in os.listdir(fwr_dir):
            if f.endswith('.fwr'):
                print(f"    Found: {f}")
        return
    
    # Parse Intel HEX
    print(f"[*] Loading firmware: {FIRMWARE_PATH}")
    binary = parse_intel_hex(FIRMWARE_PATH)
    print(f"    Binary size: {len(binary)} bytes ({len(binary)//256} chunks of 256)")
    
    # Base64 encode for transport to browser
    fw_b64 = base64.b64encode(binary).decode()
    
    print("[*] Connecting to Wootility CDP...")
    time.sleep(1)
    
    ws_url = get_ws_url()
    if not ws_url:
        print("[-] No Wootility page found!")
        return
    
    ws = websocket.create_connection(ws_url, timeout=10)
    print("[+] Connected")

    # Step 1: Open bootloader device
    print("\n[1] Opening bootloader device...")
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return 'No bootloader device';
            if (!boot.opened) await boot.open();
            window._bootDev = boot;
            return 'Opened: ' + boot.productName;
        })()
    """)
    print(f"    {result}")
    if 'No bootloader' in str(result):
        ws.close()
        return

    # Step 2: Verify GET_INFO works
    print("\n[2] Testing GET_INFO command...")
    result = cdp_eval(ws, """
        (async () => {
            const dev = window._bootDev;
            const cmd = new Uint8Array(64);
            cmd[0] = 0xDF; cmd[1] = 0xDB; cmd[2] = 0x00;
            
            const respPromise = new Promise((resolve, reject) => {
                const t = setTimeout(() => reject('timeout'), 2000);
                dev.addEventListener('inputreport', (e) => {
                    clearTimeout(t);
                    resolve(new Uint8Array(e.data.buffer));
                }, {once: true});
            });
            
            await dev.sendFeatureReport(0, cmd);
            const resp = await respPromise;
            const hex = Array.from(resp).map(b => b.toString(16).padStart(2,'0')).join('');
            return 'GET_INFO: ' + hex.substring(0, 16);
        })()
    """)
    print(f"    {result}")

    # Step 3: Inject firmware data and flash functions
    print("\n[3] Injecting firmware data into browser context...")
    
    # Send firmware in chunks (base64 string might be too large for single eval)
    chunk_size = 100000  # 100KB of base64 at a time
    total_chunks_b64 = (len(fw_b64) + chunk_size - 1) // chunk_size
    
    result = cdp_eval(ws, "window._fwB64Parts = []; 'ready'")
    for i in range(total_chunks_b64):
        part = fw_b64[i * chunk_size : (i + 1) * chunk_size]
        result = cdp_eval(ws, f"window._fwB64Parts.push('{part}'); window._fwB64Parts.length")
        print(f"    Uploaded part {i+1}/{total_chunks_b64}: {result}")
    
    # Decode base64 to Uint8Array in browser
    result = cdp_eval(ws, """
        (() => {
            const b64 = window._fwB64Parts.join('');
            const raw = atob(b64);
            const arr = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
            window._firmware = arr;
            return 'Firmware loaded: ' + arr.length + ' bytes, first 16: ' + 
                Array.from(arr.slice(0, 16)).map(b => b.toString(16).padStart(2,'0')).join(' ');
        })()
    """)
    print(f"    {result}")

    # Step 4: Define flash helper functions in browser
    print("\n[4] Setting up flash protocol in browser...")
    result = cdp_eval(ws, """
        (() => {
            // Helper: send DFDB feature report command and get response
            window._sendDfdbCmd = async function(cmd, param) {
                const dev = window._bootDev;
                const data = new Uint8Array(64);
                data[0] = 0xDF;
                data[1] = 0xDB;
                data[2] = cmd;
                
                if (param !== undefined) {
                    // Write param as uint32 little-endian at offset 3
                    data[3] = param & 0xFF;
                    data[4] = (param >> 8) & 0xFF;
                    data[5] = (param >> 16) & 0xFF;
                    data[6] = (param >> 24) & 0xFF;
                }
                
                const respPromise = new Promise((resolve, reject) => {
                    const t = setTimeout(() => resolve(null), 3000);
                    dev.addEventListener('inputreport', (e) => {
                        clearTimeout(t);
                        resolve(new Uint8Array(e.data.buffer));
                    }, {once: true});
                });
                
                await dev.sendFeatureReport(0, data);
                return await respPromise;
            };
            
            // Helper: send output report (raw data chunk)
            window._sendOutput = async function(chunk) {
                const dev = window._bootDev;
                await dev.sendReport(0, chunk);
            };
            
            // Helper: hex string from Uint8Array
            window._hex = function(arr, len) {
                if (!arr) return 'null';
                const slice = len ? arr.slice(0, len) : arr;
                return Array.from(slice).map(b => b.toString(16).padStart(2,'0')).join('');
            };
            
            return 'Flash functions ready';
        })()
    """)
    print(f"    {result}")

    # Step 5: Execute flash protocol
    print("\n[5] Starting flash process...")
    
    CHUNK_SIZE = 256
    OUTPUT_SIZE = 64
    num_chunks = len(binary) // CHUNK_SIZE
    
    # Step 5a: GET_INFO
    result = cdp_eval(ws, """
        (async () => {
            const resp = await window._sendDfdbCmd(0x00);
            return 'GET_INFO: ' + window._hex(resp, 8);
        })()
    """)
    print(f"    {result}")

    # Step 5b: ERASE (CMD 6 with magic key 0xFFAAFFBB)
    print("    Sending ERASE (CMD 6)...")
    result = cdp_eval(ws, """
        (async () => {
            const resp = await window._sendDfdbCmd(0x06, 0xFFAAFFBB);
            return 'ERASE: ' + window._hex(resp, 8);
        })()
    """, timeout=10)
    print(f"    {result}")

    # Step 5c: PREPARE (CMD 2 with num_chunks)
    print(f"    Sending PREPARE (CMD 2, chunks={num_chunks})...")
    result = cdp_eval(ws, f"""
        (async () => {{
            const resp = await window._sendDfdbCmd(0x02, {num_chunks});
            return 'PREPARE: ' + window._hex(resp, 8);
        }})()
    """, timeout=10)
    print(f"    {result}")

    # Step 5d: Flash all chunks
    print(f"    Flashing {num_chunks} chunks (256 bytes each)...")
    
    # Do larger batches for speed, with good progress reporting
    batch_size = 50
    for batch_start in range(0, num_chunks, batch_size):
        batch_end = min(batch_start + batch_size, num_chunks)
        
        result = cdp_eval(ws, f"""
            (async () => {{
                const fw = window._firmware;
                const CHUNK = 256;
                const OUTPUT = 64;
                let lastResp = '';
                let errors = 0;
                
                for (let i = {batch_start}; i < {batch_end}; i++) {{
                    // Send 4x64B output reports for this 256B chunk
                    for (let j = 0; j < CHUNK / OUTPUT; j++) {{
                        const offset = i * CHUNK + j * OUTPUT;
                        const sub = fw.slice(offset, offset + OUTPUT);
                        await window._sendOutput(sub);
                    }}
                    
                    // CONFIRM chunk (CMD 3 + chunk index)
                    const resp = await window._sendDfdbCmd(0x03, i);
                    const respHex = window._hex(resp, 8);
                    lastResp = respHex;
                    
                    // Check for error responses
                    if (resp && resp[2] !== 0xFF) {{
                        errors++;
                    }}
                }}
                
                return 'last=' + lastResp + ' errors=' + errors;
            }})()
        """, timeout=120)
        
        pct = int(batch_end / num_chunks * 100)
        print(f"    [{pct:3d}%] chunks {batch_start}-{batch_end-1}: {result}")

    # Step 5e: STATUS check (CMD 4)
    print("    Checking STATUS (CMD 4)...")
    result = cdp_eval(ws, """
        (async () => {
            const resp = await window._sendDfdbCmd(0x04);
            return 'STATUS: ' + window._hex(resp, 16);
        })()
    """)
    print(f"    {result}")

    # Step 5f: REBOOT (CMD 5)
    print("    Sending REBOOT (CMD 5)...")
    result = cdp_eval(ws, """
        (async () => {
            try {
                const data = new Uint8Array(64);
                data[0] = 0xDF; data[1] = 0xDB; data[2] = 0x05;
                await window._bootDev.sendFeatureReport(0, data);
                return 'REBOOT sent';
            } catch(e) {
                return 'REBOOT: ' + e.message;
            }
        })()
    """)
    print(f"    {result}")

    print("\n[*] Waiting for keyboard to reboot...")
    time.sleep(5)

    # Check if normal device appears
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({
                name: d.productName,
                pid: '0x' + d.productId.toString(16),
                opened: d.opened
            }));
        })()
    """)
    print(f"    Devices: {result}")

    ws.close()
    print("\n[+] Done!")


def parse_intel_hex(path):
    """Parse Intel HEX file into binary, compact (no leading gap)."""
    # First pass: collect all data records with absolute addresses
    records = []
    base_addr = 0
    
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith(':'):
                continue
            
            raw = bytes.fromhex(line[1:])
            byte_count = raw[0]
            address = (raw[1] << 8) | raw[2]
            record_type = raw[3]
            payload = raw[4:4 + byte_count]
            
            if record_type == 0x04:  # Extended Linear Address
                base_addr = ((payload[0] << 8) | payload[1]) << 16
            elif record_type == 0x00:  # Data
                abs_addr = base_addr + address
                records.append((abs_addr, payload))
            elif record_type == 0x01:  # EOF
                break
    
    if not records:
        return bytes()
    
    # Find min address to create compact binary
    min_addr = min(addr for addr, _ in records)
    max_end = max(addr + len(d) for addr, d in records)
    
    data = bytearray(b'\xFF' * (max_end - min_addr))
    for addr, payload in records:
        offset = addr - min_addr
        data[offset:offset + len(payload)] = payload
    
    # Pad to chunk boundary
    while len(data) % 256 != 0:
        data.append(0xFF)
    
    print(f"    Address range: 0x{min_addr:08X} - 0x{max_end:08X}")
    print(f"    Compact binary: {len(data)} bytes ({len(data)//256} chunks)")
    
    return bytes(data)


if __name__ == "__main__":
    main()
