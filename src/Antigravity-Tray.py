# -*- coding: utf-8 -*-
"""
Antigravity 任务栏托盘常驻守护进程 (v1.0)
常驻在系统右下角任务栏托盘：
1. 动态显示私有代理实时延迟数字与颜色
2. 双击或右键菜单随时打开「Antigravity 私有代理中控台」
3. 支持单实例保护与伴随 Antigravity 生命期自动退出
"""

import os
import sys
import json
import time
import socket
import threading
import subprocess
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pystray

# --- 路径定义 ---
PROXY_ROOT = Path(os.environ['LOCALAPPDATA']) / 'Antigravity' / 'private-proxy'
STATE_FILE = PROXY_ROOT / 'supervisor-state.json'
CONFIG_FILE = PROXY_ROOT / 'mihomo-antigravity.yaml'
SCRIPT_ROOT = Path(__file__).resolve().parent
PANEL_SCRIPT = SCRIPT_ROOT / 'Antigravity-Panel.py'
PYTHONW_PATH = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Python' / 'Python311' / 'pythonw.exe'
if not PYTHONW_PATH.exists():
    PYTHONW_PATH = 'pythonw.exe'

tray_icon = None
current_lat = 9999
current_status = 'ready'
current_server = ''
current_egress = 'US'
lock_socket = None


def ensure_single_instance():
    """使用本地 socket 确保只有一个托盘实例在运行"""
    global lock_socket
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(('127.0.0.1', 17898))
        lock_socket.listen(1)
        return True
    except Exception:
        # 已有实例在运行，直接退出
        sys.exit(0)


def is_antigravity_alive():
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq Antigravity.exe'],
            text=True,
            errors='ignore'
        )
        return 'antigravity.exe' in out.lower()
    except Exception:
        return True


def get_current_info():
    global current_lat, current_status, current_server, current_egress
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, encoding='utf-8-sig') as f:
                s = json.load(f)
                current_status = s.get('status', 'ready')
                current_egress = s.get('egress_country', 'US')
    except Exception:
        pass

    try:
        if CONFIG_FILE.exists():
            txt = CONFIG_FILE.read_text(encoding='utf-8')
            m = re.search(r'server:\s*([^\s,]+),\s*port:\s*(\d+)', txt)
            if m:
                current_server = f"{m.group(1)}:{m.group(2)}"
                srv, prt = m.group(1), int(m.group(2))
                t0 = time.time()
                try:
                    sock = socket.create_connection((srv, prt), timeout=1.5)
                    sock.close()
                    current_lat = int((time.time() - t0) * 1000)
                except Exception:
                    current_lat = 9999
    except Exception:
        pass


def make_icon_image(status, lat):
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if status == 'ready' and lat < 200:
        bg = (34, 197, 94)    # Green <200ms
    elif status == 'ready' and lat < 450:
        bg = (234, 179, 8)    # Amber <450ms
    else:
        bg = (239, 68, 68)    # Red

    draw.ellipse([3, 3, 61, 61], fill=bg)
    draw.ellipse([5, 5, 59, 59], outline=(255, 255, 255, 160), width=2)

    label = str(lat) if lat < 9000 else '?'
    try:
        font = ImageFont.truetype('arial.ttf', 22)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 2), label, fill='white', font=font)
    return img


def open_panel():
    try:
        subprocess.Popen([str(PYTHONW_PATH), str(PANEL_SCRIPT)], cwd=str(SCRIPT_ROOT))
    except Exception as e:
        print('Error opening panel:', e)


def on_exit(icon, item):
    icon.stop()
    os._exit(0)


def monitor_loop():
    not_running_counter = 0
    while True:
        time.sleep(20)
        try:
            # 检查 Antigravity 是否还在运行，若连续 3 次（60秒）未运行则自动退出托盘
            if not is_antigravity_alive():
                not_running_counter += 1
                if not_running_counter >= 3:
                    if tray_icon:
                        tray_icon.stop()
                    os._exit(0)
            else:
                not_running_counter = 0

            get_current_info()
            if tray_icon:
                lat_str = f"{current_lat}ms" if current_lat < 9000 else "超时"
                tray_icon.icon = make_icon_image(current_status, current_lat)
                tray_icon.title = f"Antigravity 代理: [{current_egress}] {lat_str} ({current_server})"
        except Exception:
            pass


def main():
    global tray_icon
    ensure_single_instance()
    get_current_info()
    img = make_icon_image(current_status, current_lat)

    menu = pystray.Menu(
        pystray.MenuItem(lambda text: f"⚡ 实时延迟: {current_lat}ms [{current_egress}]", None, enabled=False),
        pystray.MenuItem(lambda text: f"🌐 当前出口: {current_server}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🖥 打开节点控制面板 (测速 / 切换)", lambda icon, item: open_panel(), default=True),
        pystray.MenuItem("🔄 刷新延迟与状态", lambda icon, item: get_current_info()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 退出托盘", on_exit)
    )

    lat_str = f"{current_lat}ms" if current_lat < 9000 else "就绪"
    tray_icon = pystray.Icon('AntigravityTray', img, f"Antigravity 代理监控 [{current_egress}]: {lat_str}", menu=menu)
    threading.Thread(target=monitor_loop, daemon=True).start()
    tray_icon.run()


if __name__ == '__main__':
    main()
