"""
Intercept WebHID traffic and find Wootility's internal flash function.
Instead of reimplementing the protocol, we'll use Wootility's own code.
"""
import json
import time
import urllib.request
import websocket

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
                    return f"EXCEPTION: {result.get('description', '')}"
                return result.get("value", result.get("description", str(result)))
        except websocket.WebSocketTimeoutException:
            continue
    return "TIMEOUT"

def main():
    ws_url = get_ws_url()
    ws = websocket.create_connection(ws_url, timeout=5)
    print("[+] Connected to Wootility CDP")

    # Step 1: Inject traffic interceptor on the bootloader device
    print("\n[1] Setting up WebHID traffic interceptor...")
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return 'No boot device';
            if (!boot.opened) await boot.open();
            
            // Create traffic log
            window._hidLog = [];
            
            // Wrap sendFeatureReport
            const origSendFeature = boot.sendFeatureReport.bind(boot);
            boot.sendFeatureReport = async function(rid, data) {
                const arr = new Uint8Array(data instanceof ArrayBuffer ? data : data.buffer || data);
                window._hidLog.push({
                    type: 'sendFeatureReport',
                    rid: rid,
                    data: Array.from(arr.slice(0, 8)).map(b => b.toString(16).padStart(2,'0')).join(' '),
                    size: arr.length,
                    time: Date.now()
                });
                return origSendFeature(rid, data);
            };
            
            // Wrap sendReport (output report)
            const origSendReport = boot.sendReport.bind(boot);
            boot.sendReport = async function(rid, data) {
                const arr = new Uint8Array(data instanceof ArrayBuffer ? data : data.buffer || data);
                window._hidLog.push({
                    type: 'sendReport',
                    rid: rid,
                    data: Array.from(arr.slice(0, 8)).map(b => b.toString(16).padStart(2,'0')).join(' '),
                    size: arr.length,
                    time: Date.now()
                });
                return origSendReport(rid, data);
            };
            
            window._bootDev = boot;
            return 'Interceptor installed on ' + boot.productName;
        })()
    """)
    print(f"    {result}")

    # Step 2: Search for the firmware update classes in the JS modules
    print("\n[2] Searching for firmware update code in loaded modules...")
    result = cdp_eval(ws, """
        (() => {
            // Search through all script elements for relevant code
            const scripts = document.querySelectorAll('script');
            const results = [];
            
            for (const script of scripts) {
                if (script.src) results.push('Script src: ' + script.src);
            }
            
            // Check if there are any module imports
            // Also look for global class constructors
            const constructors = [];
            for (const key of Object.getOwnPropertyNames(window)) {
                try {
                    const val = window[key];
                    if (typeof val === 'function' && val.prototype) {
                        const proto = Object.getOwnPropertyNames(val.prototype);
                        if (proto.some(p => p.toLowerCase().includes('firmware') || 
                                       p.toLowerCase().includes('flash') ||
                                       p.toLowerCase().includes('bootloader'))) {
                            constructors.push({name: key, methods: proto});
                        }
                    }
                } catch(e) {}
            }
            
            return { scripts: results, constructors: constructors };
        })()
    """)
    print(f"    {result}")

    # Step 3: Search through the main JS bundle for the executeFirmwareUpdate function
    print("\n[3] Scanning JS bundle for flash protocol...")
    result = cdp_eval(ws, """
        (async () => {
            // Get the main JS bundle
            const scripts = document.querySelectorAll('script[src]');
            let mainSrc = null;
            for (const s of scripts) {
                if (s.src.includes('index') || s.src.includes('main') || s.src.includes('app')) {
                    mainSrc = s.src;
                    break;
                }
            }
            if (!mainSrc && scripts.length > 0) {
                mainSrc = scripts[scripts.length - 1].src;
            }
            
            if (!mainSrc) return 'No script found';
            
            // Fetch the JS source
            const resp = await fetch(mainSrc);
            const code = await resp.text();
            window._jsCode = code;
            
            // Search for key patterns
            const patterns = [
                'executeFirmwareUpdate',
                'CHUNK_SIZE',
                'sendCommandNoResponse',
                'sendCommandWithResponse', 
                'FlashingFi',
                '0xFFAAFFBB',
                'ffaaffbb',
                'ERASE',
                'PrepareFlash',
                'prepareFlash',
                'numChunks',
                'chunkIndex',
                'bootloaderDevice',
                'Ce.prototype',
            ];
            
            const found = {};
            for (const pat of patterns) {
                const idx = code.indexOf(pat);
                if (idx >= 0) {
                    found[pat] = {
                        pos: idx,
                        context: code.substring(Math.max(0, idx - 40), idx + 60)
                    };
                }
            }
            
            return { scriptSrc: mainSrc, codeLength: code.length, found: found };
        })()
    """, timeout=20)
    print(f"    {json.dumps(result, indent=2) if isinstance(result, dict) else result}")

    # Step 4: Find the actual protocol constants
    print("\n[4] Deep-searching for bootloader protocol details...")
    result = cdp_eval(ws, """
        (() => {
            const code = window._jsCode;
            if (!code) return 'No code loaded';
            
            // Search for numeric patterns that might be protocol constants
            const searches = [
                // DFDB magic bytes
                { name: 'DFDB_0xDFDB', pattern: '57307' },  // 0xDFDB = 57307
                { name: 'DFDB_0xdfdb', pattern: '0xdfdb' },
                { name: 'DFDB_hex', pattern: '\\\\xdf\\\\xdb' },
                // Output size and chunk size
                { name: 'size_256', pattern: '=256' },
                { name: 'size_64', pattern: '=64' },
                // Magic erase key
                { name: 'erase_key', pattern: '4289396667' }, // 0xFFAAFFBB
                { name: 'erase_hex', pattern: 'ffaaffbb' },
                // sendReport
                { name: 'sendReport', pattern: 'sendReport' },
                { name: 'sendFeatureReport', pattern: 'sendFeatureReport' },
                // class patterns
                { name: 'protocolRevision', pattern: 'protocolRevision' },
                { name: '_magicWord', pattern: '_magicWord' },
                { name: 'magicWord', pattern: 'magicWord' },
            ];
            
            const results = {};
            for (const s of searches) {
                let count = 0;
                let firstCtx = '';
                let idx = code.indexOf(s.pattern);
                while (idx >= 0 && count < 3) {
                    count++;
                    if (count === 1) {
                        firstCtx = code.substring(Math.max(0, idx - 50), idx + 80);
                    }
                    idx = code.indexOf(s.pattern, idx + 1);
                }
                if (count > 0) {
                    results[s.name] = { count: count, ctx: firstCtx };
                }
            }
            
            return results;
        })()
    """)
    print(f"    {json.dumps(result, indent=2) if isinstance(result, dict) else result}")

    ws.close()
    print("\n[+] Done")

if __name__ == "__main__":
    main()
