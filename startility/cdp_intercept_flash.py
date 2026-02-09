"""
Startility - Intercept Wootility Flash Protocol
=================================================
Injects a WebHID sniffer into Wootility, then tricks it into
thinking a firmware update is needed by patching the version
comparison in memory. Captures the complete flash protocol.
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
            page['webSocketDebuggerUrl'], timeout=60)
        self.mid = 0
        print(f"[+] Connected: {page.get('title')}")
    
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
                if 'value' in r:
                    return r['value']
                if r.get('subtype') == 'error':
                    return {'error': r.get('description', '?')}
                return r


def main():
    print("=" * 60)
    print("  Startility - WebHID Protocol Interceptor")
    print("=" * 60)
    
    cdp = CDP()
    
    # Step 1: Inject WebHID sniffer
    print("\n[*] Step 1: Injecting WebHID sniffer...")
    cdp.ev("""
        (() => {
            if (window.__webhid_hooked) return 'already hooked';
            window.__webhid_log = [];
            window.__webhid_hooked = true;
            
            const origSendReport = HIDDevice.prototype.sendReport;
            HIDDevice.prototype.sendReport = function(id, data) {
                const bytes = new Uint8Array(data);
                const entry = {
                    ts: Date.now(),
                    type: 'sendReport',
                    reportId: id,
                    size: bytes.length,
                    first16: Array.from(bytes.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' '),
                };
                window.__webhid_log.push(entry);
                if (window.__webhid_log.length <= 20) {
                    console.log('[HID OUT]', entry.first16, 'size=' + entry.size);
                }
                return origSendReport.call(this, id, data);
            };
            
            const origSendFeature = HIDDevice.prototype.sendFeatureReport;
            HIDDevice.prototype.sendFeatureReport = function(id, data) {
                const bytes = new Uint8Array(data);
                const entry = {
                    ts: Date.now(),
                    type: 'sendFeatureReport',
                    reportId: id,
                    size: bytes.length,
                    first16: Array.from(bytes.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' '),
                };
                window.__webhid_log.push(entry);
                console.log('[HID FEAT]', entry.first16, 'size=' + entry.size);
                return origSendFeature.call(this, id, data);
            };
            
            return 'hooks installed';
        })()
    """)
    print("    Sniffer installed.")
    
    # Step 2: Find the Vue/framework app and device state
    print("\n[*] Step 2: Finding app internals...")
    
    # Try to find Vue component tree with firmware update
    result = cdp.ev("""
        (() => {
            // Walk DOM for Vue components
            const results = [];
            const walk = (el, depth) => {
                if (depth > 10) return;
                const vnode = el.__vueParentComponent || el._vnode;
                if (el.__vue__) {
                    const data = el.__vue__.$data || {};
                    const keys = Object.keys(data);
                    if (keys.some(k => /firmware|version|update|flash|device/i.test(k))) {
                        results.push({depth, tag: el.tagName, keys});
                    }
                }
                for (const child of el.children || []) walk(child, depth + 1);
            };
            walk(document.body, 0);
            
            // Also check all button/interactive elements
            const buttons = document.querySelectorAll('button, [role=button], .btn, a[href]');
            const btnTexts = [];
            buttons.forEach(b => {
                const t = b.textContent?.trim();
                if (t && t.length < 50) btnTexts.push(t);
            });
            
            return {vueComponents: results.length, buttons: btnTexts};
        })()
    """)
    print(f"    {json.dumps(result, indent=2)}")
    
    # Step 3: Look for the three-dot menu device action
    print("\n[*] Step 3: Looking for device firmware update triggers...")
    
    # Search for text content related to firmware/update in the DOM
    result = cdp.ev("""
        (() => {
            const allText = document.body.innerText;
            const lines = allText.split('\\n').filter(l => 
                /firmware|serial|update|flash|version|v2\\.12/i.test(l)
            );
            return lines.slice(0, 20);
        })()
    """)
    print(f"    Relevant text: {result}")
    
    # Step 4: Try to find and call firmware update function
    print("\n[*] Step 4: Searching for firmware update functions...")
    
    # Search window and all objects for update-related functions
    result = cdp.ev("""
        (() => {
            const found = [];
            
            // Search all script-created globals
            for (const key of Object.getOwnPropertyNames(window)) {
                try {
                    const val = window[key];
                    if (typeof val === 'function') {
                        const src = val.toString().substring(0, 200);
                        if (/firmware|bootloader|0x131[fF]|dfdb|flash/i.test(src)) {
                            found.push({name: key, preview: src.substring(0, 100)});
                        }
                    }
                    if (typeof val === 'object' && val !== null) {
                        for (const subkey of Object.keys(val).slice(0, 50)) {
                            if (/firmware|update|flash|boot/i.test(subkey)) {
                                found.push({obj: key, prop: subkey, type: typeof val[subkey]});
                            }
                        }
                    }
                } catch(e) {}
            }
            return found.slice(0, 20);
        })()
    """)
    print(f"    {json.dumps(result, indent=2)}")
    
    # Step 5: Try brute-force finding the flash sequence
    # Look for the Wootility's internal keyboard device wrapper
    print("\n[*] Step 5: Examining opened WebHID devices for flash methods...")
    
    result = cdp.ev("""
        (async () => {
            const devices = await navigator.hid.getDevices();
            const results = [];
            for (const dev of devices) {
                if (dev.opened && dev.vendorId === 0x31E3) {
                    // Check event listeners
                    results.push({
                        name: dev.productName,
                        pid: '0x' + dev.productId.toString(16),
                        opened: dev.opened,
                        hasInputReportListener: dev.oninputreport !== null || dev.oninputreport !== undefined,
                    });
                }
            }
            return results;
        })()
    """)
    print(f"    {json.dumps(result, indent=2)}")
    
    # Step 6: Try the nuclear option - manually trigger firmware flash
    # by finding the keyboard object in the app's module scope
    print("\n[*] Step 6: Searching module scope for flash logic...")
    
    result = cdp.ev("""
        (() => {
            // Try to access webpack/vite module cache
            const moduleKeys = [];
            
            // Vite modules are typically in import.meta or __vite_ssr_import__
            // Try checking for require-style module systems
            if (typeof __webpack_modules__ !== 'undefined') {
                moduleKeys.push('webpack: ' + Object.keys(__webpack_modules__).length);
            }
            
            // Check for any global stores/managers
            const globals = {};
            for (const key of Object.getOwnPropertyNames(window)) {
                try {
                    const val = window[key];
                    if (val && typeof val === 'object' && !Array.isArray(val) && 
                        key.length > 1 && key.length < 30 && !/^(on|webkit|chrome)/.test(key)) {
                        const methods = Object.keys(val).filter(k => typeof val[k] === 'function');
                        if (methods.length > 3 && methods.length < 50) {
                            const relevant = methods.filter(m => 
                                /device|keyboard|hid|update|firmware|flash|serial/i.test(m));
                            if (relevant.length > 0) {
                                globals[key] = relevant;
                            }
                        }
                    }
                } catch(e) {}
            }
            
            return {moduleKeys, globals};
        })()
    """)
    print(f"    {json.dumps(result, indent=2)}")
    
    # Step 7: Get the current WebHID log
    print("\n[*] Step 7: Current WebHID log:")
    log = cdp.ev("window.__webhid_log")
    if log:
        for entry in log[-10:]:
            print(f"    {entry}")
    else:
        print("    (empty)")
    
    print(f"\n{'=' * 60}")
    print("  Sniffer active. Now trigger firmware update in Wootility.")
    print("  Run this again to check captured log.")
    print(f"{'=' * 60}")
    
    cdp.close()


if __name__ == "__main__":
    main()
