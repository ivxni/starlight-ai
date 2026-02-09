"""Click Updates button in Wootility and check what's available."""
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
    print("[+] Connected to Wootility")

    # Click Updates button
    print("\n[*] Clicking 'Updates' button...")
    result = cdp_eval(ws, """
        (() => {
            const buttons = Array.from(document.querySelectorAll('button, [role=button], div[class*=btn], div[class*=item], span, a'));
            for (const btn of buttons) {
                if (btn.textContent?.trim() === 'Updates') {
                    btn.click();
                    return 'Clicked Updates';
                }
            }
            // Try finding by any clickable with Updates text
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.childNodes.length <= 2 && el.textContent?.trim() === 'Updates') {
                    el.click();
                    return 'Clicked Updates (generic)';
                }
            }
            return 'Updates button not found';
        })()
    """)
    print(f"    {result}")
    
    time.sleep(2)

    # Check what's on the page now
    result = cdp_eval(ws, """
        (() => {
            const buttons = Array.from(document.querySelectorAll('button, [role=button]'));
            const btnTexts = buttons.map(b => b.textContent?.trim()).filter(Boolean);
            
            const texts = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,p,span,div'))
                .map(el => {
                    const t = el.textContent?.trim();
                    if (!t || t.length < 3 || t.length > 200) return null;
                    // Only direct text, not nested
                    if (el.children.length > 3) return null;
                    return t;
                })
                .filter(Boolean)
                .filter((v, i, a) => a.indexOf(v) === i)
                .slice(0, 30);
            
            return { buttons: btnTexts, texts: texts };
        })()
    """)
    print(f"\n    Page content: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")

    # Also check if there's any firmware/restore related text
    result = cdp_eval(ws, """
        (() => {
            const body = document.body.innerText;
            const lines = body.split('\\n').filter(l => l.trim());
            const relevant = lines.filter(l => {
                const ll = l.toLowerCase();
                return ll.includes('firmware') || ll.includes('restore') || 
                       ll.includes('update') || ll.includes('flash') ||
                       ll.includes('version') || ll.includes('download') ||
                       ll.includes('current') || ll.includes('latest');
            });
            return relevant.slice(0, 20);
        })()
    """)
    print(f"\n    Relevant text: {result}")

    ws.close()
    print("\n[+] Done")

if __name__ == "__main__":
    main()
