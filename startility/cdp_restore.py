"""
CDP-based restore: Grant WebHID access to bootloader device,
then trigger Wootility's restore function.
"""
import json
import time
import urllib.request
import websocket

def get_ws_url():
    """Get CDP WebSocket URL."""
    data = urllib.request.urlopen("http://127.0.0.1:9222/json").read()
    targets = json.loads(data)
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    return None

def cdp_eval(ws, expr, timeout=10):
    """Evaluate JS expression via CDP."""
    msg_id = int(time.time() * 1000) % 100000
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
                return result.get("value", result.get("description", str(result)))
        except websocket.WebSocketTimeoutException:
            continue
    return None

def main():
    print("[*] Connecting to Wootility via CDP...")
    time.sleep(3)
    
    ws_url = get_ws_url()
    if not ws_url:
        print("[-] No Wootility page found!")
        return
    
    ws = websocket.create_connection(ws_url, timeout=5)
    print(f"[+] Connected to Wootility")

    # Check current HID devices
    print("\n[*] Checking WebHID devices...")
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({
                vendorId: d.vendorId,
                productId: d.productId,
                productName: d.productName,
                opened: d.opened
            }));
        })()
    """)
    print(f"    Current devices: {result}")

    # Try to request the bootloader device
    # In Electron, we can use session.defaultSession.setDevicePermissionHandler
    # But via CDP, we need to use the Electron API
    print("\n[*] Trying to grant HID permission for bootloader (0x131F)...")
    
    # Method 1: Try require('electron') to set permission handler
    result = cdp_eval(ws, """
        (async () => {
            try {
                // Try Electron's permission bypass
                const { session } = require('electron').remote || {};
                if (session) {
                    session.defaultSession.setDevicePermissionHandler((details) => {
                        return details.device.vendorId === 0x31E3;
                    });
                    return 'Permission handler set via electron.remote';
                }
            } catch(e) {}
            
            try {
                // Try via electronIntegration
                if (window.electronIntegration) {
                    return 'electronIntegration: ' + JSON.stringify(Object.keys(window.electronIntegration));
                }
            } catch(e) {}
            
            return 'No electron API access';
        })()
    """)
    print(f"    Result: {result}")

    # Method 2: Try navigator.hid.requestDevice with the bootloader filter
    print("\n[*] Requesting bootloader device via WebHID...")
    print("    NOTE: A device picker dialog may appear in Wootility - select 'Wooting Restore'!")
    result = cdp_eval(ws, """
        (async () => {
            try {
                const devices = await navigator.hid.requestDevice({
                    filters: [{ vendorId: 0x31E3, productId: 0x131F }]
                });
                return 'Got ' + devices.length + ' devices: ' + 
                    devices.map(d => d.productName).join(', ');
            } catch(e) {
                return 'Error: ' + e.message;
            }
        })()
    """, timeout=30)
    print(f"    Result: {result}")

    # Check devices again
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({
                vid: '0x' + d.vendorId.toString(16),
                pid: '0x' + d.productId.toString(16),
                name: d.productName,
                opened: d.opened
            }));
        })()
    """)
    print(f"\n    Devices after request: {result}")

    ws.close()
    print("\n[+] Done. Check Wootility UI for restore option.")

if __name__ == "__main__":
    main()
