"""Quick CDP connection check and WebHID inspection."""
import requests
import json
import sys
import websocket
import time

PORT = 9222

def cdp_eval(ws_url, expr, timeout=10):
    ws = websocket.create_connection(ws_url, timeout=timeout)
    ws.send(json.dumps({
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {
            'expression': expr,
            'returnByValue': True,
            'awaitPromise': True,
            'timeout': timeout * 1000,
        }
    }))
    while True:
        resp = json.loads(ws.recv())
        if resp.get('id') == 1:
            ws.close()
            return resp.get('result', {}).get('result', {}).get('value')
    

def main():
    # Connect
    print("[*] Connecting to CDP...")
    try:
        r = requests.get(f'http://127.0.0.1:{PORT}/json', timeout=3)
        targets = r.json()
    except:
        print("[-] Cannot connect. Launch Wootility with --remote-debugging-port=9222")
        sys.exit(1)
    
    page = None
    for t in targets:
        print(f"  Target: type={t.get('type')} title={t.get('title')}")
        if t.get('type') == 'page':
            page = t
    
    if not page:
        print("[-] No page target found!")
        sys.exit(1)
    
    ws_url = page['webSocketDebuggerUrl']
    print(f"[+] WS: {ws_url}\n")
    
    # Wait for app load
    time.sleep(2)
    
    # Check WebHID devices
    print("[*] WebHID devices:")
    devs = cdp_eval(ws_url, """
        (async () => {
            const devices = await navigator.hid.getDevices();
            return devices.map(d => ({
                name: d.productName,
                vid: d.vendorId,
                pid: d.productId,
                opened: d.opened,
                collections: d.collections.length
            }));
        })()
    """)
    if devs:
        for d in devs:
            print(f"  {d}")
    else:
        print("  (none)")
    
    # Check Vue/Pinia stores for device state
    print("\n[*] App state:")
    state = cdp_eval(ws_url, """
        (() => {
            const app = document.querySelector('#app');
            const results = {};
            
            // Vue 3 app
            if (app && app.__vue_app__) {
                results.vue = true;
                const gp = app.__vue_app__.config.globalProperties;
                results.globals = Object.keys(gp).filter(k => k.startsWith('$'));
            }
            
            // Pinia
            if (window.__pinia) {
                results.pinia = true;
                const stores = {};
                window.__pinia._s.forEach((store, name) => {
                    stores[name] = Object.keys(store.$state || store);
                });
                results.stores = stores;
            }
            
            return results;
        })()
    """)
    print(f"  {json.dumps(state, indent=2)}")
    
    # Try to find device/firmware state in Pinia stores
    print("\n[*] Looking for firmware/device state...")
    fw_state = cdp_eval(ws_url, """
        (() => {
            if (!window.__pinia) return {error: 'no pinia'};
            const results = {};
            window.__pinia._s.forEach((store, name) => {
                const state = store.$state || store;
                const stateStr = JSON.stringify(state);
                if (stateStr.includes('firmware') || stateStr.includes('serial') || 
                    stateStr.includes('version') || stateStr.includes('bootloader') ||
                    stateStr.includes('update') || stateStr.includes('flash')) {
                    results[name] = {};
                    for (const [k, v] of Object.entries(state)) {
                        if (typeof v !== 'function') {
                            const vs = JSON.stringify(v);
                            if (vs && vs.length < 500) {
                                results[name][k] = v;
                            } else if (vs) {
                                results[name][k] = `[${typeof v}, len=${vs.length}]`;
                            }
                        }
                    }
                }
            });
            return results;
        })()
    """)
    if fw_state:
        print(f"  {json.dumps(fw_state, indent=2, default=str)}")
    
    # Try to find the firmware update function
    print("\n[*] Looking for update/flash actions...")
    actions = cdp_eval(ws_url, """
        (() => {
            if (!window.__pinia) return {error: 'no pinia'};
            const results = {};
            window.__pinia._s.forEach((store, name) => {
                const actionNames = [];
                for (const key of Object.keys(store)) {
                    if (typeof store[key] === 'function' && !key.startsWith('$') && !key.startsWith('_')) {
                        const fnStr = store[key].toString().substring(0, 100);
                        if (key.toLowerCase().includes('flash') || 
                            key.toLowerCase().includes('update') ||
                            key.toLowerCase().includes('firmware') ||
                            key.toLowerCase().includes('bootloader') ||
                            key.toLowerCase().includes('restore')) {
                            actionNames.push(key);
                        }
                    }
                }
                if (actionNames.length > 0) {
                    results[name] = actionNames;
                }
            });
            return results;
        })()
    """)
    if actions:
        print(f"  {json.dumps(actions, indent=2)}")
    else:
        print("  (none found)")
    
    # List ALL store names and their action names
    print("\n[*] All Pinia stores and actions:")
    all_stores = cdp_eval(ws_url, """
        (() => {
            if (!window.__pinia) return 'no pinia';
            const results = {};
            window.__pinia._s.forEach((store, name) => {
                const actions = [];
                for (const key of Object.keys(store)) {
                    if (typeof store[key] === 'function' && !key.startsWith('$') && !key.startsWith('_')) {
                        actions.push(key);
                    }
                }
                results[name] = actions;
            });
            return results;
        })()
    """)
    if all_stores:
        for store_name, actions in (all_stores.items() if isinstance(all_stores, dict) else []):
            flash_related = [a for a in actions if any(k in a.lower() for k in 
                            ['flash', 'update', 'firmware', 'boot', 'restore', 'serial', 'device', 'version'])]
            if flash_related:
                print(f"  [{store_name}] RELEVANT: {flash_related}")
            else:
                print(f"  [{store_name}] {len(actions)} actions")


if __name__ == "__main__":
    main()
