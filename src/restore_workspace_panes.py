# -*- coding: utf-8 -*-
"""
Antigravity 多分屏工作台一键恢复与记忆中控
"""
import os
import sys
import json
import asyncio
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
    base_origin = f"{parsed.scheme}://{parsed.netloc}"

    combined_route = "+".join(columns)
    target_url = f"{base_origin}/c/{combined_route}?focused={focused}"

    print(f"正在复原 {len(columns)} 列工作台: {target_url}")
    async with websockets.connect(ws_url) as ws:
        await cdp_call(ws, seq_holder, "Page.navigate", {"url": target_url})
        await asyncio.sleep(2.0)
        await hide_install_ide(ws, seq_holder)
        js_focus = f"""
        (() => {{
            const panes = Array.from(document.querySelectorAll('.group\\/pane'));
            const target = panes.find(p => p.querySelector('a[href*="{focused}"]')) || panes[0];
            if (target) {{
                const ed = target.querySelector('[data-lexical-editor="true"]') || target;
                ed.focus();
            }}
        }})()
        """
        await cdp_call(ws, seq_holder, "Runtime.evaluate", {"expression": js_focus})
        print(f"[OK] 成功复原 {len(columns)} 列分屏！已激活主工作台。")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        asyncio.run(save_current_layout())
    else:
        asyncio.run(restore_layout())

if __name__ == "__main__":
    main()
