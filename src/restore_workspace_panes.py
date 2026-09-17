# -*- coding: utf-8 -*-
"""
Antigravity 多分屏工作台一键恢复与记忆中控
"""
import os
import sys
import json
import asyncio
import subprocess
import urllib.request
import urllib.parse
import websockets

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\workspace_panes.json")
DEVTOOLS_PORT_PATH = os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort")

def find_live_web_server_port():
    import ssl
    import psutil
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    candidate_ports = []
    for p in psutil.process_iter(['pid', 'name']):
        try:
            name = (p.info.get('name') or '').lower()
            if 'language_server' in name or 'antigravity' in name:
                for conn in p.net_connections():
                    if conn.status == 'LISTEN' and conn.laddr.port:
                        candidate_ports.append(conn.laddr.port)
        except Exception:
            pass
    for port in sorted(set(candidate_ports)):
        try:
            req = urllib.request.urlopen(f'https://127.0.0.1:{port}/c', context=ctx, timeout=1.5)
            if req.status in (200, 301, 302, 404):
                return port
        except Exception:
            pass
    return None


def get_devtools_ws_url():
    if not os.path.exists(DEVTOOLS_PORT_PATH):
        raise RuntimeError("未找到 Antigravity DevToolsActivePort，请确认客户端正在运行")
    with open(DEVTOOLS_PORT_PATH, "r", encoding="utf-8", errors="ignore") as f:
        port = int(f.readline().strip())

    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json")
    targets = json.loads(req.read().decode("utf-8"))
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        raise RuntimeError("未检测到可用的 Antigravity 页面")
    return pages[0]["webSocketDebuggerUrl"], pages[0].get("url", "")

async def cdp_call(ws, seq_holder, method, params=None):
    seq_holder[0] += 1
    cur_id = seq_holder[0]
    payload = {"id": cur_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        msg = await ws.recv()
        d = json.loads(msg)
        if d.get("id") == cur_id:
            return d

def load_localization_script():
    base_dirs = [
        os.path.join(os.path.dirname(__file__), "localization-extension"),
        os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher\localization-extension"),
        r"d:\AICode\工具开发\projects\antigravity-recovery-launcher\src\localization-extension"
    ]
    for d in base_dirs:
        core_p = os.path.join(d, "translation-core.js")
        content_p = os.path.join(d, "content.js")
        if os.path.exists(core_p) and os.path.exists(content_p):
            with open(core_p, "r", encoding="utf-8") as f:
                core_js = f.read()
            with open(content_p, "r", encoding="utf-8") as f:
                content_js = f.read()
            return core_js + "\n" + content_js
    return ""

async def hide_install_ide(ws, seq_holder):
    js = """
    (() => {
        let style = document.getElementById('__agy_hide_ide_btn__');
        if (!style) {
            style = document.createElement('style');
            style.id = '__agy_hide_ide_btn__';
            style.textContent = `
                button[data-testid="install-editor"],
                button[data-testid^="open-editor"],
                button[data-testid="editor-loading"],
                a[data-testid="install-editor"],
                a[data-testid^="open-editor"] { display: none !important; }
            `;
            (document.head || document.documentElement).appendChild(style);
        }
    })()
    """
    await cdp_call(ws, seq_holder, "Runtime.evaluate", {"expression": js})

async def save_current_layout():
    ws_url, page_url = get_devtools_ws_url()
    seq_holder = [100]
    async with websockets.connect(ws_url) as ws:
        js = """
        (() => {
            const path = window.location.pathname;
            const match = path.match(/\/c\/([^/?]+)/);
            if (!match) return null;
            const ids = match[1].split(/[\+\s]+/);
            return {
                ids,
                url: window.location.href
            };
        })()
        """
        res = await cdp_call(ws, seq_holder, "Runtime.evaluate", {"expression": js, "returnByValue": True})
        val = res.get("result", {}).get("result", {}).get("value")
        if not val or not val.get("ids"):
            print("未能从当前页面中解析出分屏会话 ID")
            return

        ids = [i for i in val["ids"] if i and i != "_new"]
        config = {
            "updated_at": __import__("datetime").datetime.now().isoformat(),
            "columns": [{"id": cid} for cid in ids],
            "focused": ids[0] if ids else ""
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[OK] 成功保存当前 {len(ids)} 列分屏布局到 {CONFIG_PATH}")

async def restore_layout():
    if not os.path.exists(CONFIG_PATH):
        print(f"未找到布局配置文件: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    columns = [c["id"] if isinstance(c, dict) else c for c in config.get("columns", [])]
    focused = config.get("focused", columns[0] if columns else "")

    if not columns:
        print("配置文件中未定义任何分屏列")
        return

    ws_url, page_url = get_devtools_ws_url()
    seq_holder = [100]

    parsed = urllib.parse.urlparse(page_url)
    if parsed.netloc and "chrome-error" not in page_url:
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
    else:
        live_port = find_live_web_server_port()
        base_origin = f"https://127.0.0.1:{live_port}" if live_port else "https://127.0.0.1:61658"

    combined_route = "+".join(columns)
    target_url = f"{base_origin}/c/{combined_route}?focused={focused}"

    injection_script = load_localization_script()

    print(f"正在复原 {len(columns)} 列工作台: {target_url}")
    async with websockets.connect(ws_url) as ws:
        # Pre-register script before navigating
        if injection_script:
            await cdp_call(ws, seq_holder, "Page.addScriptToEvaluateOnNewDocument", {"source": injection_script})

        await cdp_call(ws, seq_holder, "Page.navigate", {"url": target_url})
        await asyncio.sleep(2.5)

        if injection_script:
            await cdp_call(ws, seq_holder, "Runtime.evaluate", {"expression": injection_script})
        await hide_install_ide(ws, seq_holder)

        target_idx = columns.index(focused) if focused in columns else 0
        js_focus = f"""
        (() => {{
            const panes = Array.from(document.querySelectorAll('.group\\\\/pane'));
            const target = panes[{target_idx}] || panes[0];
            if (target) {{
                const ed = target.querySelector('[data-lexical-editor="true"]') || target;
                ed.focus();
            }}
        }})()
        """
        await cdp_call(ws, seq_holder, "Runtime.evaluate", {"expression": js_focus})

    # Trigger official loader as well
    loader = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher\Antigravity-CdpLocalizationLoader.exe")
    if os.path.exists(loader):
        try:
            subprocess.run([loader], capture_output=True, timeout=5)
        except Exception:
            pass

    print(f"[OK] 成功复原 {len(columns)} 列分屏！汉化语言包已同步注入，右上角干扰图标已彻底抹除。")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        asyncio.run(save_current_layout())
    else:
        asyncio.run(restore_layout())

if __name__ == "__main__":
    main()
