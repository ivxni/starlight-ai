"""
CDP-based restore v2: Open the bootloader device directly via WebHID
and try to trigger Wootility's restore/flash functionality.
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
                    return f"EXCEPTION: {exc.get('text', '')} - {result.get('description', '')}"
                return result.get("value", result.get("description", str(result)))
        except websocket.WebSocketTimeoutException:
            continue
    return "TIMEOUT"

def main():
    print("[*] Connecting to Wootility via CDP...")
    time.sleep(2)
    
    ws_url = get_ws_url()
    if not ws_url:
        print("[-] No Wootility page found!")
        return
    
    ws = websocket.create_connection(ws_url, timeout=5)
    print(f"[+] Connected")

    # Step 1: Explore window scope for Wootility internals
    print("\n[1] Exploring Wootility internals...")
    
    # Check for Vue/React store or global state
    result = cdp_eval(ws, """
        (() => {
            const keys = Object.keys(window).filter(k => 
                !k.startsWith('__') && k !== 'chrome' && k !== 'navigator' && 
                k !== 'location' && k !== 'document' && k !== 'performance' &&
                typeof window[k] !== 'function' || 
                (typeof window[k] === 'function' && k.length > 3)
            ).slice(0, 50);
            return keys;
        })()
    """)
    print(f"    Window keys: {result}")

    # Check for Vue
    result = cdp_eval(ws, """
        (() => {
            const app = document.querySelector('#app');
            if (app && app.__vue_app__) return 'Vue3 found';
            if (app && app.__vue__) return 'Vue2 found';
            if (window.__NUXT__) return 'Nuxt found';
            if (window.__NEXT_DATA__) return 'Next found';
            if (window.__svelte_app__) return 'Svelte found';
            // Check for pinia/vuex stores
            const allKeys = Object.keys(window);
            const storeKeys = allKeys.filter(k => k.toLowerCase().includes('store') || k.toLowerCase().includes('pinia'));
            return 'Framework check: app=' + !!app + ', stores=' + JSON.stringify(storeKeys);
        })()
    """)
    print(f"    Framework: {result}")

    # Step 2: Open the bootloader device directly
    print("\n[2] Opening bootloader device via WebHID...")
    result = cdp_eval(ws, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            const boot = devices.find(d => d.productId === 0x131F);
            if (!boot) return 'No bootloader device found';
            
            if (!boot.opened) {
                await boot.open();
            }
            
            // Get collections info
            const collections = boot.collections.map(c => ({
                usagePage: '0x' + c.usagePage.toString(16),
                usage: '0x' + c.usage.toString(16),
                inputReports: c.inputReports?.map(r => ({id: r.reportId, items: r.items?.length})),
                outputReports: c.outputReports?.map(r => ({id: r.reportId, items: r.items?.length})),
                featureReports: c.featureReports?.map(r => ({id: r.reportId, items: r.items?.length}))
            }));
            
            window._bootDevice = boot;
            return {
                name: boot.productName,
                pid: '0x' + boot.productId.toString(16),
                vid: '0x' + boot.vendorId.toString(16),
                opened: boot.opened,
                collections: collections
            };
        })()
    """)
    print(f"    Device: {result}")

    # Step 3: Try DFDB GET_INFO command
    print("\n[3] Testing DFDB command (GET_INFO)...")
    result = cdp_eval(ws, """
        (async () => {
            const dev = window._bootDevice;
            if (!dev || !dev.opened) return 'Device not open';
            
            // Send GET_INFO: DFDB + CMD 0x00 + padding
            const cmd = new Uint8Array(64);
            cmd[0] = 0xDF;
            cmd[1] = 0xDB;
            cmd[2] = 0x00; // CMD 0 = GET_INFO
            
            // Set up response listener
            const responsePromise = new Promise((resolve, reject) => {
                const timeout = setTimeout(() => reject('timeout'), 3000);
                dev.addEventListener('inputreport', (event) => {
                    clearTimeout(timeout);
                    const data = new Uint8Array(event.data.buffer);
                    resolve(Array.from(data).map(b => b.toString(16).padStart(2,'0')).join(''));
                }, {once: true});
            });
            
            await dev.sendFeatureReport(0, cmd);
            
            try {
                const resp = await responsePromise;
                return 'Response: ' + resp;
            } catch(e) {
                // Try reading feature report instead
                try {
                    const fr = await dev.receiveFeatureReport(0);
                    const data = new Uint8Array(fr.buffer);
                    return 'FeatureReport: ' + Array.from(data).map(b => b.toString(16).padStart(2,'0')).join('');
                } catch(e2) {
                    return 'No response: ' + e + ', feature: ' + e2.message;
                }
            }
        })()
    """, timeout=10)
    print(f"    GET_INFO: {result}")

    # Step 4: Search for Wootility's flash/restore functions
    print("\n[4] Searching for Wootility flash/restore functions...")
    
    # Look for service workers, stores, etc
    result = cdp_eval(ws, """
        (() => {
            // Search for anything related to firmware/flash/restore/update
            const interesting = {};
            
            // Check electronIntegration
            if (window.electronIntegration) {
                interesting.electronKeys = Object.keys(window.electronIntegration);
            }
            
            // Look for global functions/objects
            for (const key of Object.getOwnPropertyNames(window)) {
                try {
                    const val = window[key];
                    const lk = key.toLowerCase();
                    if (lk.includes('firmware') || lk.includes('flash') || 
                        lk.includes('restore') || lk.includes('update') ||
                        lk.includes('keyboard') || lk.includes('wooting') ||
                        lk.includes('device') || lk.includes('boot') ||
                        lk.includes('store') || lk.includes('service')) {
                        interesting[key] = typeof val;
                    }
                } catch(e) {}
            }
            
            return interesting;
        })()
    """)
    print(f"    Interesting globals: {result}")

    # Step 5: Try to find Vue/Pinia stores via app internals
    print("\n[5] Checking Vue app for stores/services...")
    result = cdp_eval(ws, """
        (() => {
            const app = document.querySelector('#app');
            if (!app) return 'No #app element';
            
            // Vue 3
            if (app.__vue_app__) {
                const vueApp = app.__vue_app__;
                const config = vueApp.config;
                const provides = vueApp._context?.provides;
                
                if (provides) {
                    const keys = Object.keys(provides).slice(0, 20);
                    return 'Vue3 provides: ' + JSON.stringify(keys);
                }
                return 'Vue3 app found, no provides';
            }
            
            // Try Pinia
            const pinia = app.__vue_app__?.config?.globalProperties?.$pinia;
            if (pinia) {
                return 'Pinia stores: ' + JSON.stringify(Object.keys(pinia.state.value));
            }
            
            return 'No Vue app found on #app';
        })()
    """)
    print(f"    Vue: {result}")

    # Step 6: Try dispatching action via electronIntegration
    print("\n[6] Checking electronIntegration.onActionDispatch...")
    result = cdp_eval(ws, """
        (() => {
            if (window.electronIntegration && window.electronIntegration.onActionDispatch) {
                return typeof window.electronIntegration.onActionDispatch;
            }
            return 'no onActionDispatch';
        })()
    """)
    print(f"    onActionDispatch type: {result}")

    # Step 7: Look at the DOM for any hidden buttons/elements
    print("\n[7] Checking DOM for restore/update elements...")
    result = cdp_eval(ws, """
        (() => {
            const body = document.body.innerHTML;
            const restore = body.includes('restore') || body.includes('Restore');
            const update = body.includes('update') || body.includes('Update');
            const flash = body.includes('flash') || body.includes('Flash');
            const noDevice = body.includes('connect') || body.includes('Connect');
            
            // Get all buttons
            const buttons = Array.from(document.querySelectorAll('button, [role=button], .btn'));
            const btnTexts = buttons.map(b => b.textContent?.trim()).filter(Boolean);
            
            // Get visible text
            const h1s = Array.from(document.querySelectorAll('h1,h2,h3,h4,p,span'))
                .map(el => el.textContent?.trim())
                .filter(t => t && t.length > 2 && t.length < 100)
                .slice(0, 20);
                
            return {
                hasRestore: restore,
                hasUpdate: update, 
                hasFlash: flash,
                hasConnect: noDevice,
                buttons: btnTexts,
                texts: h1s
            };
        })()
    """)
    print(f"    DOM: {result}")

    ws.close()
    print("\n[+] Done")

if __name__ == "__main__":
    main()
