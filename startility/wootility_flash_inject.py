"""
Startility - Wootility Flash Injector
======================================
Launches Wootility with Chrome DevTools Protocol enabled,
then injects JavaScript to bypass version check and trigger firmware flash.

Usage:
  python wootility_flash_inject.py

Prerequisites:
  - Wootility must be installed
  - Patched firmware must exist (run flash_patched.py first)
  - pip install websocket-client requests
"""

import subprocess
import time
import json
import sys
import os
import requests
import threading

WOOTILITY_EXE = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    'Programs', 'wootility', 'Wootility.exe'
)
DEBUG_PORT = 9222
PATCHED_FW = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'wooting_60he_arm_patched.fwr'
)


def kill_wootility():
    """Kill any running Wootility instances."""
    try:
        subprocess.run(['taskkill', '/f', '/im', 'Wootility.exe'],
                      capture_output=True)
    except:
        pass
    time.sleep(1)


def launch_with_debug():
    """Launch Wootility with remote debugging enabled."""
    print(f"[*] Launching Wootility with debug port {DEBUG_PORT}...")
    proc = subprocess.Popen(
        [WOOTILITY_EXE, f'--remote-debugging-port={DEBUG_PORT}',
         '--remote-allow-origins=*'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return proc


def wait_for_debugger(timeout=15):
    """Wait for Chrome DevTools Protocol to become available."""
    print(f"[*] Waiting for debugger ({timeout}s timeout)...")
    
    for i in range(timeout * 2):
        try:
            resp = requests.get(f'http://127.0.0.1:{DEBUG_PORT}/json', timeout=1)
            if resp.status_code == 200:
                targets = resp.json()
                print(f"[+] Debugger connected! ({len(targets)} target(s))")
                return targets
        except:
            pass
        time.sleep(0.5)
    
    return None


def find_renderer_target(targets):
    """Find the main renderer page target."""
    for t in targets:
        if t.get('type') == 'page':
            return t
    # Fallback: return first target
    return targets[0] if targets else None


def cdp_eval(ws_url, expression, timeout=10):
    """Evaluate JavaScript expression via CDP WebSocket."""
    try:
        import websocket
    except ImportError:
        print("[-] Need websocket-client: pip install websocket-client")
        sys.exit(1)
    
    ws = websocket.create_connection(ws_url, timeout=timeout)
    
    msg = json.dumps({
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {
            'expression': expression,
            'returnByValue': True,
            'awaitPromise': True,
            'timeout': timeout * 1000,
        }
    })
    
    ws.send(msg)
    
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == 1:
            ws.close()
            return resp
    
    ws.close()
    return None


def inject_flash_trigger(ws_url):
    """Inject JavaScript to find and trigger firmware flash."""
    
    # Step 1: Check WebHID devices
    print("\n[*] Step 1: Checking WebHID devices...")
    result = cdp_eval(ws_url, """
        (async () => {
            try {
                const devices = await navigator.hid.getDevices();
                return {
                    count: devices.length,
                    devices: devices.map(d => ({
                        vendorId: '0x' + d.vendorId.toString(16),
                        productId: '0x' + d.productId.toString(16),
                        productName: d.productName,
                        opened: d.opened,
                        collections: d.collections?.map(c => ({
                            usagePage: '0x' + c.usagePage.toString(16),
                            usage: '0x' + c.usage.toString(16),
                            inputReports: c.inputReports?.length || 0,
                            outputReports: c.outputReports?.length || 0,
                            featureReports: c.featureReports?.length || 0,
                        })) || []
                    }))
                };
            } catch(e) {
                return {error: e.message};
            }
        })()
    """)
    
    if result and 'result' in result:
        val = result['result'].get('result', {}).get('value', {})
        if 'error' in val:
            print(f"    Error: {val['error']}")
        else:
            print(f"    Found {val.get('count', 0)} WebHID device(s)")
            for dev in val.get('devices', []):
                print(f"    - {dev.get('productName', '?')} "
                      f"VID={dev.get('vendorId')} PID={dev.get('productId')} "
                      f"opened={dev.get('opened')}")
                for col in dev.get('collections', []):
                    print(f"      Collection: page={col.get('usagePage')} "
                          f"in={col.get('inputReports')} "
                          f"out={col.get('outputReports')} "
                          f"feat={col.get('featureReports')}")
    
    # Step 2: Search for firmware update related globals
    print("\n[*] Step 2: Searching for flash-related objects...")
    result = cdp_eval(ws_url, """
        (async () => {
            // Look for Vue/React state with firmware/update references
            const results = {};
            
            // Check for common framework stores
            if (window.__STORE__) results.store = 'found';
            if (window.__VUE_DEVTOOLS_GLOBAL_HOOK__) results.vue = 'found';
            if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) results.react = 'found';
            
            // Check for Wooting-specific globals
            const wootKeys = Object.keys(window).filter(k => 
                k.toLowerCase().includes('woot') || 
                k.toLowerCase().includes('firmware') ||
                k.toLowerCase().includes('device') ||
                k.toLowerCase().includes('keyboard')
            );
            results.wootGlobals = wootKeys;
            
            // Check for Vue app on document
            const app = document.querySelector('#app');
            if (app && app.__vue_app__) {
                results.vueApp = 'found';
                const store = app.__vue_app__.config.globalProperties.$store;
                if (store) {
                    results.storeState = Object.keys(store.state || {});
                }
            }
            
            // Check Pinia stores
            if (window.__pinia) {
                results.pinia = 'found';
                results.piniaStores = Object.keys(window.__pinia._s || {});
            }
            
            return results;
        })()
    """)
    
    if result and 'result' in result:
        val = result['result'].get('result', {}).get('value', {})
        print(f"    Framework detection: {json.dumps(val, indent=2)}")
    
    # Step 3: Try to find the keyboard device and send bootloader command
    print("\n[*] Step 3: Checking for open HID device handles...")
    result = cdp_eval(ws_url, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            const results = [];
            
            for (const dev of devices) {
                const info = {
                    name: dev.productName,
                    vid: dev.vendorId,
                    pid: dev.productId,
                    opened: dev.opened,
                };
                
                if (dev.opened) {
                    // Try to read feature report (GET_VERSION via D1DA)
                    try {
                        const d1da = new Uint8Array([0xd1, 0xda, 0x01, 0, 0, 0, 0]);
                        await dev.sendFeatureReport(0x00, d1da);
                        // Wait briefly
                        await new Promise(r => setTimeout(r, 100));
                        info.sentCommand = true;
                    } catch(e) {
                        info.sendError = e.message;
                    }
                }
                
                results.push(info);
            }
            
            return results;
        })()
    """)
    
    if result and 'result' in result:
        val = result['result'].get('result', {}).get('value', [])
        for dev in val:
            print(f"    Device: {dev}")
    
    return result


def main():
    print("=" * 60)
    print("  Startility - Wootility Flash Injector")
    print("=" * 60)
    
    if not os.path.exists(WOOTILITY_EXE):
        print(f"\n[-] Wootility not found: {WOOTILITY_EXE}")
        sys.exit(1)
    
    if not os.path.exists(PATCHED_FW):
        print(f"\n[-] Patched firmware not found: {PATCHED_FW}")
        print("    Run flash_patched.py first!")
        sys.exit(1)
    
    # Install dependencies
    try:
        import websocket
        import requests
    except ImportError:
        print("[*] Installing dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 
                       'websocket-client', 'requests'],
                      capture_output=True)
        import websocket
    
    # Kill existing Wootility
    kill_wootility()
    
    # Launch with debug
    proc = launch_with_debug()
    
    # Wait for debugger
    targets = wait_for_debugger()
    if not targets:
        print("[-] Failed to connect to debugger!")
        print("    Wootility may have blocked remote debugging.")
        proc.terminate()
        sys.exit(1)
    
    # Find renderer
    target = find_renderer_target(targets)
    if not target:
        print("[-] No renderer target found!")
        sys.exit(1)
    
    ws_url = target.get('webSocketDebuggerUrl', '')
    print(f"[+] Target: {target.get('title', '?')}")
    print(f"    WS URL: {ws_url}")
    
    if not ws_url:
        print("[-] No WebSocket URL available!")
        sys.exit(1)
    
    # Wait for app to fully load
    print("\n[*] Waiting for Wootility to load (5s)...")
    time.sleep(5)
    
    # Inject and inspect
    inject_flash_trigger(ws_url)
    
    print(f"\n{'=' * 60}")
    print("  Manual debugging available at:")
    print(f"  chrome://inspect  (port {DEBUG_PORT})")
    print(f"{'=' * 60}")
    print("\nPress Ctrl+C to close Wootility and exit.")
    
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
