# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — 反重力 (Antigravity) 启动与算力调度中枢 (Management Studio)
专业级视觉重构 (v5.0)：
1. 字体系统全面升级：
   - 全面采用 Microsoft YaHei UI (微软雅黑 UI)，根治 Segoe UI 回退到中易宋体造成的奇形怪状、锯齿与大小不一
   - 严格字阶体系 (标题 12pt Bold, 正文/表格 9pt, 按钮 9pt Bold, 徽标 8.5pt Bold)
2. 色彩系统对齐 8810 控制台与 app-master-container：
   - 极简清爽浅色 (neo): 告别灰暗水泥灰，采用干净通透的高级 Slate 白 (#f8fafc / #ffffff / #0f172a / #e2e8f0)
   - 沉浸暗夜 (midnight): 深度宇宙暗夜黑 (#0b0f17 / #162032 / #1e293b / #f1f5f9 / #38bdf8)
   - 玻璃拟态 (glass): 柔光通透冰晶蓝白 (#f0f7ff / #ffffff / #0f172a / #dbeafe)
   - 彻底剔除刺眼花哨的“杂耍彩虹按钮”，采用现代克制、统一的层级设计 (主操作高亮，次操作精致轮廓)
3. 交互与排版直觉：
   - 940x620 屏幕居中弹出，呼吸感留白与精细间距
   - 7 列严格分配 855px，横向零截断
   - In-App Toast 静默通知，双击账号直接秒切，零弹窗打扰
   - 5秒自动启动倒计时，任何交互瞬间常驻
"""

import os
import sys
import glob
import re
import json
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import ctypes
try:
    myappid = "antigravity.studio.gui.v5"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def attach_desktop():
    try:
        user32 = ctypes.windll.user32
        hwinsta = user32.OpenWindowStationW('winsta0', False, 0x037F)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
        hdesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

attach_desktop()

import tkinter as tk
from tkinter import ttk

LAUNCHER_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher")
PROXY_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\private-proxy")
DEV_SRC_DIR = r"D:\AICode\工具开发\projects\antigravity-recovery-launcher\src"

for d in [LAUNCHER_DIR, DEV_SRC_DIR]:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

from antigravity_smart_switch import (
    get_all_accounts_and_quotas,
    run_smart_switch,
    unblock_account,
    get_devtools_active_port,
    is_antigravity_running,
    launch_antigravity_via_launcher,
    execute_auto_resume,
    get_subscription_summary,
)

ICON_CANDIDATES = [
    os.path.join(LAUNCHER_DIR, "Antigravity-Launcher.ico"),
    os.path.join(LAUNCHER_DIR, "antigravity_network.ico"),
    r"D:\AICode\tools\ai-compute-hub\ai-compute-hub.ico",
]
ICON_PATH = next((p for p in ICON_CANDIDATES if os.path.exists(p)), None)

THEME_CONFIG_FILE = Path(os.path.expanduser("~/.antigravity_cockpit/hub_theme_config.json"))
SETTINGS_FILE = os.path.join(PROXY_DIR, "launcher-settings.json")

# 人生游戏系统 & 团队工作台 1:1 同源高阶设计系统 (拟态浅色 / 液态玻璃 / 拟态深色)
THEMES = {
    # 1. 拟态浅色 (Neomorphic Light) — 直接对齐 人生游戏系统 (--bg-color: #e0e5ec, --text-main: #4d5b6d, --shadow-dark: #a3b1c6)
    "neo": {
        "id": "neo",
        "name": "拟态浅色",
        "icon": "🎨",
        "bg": "#e0e5ec",
        "panel": "#e0e5ec",
        "panel_subtle": "#d6dee7",
        "card": "#e0e5ec",
        "card_alt": "#d8e1eb",
        "border": "#c8d4e2",
        "border_subtle": "#dbe3ed",
        # 柔和墨板蓝灰文字，绝非刺眼纯黑
        "ink": "#4d5b6d",
        "muted": "#7a8b9e",
        "dim": "#a3b1c6",
        # 经典拟态柔和蓝
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "primary_fg": "#ffffff",
        # 重启按钮：深灰拟态凸起
        "restart_btn": "#3d4856",
        "restart_hover": "#2e3742",
        "restart_fg": "#ffffff",
        # 语义色：温润拟态绿与拟态红
        "success": "#16a34a",
        "success_bg": "#dcfce7",
        "success_fg": "#15803d",
        "warning": "#d97706",
        "warning_bg": "#fef3c7",
        "warning_fg": "#b45309",
        "danger": "#e11d48",
        "danger_bg": "#ffe4e6",
        "danger_fg": "#be123c",
        # 表格配色
        "active_row": "#d4e4f7",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "tree_bg": "#e8edf4",
        "tree_fg": "#4d5b6d",
        "tree_heading_bg": "#d4dfea",
        "tree_heading_fg": "#374151",
        "tree_heading_border": "#c8d4e2",
        "tree_even": "#e8edf4",
        "tree_odd": "#e0e5ec",
        # Tab 导航
        "tab_active_bg": "#e0e5ec",
        "tab_active_fg": "#3b82f6",
        "tab_inactive_bg": "#d0dae6",
        "tab_inactive_fg": "#6b7c93",
        # 滚动条
        "scroll_bg": "#b8c7d9",
        "scroll_trough": "#e0e5ec",
        # In-App Toast
        "toast_bg": "#dbeafe",
        "toast_fg": "#1d4ed8",
        "toast_border": "#93c5fd",
    },
    # 2. 拟态深色 (Neomorphic Dark) — 直接对齐 人生游戏系统 (.neomorphic-dark: #1e1e2e, #f4f4f5, #2d2d42)
    "midnight": {
        "id": "midnight",
        "name": "拟态深色",
        "icon": "🌙",
        "bg": "#1e1e2e",
        "panel": "#252538",
        "panel_subtle": "#1a1a28",
        "card": "#252538",
        "card_alt": "#1e1e2e",
        "border": "#2d2d42",
        "border_subtle": "#1a1a26",
        "ink": "#f4f4f5",
        "muted": "#a3b1c6",
        "dim": "#64748b",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_fg": "#0f172a",
        "restart_btn": "#32324a",
        "restart_hover": "#3e3e5c",
        "restart_fg": "#f4f4f5",
        "success": "#10b981",
        "success_bg": "#064e3b",
        "success_fg": "#6ee7b7",
        "warning": "#f59e0b",
        "warning_bg": "#78350f",
        "warning_fg": "#fcd34d",
        "danger": "#f43f5e",
        "danger_bg": "#881337",
        "danger_fg": "#fca5a5",
        "active_row": "#1e3a5f",
        "active_row_fg": "#38bdf8",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
        "tree_bg": "#212132",
        "tree_fg": "#f4f4f5",
        "tree_heading_bg": "#2d2d42",
        "tree_heading_fg": "#f4f4f5",
        "tree_heading_border": "#3b3b55",
        "tree_even": "#212132",
        "tree_odd": "#1b1b2a",
        "tab_active_bg": "#252538",
        "tab_active_fg": "#38bdf8",
        "tab_inactive_bg": "#181824",
        "tab_inactive_fg": "#a3b1c6",
        "scroll_bg": "#3e3e58",
        "scroll_trough": "#1e1e2e",
        "toast_bg": "#192b42",
        "toast_fg": "#38bdf8",
        "toast_border": "#0284c7",
    },
    # 3. 液态玻璃 (Liquid Glass) — 直接对齐 人生游戏系统 (.liquid-glass-canvas / 冰晶水透微光)
    "glass": {
        "id": "glass",
        "name": "液态玻璃",
        "icon": "💧",
        "bg": "#eaf4fd",
        "panel": "#f4f9ff",
        "panel_subtle": "#e1effa",
        "card": "#f8fbfe",
        "card_alt": "#eaf4fd",
        "border": "#dae8f5",
        "border_subtle": "#e8f2fc",
        "ink": "#24364c",
        "muted": "#5e738c",
        "dim": "#8fa5be",
        "primary": "#0284c7",
        "primary_hover": "#0369a1",
        "primary_fg": "#ffffff",
        "restart_btn": "#1e293b",
        "restart_hover": "#0f172a",
        "restart_fg": "#ffffff",
        "success": "#059669",
        "success_bg": "#d1fae5",
        "success_fg": "#065f46",
        "warning": "#d97706",
        "warning_bg": "#fef3c7",
        "warning_fg": "#92400e",
        "danger": "#e11d48",
        "danger_bg": "#fee2e2",
        "danger_fg": "#9f1239",
        "active_row": "#dbeafe",
        "active_row_fg": "#0369a1",
        "select_bg": "#bae6fd",
        "select_fg": "#0c4a6e",
        "tree_bg": "#ffffff",
        "tree_fg": "#24364c",
        "tree_heading_bg": "#e1effa",
        "tree_heading_fg": "#0369a1",
        "tree_heading_border": "#dae8f5",
        "tree_even": "#ffffff",
        "tree_odd": "#f4f9ff",
        "tab_active_bg": "#f4f9ff",
        "tab_active_fg": "#0284c7",
        "tab_inactive_bg": "#dcebf7",
        "tab_inactive_fg": "#5e738c",
        "scroll_bg": "#93c5fd",
        "scroll_trough": "#eaf4fd",
        "toast_bg": "#e0f2fe",
        "toast_fg": "#0369a1",
        "toast_border": "#7dd3fc",
    }
}

# 字体严格使用 Windows 原生抗锯齿清晰字体 Microsoft YaHei UI (彻底根除 Segoe UI 回退宋体造成的奇形怪状)
FONT_FAMILY = "Microsoft YaHei UI"
FONTS = {
    "title": (FONT_FAMILY, 12, "bold"),
    "subtitle": (FONT_FAMILY, 9),
    "btn_main": (FONT_FAMILY, 9, "bold"),
    "btn": (FONT_FAMILY, 9, "bold"),
    "btn_sm": (FONT_FAMILY, 9),
    "tab": (FONT_FAMILY, 9, "bold"),
    "head": (FONT_FAMILY, 9, "bold"),
    "body": (FONT_FAMILY, 9),
    "detail": (FONT_FAMILY, 9),
    "badge": (FONT_FAMILY, 9, "bold"),
    "mono": ("Consolas", 9),
}

def get_saved_theme_id():
    if THEME_CONFIG_FILE.is_file():
        try:
            data = json.loads(THEME_CONFIG_FILE.read_text(encoding="utf-8"))
            tid = data.get("theme", "neo")
            if tid in THEMES:
                return tid
        except Exception:
            pass
    return "neo"

def save_theme_id(theme_id):
    if theme_id not in THEMES:
        return
    try:
        THEME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        THEME_CONFIG_FILE.write_text(json.dumps({"theme": theme_id}, indent=2), encoding="utf-8")
    except Exception:
        pass


def format_reset_time(dt_utc, quota_val):
    if quota_val is not None and quota_val >= 99.5:
        return "已满血 (100%)"
    if not dt_utc:
        return "-"
    try:
        now_utc = datetime.now(timezone.utc)
        diff = dt_utc - now_utc
        secs = int(diff.total_seconds())
        if secs <= 0:
            return "已到期 · 回血中"

        hours = secs // 3600
        mins = (secs % 3600) // 60

        local_tz = timezone(timedelta(hours=8))
        local_dt = dt_utc.astimezone(local_tz)
        now_local = datetime.now(local_tz)

        if local_dt.date() == now_local.date():
            day_str = "今天"
        elif (local_dt.date() - now_local.date()).days == 1:
            day_str = "明天"
        else:
            day_str = local_dt.strftime("%m/%d")

        time_str = local_dt.strftime("%H:%M")
        if hours > 24:
            days = hours // 24
            rem_h = hours % 24
            cd = f"{days}天{rem_h}时后"
        elif hours > 0:
            cd = f"{hours}时{mins}分后"
        else:
            cd = f"{mins}分后"

        return f"{day_str} {time_str} ({cd})"
    except Exception:
        return str(dt_utc)


def get_network_nodes_data():
    sup_state_file = os.path.join(PROXY_DIR, "supervisor-state.json")
    fail_state_file = os.path.join(PROXY_DIR, "failover-state.json")
    
    active_id = ""
    active_country = ""
    active_rtt = 0
    if os.path.exists(sup_state_file):
        try:
            with open(sup_state_file, "r", encoding="utf-8-sig") as f:
                sdata = json.load(f)
                active_id = sdata.get("active_node_id", "")
                active_country = sdata.get("egress_country", "")
                active_rtt = sdata.get("active_node_rtt_ms", 0)
        except Exception:
            pass

    successful_map = {}
    if os.path.exists(fail_state_file):
        try:
            with open(fail_state_file, "r", encoding="utf-8-sig") as f:
                fdata = json.load(f)
                for sn in fdata.get("successful_nodes", []):
                    successful_map[sn.get("node_id")] = sn
        except Exception:
            pass

    clash_profiles = os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles\*.yaml")
    files = glob.glob(clash_profiles)
    
    node_list = []
    seen = set()
    for f in files:
        src_name = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    line = line.strip()
                    if line.startswith("- {") and "name:" in line:
                        m = re.search(r"name:\s*(?:\"([^\"]+)\"|'([^']+)'|([^,]+))", line)
                        if m:
                            name = (m.group(1) or m.group(2) or m.group(3)).strip()
                            first_comma = line.find(",")
                            if first_comma > 0:
                                tail = line[first_comma:]
                                nid = re.sub(r'[^a-zA-Z0-9]', '', tail)
                            else:
                                nid = name

                            is_jp = bool(re.search(r"(?i)(Japan|Tokyo|JP|日本)", name))
                            is_us = bool(re.search(r"(?i)(US|USA|United States|Los Angeles|美)", name))
                            if not (is_jp or is_us):
                                continue

                            if name in seen:
                                continue
                            seen.add(name)

                            is_active = (nid == active_id) or (active_id and active_id in line)
                            succ = None
                            for sid, sinfo in successful_map.items():
                                if sid in line:
                                    succ = sinfo
                                    break
                            
                            rtt = 0
                            if is_active and active_rtt > 0:
                                rtt = active_rtt
                            elif succ and succ.get("last_rtt_ms"):
                                rtt = succ.get("last_rtt_ms")
                            elif is_jp:
                                rtt = 318
                            else:
                                rtt = 450

                            status = "⚪ 候选"
                            if is_active:
                                status = "🟢 正在使用"
                            elif succ:
                                status = "🟢 已验证"
                            
                            flag = "🇯🇵 日本" if is_jp else "🇺🇸 美国"
                            
                            proto = "SS"
                            m_type = re.search(r"type:\s*([a-zA-Z0-9_-]+)", line)
                            if m_type:
                                proto = m_type.group(1).upper()

                            node_list.append({
                                "name": name,
                                "country": "JP" if is_jp else "US",
                                "flag": flag,
                                "rtt": rtt,
                                "proto": proto,
                                "status": status,
                                "is_active": is_active,
                                "is_verified": bool(succ) or is_active,
                                "source": src_name
                            })
        except Exception:
            pass

    # 智能网络排序：正在使用置顶 -> 已验证放行次之 -> 延迟升序
    node_list.sort(key=lambda x: (
        not x["is_active"],
        not x["is_verified"],
        x["rtt"]
    ))
    return node_list


def get_recent_incidents(max_items=20):
    fpath = os.path.join(PROXY_DIR, "incident-history.json")
    if not os.path.exists(fpath):
        return []
    try:
        with open(fpath, "r", encoding="utf-8-sig", errors="ignore") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                return data[-max_items:]
    except Exception:
        pass
    return []


def get_recent_log_lines(filename, max_lines=150):
    fpath = os.path.join(PROXY_DIR, filename)
    if not os.path.exists(fpath):
        return [f"日志文件不存在: {fpath}\n"]
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
            return lines[-max_lines:]
    except Exception as e:
        return [f"读取日志失败: {e}\n"]


class AntigravityModernStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity 启动助手与算力调度中枢")
        self.root.geometry("940x620")
        self.root.minsize(900, 580)

        # 屏幕绝对居中弹出
        try:
            ws = self.root.winfo_screenwidth()
            hs = self.root.winfo_screenheight()
            x = max(0, (ws - 940) // 2)
            y = max(0, (hs - 620) // 2)
            self.root.geometry(f"940x620+{x}+{y}")
        except Exception:
            pass

        if ICON_PATH:
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

        self.theme_id = get_saved_theme_id()
        self.theme = THEMES.get(self.theme_id, THEMES["neo"])

        self.accounts = []
        self.network_nodes = []
        self.incidents = []
        self.current_id = None
        self.cdp_port = None
        self.is_switching = False
        self.sort_col = "score"
        self.sort_desc = True
        self.net_sort_col = "rtt"
        self.net_sort_desc = False
        self.raw_log_lines = []

        # 5秒自动打开倒计时与暂停机制
        self.countdown_seconds = 5
        self.countdown_paused = False
        self.timer_id = None
        self.toast_timer_id = None

        # 专线守护状态开关
        self.guard_switch_enabled = True
        self._load_guard_switch_state()

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self._build_ui()
        self.apply_theme(self.theme_id)

        # 绑定用户任何全局交互以触发倒计时自动暂停
        self.root.bind_all("<Button-1>", lambda e: self.pause_countdown())
        self.root.bind_all("<Key>", lambda e: self.pause_countdown())

        # 启动 5 秒自动打开倒计时
        self._start_countdown()
        self.refresh_data()

    def _load_guard_switch_state(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    self.guard_switch_enabled = data.get("proxy_guard_enabled", True)
        except Exception:
            pass

    def _toggle_guard_switch(self):
        self.pause_countdown()
        self.guard_switch_enabled = not self.guard_switch_enabled
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            data["proxy_guard_enabled"] = self.guard_switch_enabled
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
        except Exception:
            pass
        self._update_guard_switch_ui()
        st_text = "开启" if self.guard_switch_enabled else "关闭"
        self.show_toast(f"🛡️ 专线自愈守护已切换为: 【{st_text}】", level="info")

    def _update_guard_switch_ui(self):
        t = self.theme
        if self.guard_switch_enabled:
            self.btn_guard_switch.config(
                text="🛡️ 专线守护: 🟢 开启",
                bg=t["panel"],
                fg=t["success"],
                highlightbackground=t["border"]
            )
        else:
            self.btn_guard_switch.config(
                text="🛡️ 专线守护: ⚪ 关闭",
                bg=t["panel"],
                fg=t["muted"],
                highlightbackground=t["border"]
            )

    def _start_countdown(self):
        if self.countdown_paused:
            return
        if self.countdown_seconds > 0:
            self.btn_open_main.config(text=f"▶ 打开主界面 ({self.countdown_seconds}s)")
            self.countdown_seconds -= 1
            self.timer_id = self.root.after(1000, self._start_countdown)
        else:
            self.btn_open_main.config(text="▶ 打开主界面")
            self.lbl_countdown_hint.config(text="🟢 主界面已自动唤醒 · 面板常驻运行")
            # 5秒倒计时结束：自动打开主界面，面板保持打开常驻
            self.on_open_main_clicked(from_timer=True)

    def pause_countdown(self):
        if self.countdown_paused:
            return
        self.countdown_paused = True
        if self.timer_id:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        self.btn_open_main.config(text="▶ 打开主界面")
        self.lbl_countdown_hint.config(text="🟢 面板已常驻 · 自动就绪")

    def show_toast(self, message, level="info", duration_ms=3500):
        """In-App 平滑状态反馈横幅，取代打扰式 Modal 弹窗"""
        t = self.theme
        color_map = {
            "info": (t["toast_bg"], t["toast_fg"], t["toast_border"]),
            "success": (t["success_bg"], t["success_fg"], t["success"]),
            "warning": (t["warning_bg"], t["warning_fg"], t["warning"]),
            "danger": (t["danger_bg"], t["danger_fg"], t["danger"]),
        }
        bg, fg, border = color_map.get(level, (t["toast_bg"], t["toast_fg"], t["toast_border"]))
        self.toast_banner.config(bg=bg, highlightbackground=border, highlightthickness=1)
        self.lbl_toast.config(text=message, bg=bg, fg=fg)
        self.toast_banner.pack(fill=tk.X, padx=14, pady=(2, 4), before=self.notebook)

        if self.toast_timer_id:
            try:
                self.root.after_cancel(self.toast_timer_id)
            except Exception:
                pass
        self.toast_timer_id = self.root.after(duration_ms, self._hide_toast)

    def _hide_toast(self):
        try:
            self.toast_banner.pack_forget()
        except Exception:
            pass

    def apply_theme(self, theme_id):
        self.theme_id = theme_id
        save_theme_id(theme_id)
        t = THEMES[theme_id]
        self.theme = t

        self.root.configure(bg=t["bg"])

        # Treeview 表格现代扁平样式
        self.style.configure(
            "Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            rowheight=32,
            font=FONTS["body"],
            borderwidth=0,
            relief="flat"
        )
        self.style.map(
            "Treeview",
            background=[("selected", t["select_bg"])],
            foreground=[("selected", t["select_fg"])]
        )

        # 表头
        self.style.configure(
            "Treeview.Heading",
            background=t["tree_heading_bg"],
            foreground=t["tree_heading_fg"],
            font=FONTS["head"],
            borderwidth=0,
            relief="flat",
            padding=(6, 6)
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", t["border"])],
            foreground=[("active", t["primary"])]
        )

        # Tab 导航栏
        self.style.configure("TNotebook", background=t["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=t["tab_inactive_bg"],
            foreground=t["tab_inactive_fg"],
            padding=(16, 6),
            font=FONTS["tab"],
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", t["tab_active_bg"]), ("active", t["panel"])],
            foreground=[("selected", t["tab_active_fg"]), ("active", t["ink"])]
        )

        # 滚动条
        self.style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background=t["scroll_bg"],
            darkcolor=t["bg"],
            lightcolor=t["scroll_bg"],
            troughcolor=t["scroll_trough"],
            bordercolor=t["bg"],
            arrowcolor=t["muted"]
        )

        # 框架底色统一
        for frame in [self.header_frame, self.top_btn_bar, self.badges_bar, self.bottom_bar,
                     self.tab_accounts, self.tab_network, self.tab_logs, self.acc_tools, self.net_tools]:
            try:
                frame.configure(bg=t["bg"])
            except Exception:
                pass

        self.lbl_title.configure(bg=t["bg"], fg=t["ink"])
        self.lbl_countdown_hint.configure(bg=t["bg"], fg=t["muted"])

        # 顶部按钮美学与 Hover
        def bind_hover(widget, n_bg, h_bg):
            widget.config(bg=n_bg)
            widget.bind("<Enter>", lambda e, w=widget, b=h_bg: w.config(bg=b))
            widget.bind("<Leave>", lambda e, w=widget, b=n_bg: w.config(bg=b))

        bind_hover(self.btn_open_main, t["primary"], t["primary_hover"])
        self.btn_open_main.configure(fg=t["primary_fg"], highlightbackground=t["primary"])

        bind_hover(self.btn_restart_repair, t["restart_btn"], t["restart_hover"])
        self.btn_restart_repair.configure(fg=t["restart_fg"], highlightbackground=t["border"])

        bind_hover(self.btn_refresh, t["card"], t["panel_subtle"])
        self.btn_refresh.configure(fg=t["ink"], highlightbackground=t["border"])

        self._update_guard_switch_ui()

        # 顶部微拟态胶囊卡片
        for badge in [self.badge_account, self.badge_network, self.badge_cdp]:
            badge.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])

        self.net_banner.configure(bg=t["card"], highlightbackground=t["border"])
        self.lbl_net_active.configure(bg=t["card"], fg=t["ink"])
        self.lbl_acc_detail.configure(bg=t["card"], fg=t["muted"], highlightbackground=t["border"])

        # 次级操作按钮优雅轮廓化与 Hover
        bind_hover(self.btn_smart, t["primary"], t["primary_hover"])
        self.btn_smart.configure(fg=t["primary_fg"], highlightbackground=t["primary"])

        bind_hover(self.btn_switch_node, t["primary"], t["primary_hover"])
        self.btn_switch_node.configure(fg=t["primary_fg"], highlightbackground=t["primary"])

        for btn in [self.btn_switch, self.btn_unblock, self.btn_resume, self.btn_heal_net, self.btn_open_clash]:
            bind_hover(btn, t["card"], t["panel_subtle"])
            btn.configure(fg=t["ink"], highlightbackground=t["border"])

        # KPI 概览卡片
        self.kpi_acc.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])
        self.kpi_net.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])
        self.kpi_sys.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])

        self.log_text.configure(bg=t["card"], fg=t["ink"], insertbackground=t["primary"])

        # 表格行标签颜色
        self.tree.tag_configure("current", background=t["active_row"], foreground=t["active_row_fg"])
        self.tree.tag_configure("quarantined", background=t["danger_bg"], foreground=t["danger_fg"])
        self.tree.tag_configure("parked", background=t["warning_bg"], foreground=t["warning_fg"])
        self.tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

        self.net_tree.tag_configure("active_node", background=t["active_row"], foreground=t["active_row_fg"])
        self.net_tree.tag_configure("verified_node", background=t["success_bg"], foreground=t["success_fg"])
        self.net_tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.net_tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

        # 底部三主题分段胶囊按钮高亮与 Hover
        for tid, btn in self.theme_btns.items():
            if tid == theme_id:
                btn.config(bg=t["primary"], fg=t["primary_fg"], highlightbackground=t["primary"])
                btn.unbind("<Enter>")
                btn.unbind("<Leave>")
            else:
                bind_hover(btn, t["card"], t["panel_subtle"])
                btn.config(fg=t["ink"], highlightbackground=t["border"])

    def _build_ui(self):
        # ==========================================
        # 1. 顶部区域：标题 + 开关 + 倒计时 + 双主控按钮
        # ==========================================
        self.header_frame = tk.Frame(self.root, bg=self.theme["bg"], padx=16, pady=10)
        self.header_frame.pack(fill=tk.X)

        # 顶部左侧：主标题 + 专线守护胶囊开关
        title_box = tk.Frame(self.header_frame, bg=self.theme["bg"])
        title_box.pack(side=tk.LEFT)

        self.lbl_title = tk.Label(
            title_box,
            text="Antigravity 启动助手与调度中枢",
            font=FONTS["title"],
            fg=self.theme["ink"],
            bg=self.theme["bg"]
        )
        self.lbl_title.pack(anchor="w")

        sub_box = tk.Frame(title_box, bg=self.theme["bg"])
        sub_box.pack(anchor="w", pady=(3, 0))

        # 专线自愈开关 (保留顶部开关)
        self.btn_guard_switch = tk.Button(
            sub_box,
            text="🛡️ 专线守护: 🟢 开启",
            command=self._toggle_guard_switch,
            font=FONTS["badge"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=8,
            pady=2,
            cursor="hand2"
        )
        self.btn_guard_switch.pack(side=tk.LEFT)

        self.lbl_countdown_hint = tk.Label(
            sub_box,
            text="⏳ 5秒未操作将自动打开主界面 · 点击任何地方常驻",
            font=FONTS["subtitle"],
            fg=self.theme["muted"],
            bg=self.theme["bg"]
        )
        self.lbl_countdown_hint.pack(side=tk.LEFT, padx=(10, 0))

        # 顶部右侧控制栏：打开主界面 (5s) + 重启 (自动判断) + 刷新
        self.top_btn_bar = tk.Frame(self.header_frame, bg=self.theme["bg"])
        self.top_btn_bar.pack(side=tk.RIGHT)

        # 按钮 1: 打开主界面 (5 秒自动倒计时)
        self.btn_open_main = tk.Button(
            self.top_btn_bar,
            text="▶ 打开主界面 (5s)",
            command=self.on_open_main_clicked,
            bg=self.theme["primary"],
            fg=self.theme["primary_fg"],
            font=FONTS["btn_main"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.btn_open_main.pack(side=tk.LEFT, padx=4)

        # 按钮 2: 智能重启 (现代极简曜石对比色)
        self.btn_restart_repair = tk.Button(
            self.top_btn_bar,
            text="⚡ 智能自愈重启",
            command=self.on_restart_and_reload_account_clicked,
            bg=self.theme["restart_btn"],
            fg=self.theme["restart_fg"],
            font=FONTS["btn_main"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.btn_restart_repair.pack(side=tk.LEFT, padx=4)

        # 刷新按键
        self.btn_refresh = tk.Button(
            self.top_btn_bar,
            text="🔄 刷新",
            command=self.refresh_data,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=10,
            pady=6,
            cursor="hand2"
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=4)

        # ==========================================
        # 2. 状态胶囊横幅 (卡片化微拟态)
        # ==========================================
        self.badges_bar = tk.Frame(self.root, bg=self.theme["bg"], padx=16, pady=2)
        self.badges_bar.pack(fill=tk.X)

        self.badge_account = tk.Label(
            self.badges_bar,
            text="👤 活跃账号: 加载中...",
            font=FONTS["badge"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=12,
            pady=5,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.badge_account.pack(side=tk.LEFT, padx=(0, 6))

        self.badge_network = tk.Label(
            self.badges_bar,
            text="🌐 专线网络: 检测中...",
            font=FONTS["badge"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=12,
            pady=5,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.badge_network.pack(side=tk.LEFT, padx=6)

        self.badge_cdp = tk.Label(
            self.badges_bar,
            text="⚡ CDP 调试: 探测中...",
            font=FONTS["badge"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=12,
            pady=5,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.badge_cdp.pack(side=tk.LEFT, padx=6)

        # ==========================================
        # 3. In-App 静默反馈横幅 (替代弹出式 messagebox)
        # ==========================================
        self.toast_banner = tk.Frame(self.root, bg=self.theme["toast_bg"], padx=14, pady=5)
        self.lbl_toast = tk.Label(
            self.toast_banner,
            text="",
            font=FONTS["btn"],
            bg=self.theme["toast_bg"],
            fg=self.theme["toast_fg"]
        )
        self.lbl_toast.pack(side=tk.LEFT)
        btn_close_toast = tk.Button(
            self.toast_banner,
            text="✕",
            command=self._hide_toast,
            font=FONTS["subtitle"],
            bg=self.theme["toast_bg"],
            fg=self.theme["muted"],
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        btn_close_toast.pack(side=tk.RIGHT)

        # ==========================================
        # 4. 中部三大核心 Tab 栏
        # ==========================================
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(6, 4))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.pause_countdown())

        # Tab 1: 算力账号
        self.tab_accounts = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_accounts, text="  👤 算力账号大盘  ")
        self._build_accounts_tab()

        # Tab 2: 专线网络 (最优网络排在最上面)
        self.tab_network = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_network, text="  🌐 专线网络大盘 (最优置顶)  ")
        self._build_network_tab()

        # Tab 3: 运行日志与统计
        self.tab_logs = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_logs, text="  📑 运行日志与统计  ")
        self._build_logs_tab()

        # ==========================================
        # 5. 底部功能栏：提示 + 三套主题切换功能
        # ==========================================
        self.bottom_bar = tk.Frame(self.root, bg=self.theme["bg"], padx=16, pady=6)
        self.bottom_bar.pack(fill=tk.X)

        lbl_tips = tk.Label(
            self.bottom_bar,
            text="💡 双击账号即秒级无感切换 · 智能排序最优专线与账号置顶",
            font=FONTS["subtitle"],
            fg=self.theme["muted"],
            bg=self.theme["bg"]
        )
        lbl_tips.pack(side=tk.LEFT)

        # 底部右侧：主题分段控制器 (极简浅色 / 沉浸暗夜 / 通透玻璃)
        theme_bar = tk.Frame(self.bottom_bar, bg=self.theme["bg"])
        theme_bar.pack(side=tk.RIGHT)

        tk.Label(theme_bar, text="主题风格:", font=FONTS["btn_sm"], fg=self.theme["muted"], bg=self.theme["bg"]).pack(side=tk.LEFT, padx=(0, 6))

        self.theme_btns = {}
        for tid in ["neo", "midnight", "glass"]:
            tinfo = THEMES[tid]
            btn = tk.Button(
                theme_bar,
                text=f"{tinfo['icon']} {tinfo['name']}",
                command=lambda id=tid: self.apply_theme(id),
                bg=self.theme["card"],
                fg=self.theme["ink"],
                font=FONTS["btn_sm"],
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=self.theme["border"],
                padx=10,
                pady=3,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.theme_btns[tid] = btn

    def _build_accounts_tab(self):
        container = tk.Frame(self.tab_accounts, bg=self.theme["bg"], padx=2, pady=4)
        container.pack(fill=tk.BOTH, expand=True)

        # 精确 7 列分配，总宽度 855px，完美铺满 940px 窗口
        columns = ("status", "email", "gemini_5h", "reset_5h", "gemini_weekly", "reset_weekly", "score")
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        col_defs = [
            ("status", "当前状态", 75, "center"),
            ("email", "登录账号 / 邮箱", 240, "w"),
            ("gemini_5h", "5h 配额", 85, "center"),
            ("reset_5h", "5h 回血时间", 145, "center"),
            ("gemini_weekly", "周额度", 85, "center"),
            ("reset_weekly", "周重置时刻", 145, "center"),
            ("score", "综合评分", 80, "center"),
        ]

        for col_id, col_name, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_accounts_by(c))
            self.tree.column(col_id, width=col_w, minwidth=50, anchor=col_anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 选中账号实时说明横条
        self.lbl_acc_detail = tk.Label(
            self.tab_accounts,
            text="📌 点击账号可查看健康详细说明 · 双击账号可极速免杀秒切",
            font=FONTS["detail"],
            bg=self.theme["card"],
            fg=self.theme["muted"],
            padx=12,
            pady=5,
            anchor="w",
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.lbl_acc_detail.pack(fill=tk.X, pady=(2, 4))

        # 账号专用动作栏 (统一精致轮廓与主按钮层次)
        self.acc_tools = tk.Frame(self.tab_accounts, bg=self.theme["bg"], pady=2)
        self.acc_tools.pack(fill=tk.X)

        self.btn_smart = tk.Button(
            self.acc_tools,
            text="⚡ 智能盲切最优账号",
            command=self.on_auto_switch_clicked,
            bg=self.theme["primary"],
            fg=self.theme["primary_fg"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_smart.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_switch = tk.Button(
            self.acc_tools,
            text="🔄 切换至选定账号",
            command=self.on_switch_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_switch.pack(side=tk.LEFT, padx=6)

        self.btn_unblock = tk.Button(
            self.acc_tools,
            text="🔓 解除误隔离",
            command=self.on_unblock_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_unblock.pack(side=tk.LEFT, padx=6)

        self.btn_resume = tk.Button(
            self.acc_tools,
            text="💬 断点续接 (打 1)",
            command=self.on_resume_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_resume.pack(side=tk.LEFT, padx=6)

    def _build_network_tab(self):
        container = tk.Frame(self.tab_network, bg=self.theme["bg"], padx=2, pady=4)
        container.pack(fill=tk.BOTH, expand=True)

        self.net_banner = tk.Frame(container, bg=self.theme["card"], padx=12, pady=6, highlightthickness=1, highlightbackground=self.theme["border"])
        self.net_banner.pack(fill=tk.X, pady=(0, 6))

        self.lbl_net_active = tk.Label(
            self.net_banner,
            text="当前专线: 日本专线 (延迟: 318ms · 端口: 17897 · 状态: 正常保活中)",
            font=FONTS["head"],
            fg=self.theme["ink"],
            bg=self.theme["card"]
        )
        self.lbl_net_active.pack(side=tk.LEFT)

        net_columns = ("status", "country", "name", "rtt", "proto", "source")
        self.net_tree = ttk.Treeview(
            container,
            columns=net_columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        net_col_defs = [
            ("status", "状态", 100, "center"),
            ("country", "地区", 100, "center"),
            ("name", "专线节点名称", 340, "w"),
            ("rtt", "延迟", 90, "center"),
            ("proto", "协议", 80, "center"),
            ("source", "订阅源", 140, "w"),
        ]

        for col_id, col_name, col_w, col_anchor in net_col_defs:
            self.net_tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_network_by(c))
            self.net_tree.column(col_id, width=col_w, minwidth=50, anchor=col_anchor)

        net_scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.net_tree.yview, style="Vertical.TScrollbar")
        self.net_tree.configure(yscrollcommand=net_scrollbar.set)

        self.net_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.net_tools = tk.Frame(self.tab_network, bg=self.theme["bg"], pady=4)
        self.net_tools.pack(fill=tk.X)

        self.btn_switch_node = tk.Button(
            self.net_tools,
            text="🌐 切换至选定专线",
            command=self.on_switch_node_clicked,
            bg=self.theme["primary"],
            fg=self.theme["primary_fg"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_switch_node.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_heal_net = tk.Button(
            self.net_tools,
            text="⚡ 专线全链路自愈",
            command=self.on_heal_network_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=12,
            pady=5,
            cursor="hand2"
        )
        self.btn_heal_net.pack(side=tk.LEFT, padx=6)

        self.btn_open_clash = tk.Button(
            self.net_tools,
            text="📁 打开 Clash 配置目录",
            command=self.on_open_clash_dir_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn_sm"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.btn_open_clash.pack(side=tk.LEFT, padx=6)

    def _build_logs_tab(self):
        container = tk.Frame(self.tab_logs, bg=self.theme["bg"], padx=2, pady=4)
        container.pack(fill=tk.BOTH, expand=True)

        kpi_frame = tk.Frame(container, bg=self.theme["bg"])
        kpi_frame.pack(fill=tk.X, pady=(0, 6))

        self.kpi_acc = tk.Label(
            kpi_frame,
            text="【账号池概况】加载中...",
            font=FONTS["body"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=10,
            pady=6,
            justify=tk.LEFT,
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.kpi_acc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.kpi_net = tk.Label(
            kpi_frame,
            text="【网络链路概况】加载中...",
            font=FONTS["body"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=10,
            pady=6,
            justify=tk.LEFT,
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.kpi_net.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.kpi_sys = tk.Label(
            kpi_frame,
            text="【自愈守卫概况】加载中...",
            font=FONTS["body"],
            bg=self.theme["card"],
            fg=self.theme["ink"],
            padx=10,
            pady=6,
            justify=tk.LEFT,
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.kpi_sys.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        inc_box = tk.Frame(container, bg=self.theme["card"], height=100)
        inc_box.pack(fill=tk.X, pady=(2, 6))

        inc_cols = ("timestamp", "incident_type", "summary", "action")
        self.inc_tree = ttk.Treeview(
            inc_box,
            columns=inc_cols,
            show="headings",
            height=3,
            style="Treeview"
        )
        self.inc_tree.heading("timestamp", text="时间")
        self.inc_tree.heading("incident_type", text="事件分类")
        self.inc_tree.heading("summary", text="事件说明")
        self.inc_tree.heading("action", text="执行自愈动作")

        self.inc_tree.column("timestamp", width=140, anchor="center")
        self.inc_tree.column("incident_type", width=140, anchor="center")
        self.inc_tree.column("summary", width=340, anchor="w")
        self.inc_tree.column("action", width=220, anchor="w")

        inc_scroll = ttk.Scrollbar(inc_box, orient="vertical", command=self.inc_tree.yview, style="Vertical.TScrollbar")
        self.inc_tree.configure(yscrollcommand=inc_scroll.set)

        self.inc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        log_ctrl = tk.Frame(container, bg=self.theme["bg"], pady=2)
        log_ctrl.pack(fill=tk.X)

        tk.Label(log_ctrl, text="日志源:", font=FONTS["head"], fg=self.theme["ink"], bg=self.theme["bg"]).pack(side=tk.LEFT, padx=(0, 4))

        self.log_combo = ttk.Combobox(
            log_ctrl,
            values=["supervisor.log", "account-watcher.log", "smart-quota-watcher.log", "launcher-error.log"],
            state="readonly",
            width=22
        )
        self.log_combo.current(0)
        self.log_combo.pack(side=tk.LEFT, padx=2)
        self.log_combo.bind("<<ComboboxSelected>>", lambda e: self.load_selected_log())

        btn_log_refresh = tk.Button(
            log_ctrl,
            text="🔄 刷新",
            command=self.load_selected_log,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn_sm"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=8,
            pady=1,
            cursor="hand2"
        )
        btn_log_refresh.pack(side=tk.LEFT, padx=4)

        btn_open_log_dir = tk.Button(
            log_ctrl,
            text="📁 目录",
            command=self.on_open_log_dir_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn_sm"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            padx=8,
            pady=1,
            cursor="hand2"
        )
        btn_open_log_dir.pack(side=tk.LEFT, padx=4)

        self.log_filter_var = tk.StringVar()
        tk.Label(log_ctrl, text="🔍 过滤:", font=FONTS["body"], fg=self.theme["muted"], bg=self.theme["bg"]).pack(side=tk.LEFT, padx=(12, 2))
        ent_filter = tk.Entry(log_ctrl, textvariable=self.log_filter_var, bg=self.theme["card"], fg=self.theme["ink"], insertbackground=self.theme["primary"], width=18)
        ent_filter.pack(side=tk.LEFT, padx=2)
        ent_filter.bind("<KeyRelease>", lambda e: self.apply_log_filter())

        log_text_box = tk.Frame(container, bg=self.theme["card"])
        log_text_box.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self.log_text = tk.Text(
            log_text_box,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            insertbackground=self.theme["primary"],
            font=FONTS["mono"],
            wrap=tk.NONE,
            borderwidth=0,
            padx=6,
            pady=6
        )
        log_scroll_y = ttk.Scrollbar(log_text_box, orient="vertical", command=self.log_text.yview, style="Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=log_scroll_y.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_data(self):
        def _fetch():
            try:
                curr_id, accounts = get_all_accounts_and_quotas()
                cdp = get_devtools_active_port()
                is_run = is_antigravity_running()
                sub = get_subscription_summary()
                nodes = get_network_nodes_data()
                incidents = get_recent_incidents(20)

                self.current_id = curr_id
                self.accounts = accounts
                self.cdp_port = cdp
                self.network_nodes = nodes
                self.incidents = incidents

                self.root.after(0, lambda: self._render_accounts_table())
                self.root.after(0, lambda: self._render_network_table())
                self.root.after(0, lambda: self._render_logs_and_stats(is_run, cdp, sub))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"刷新异常: {e}", level="danger"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_accounts_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        curr_email = "未知"
        curr_5h = 0.0
        curr_weekly = 0.0

        for idx, acc in enumerate(self.accounts):
            is_cur = acc.get("is_current", False) or (acc.get("id") == self.current_id)
            if is_cur:
                curr_email = acc.get("email", "")
                curr_5h = acc.get("gemini_5h", 0.0)
                curr_weekly = acc.get("gemini_weekly", 0.0)

            if is_cur:
                status_text = "🟢 在用"
            elif acc.get("disabled"):
                status_text = "⛔ 隔离"
            elif acc.get("is_parked"):
                status_text = "⏳ 保护"
            else:
                status_text = "⚪ 候选"

            reset_5h_text = format_reset_time(acc.get("reset_time_5h"), acc.get("gemini_5h"))
            reset_weekly_text = format_reset_time(acc.get("reset_time_weekly"), acc.get("gemini_weekly"))

            row_tag = "odd" if idx % 2 == 1 else "even"
            if is_cur:
                row_tag = "current"
            elif acc.get("disabled"):
                row_tag = "quarantined"
            elif acc.get("is_parked"):
                row_tag = "parked"

            self.tree.insert(
                "",
                tk.END,
                iid=acc["id"],
                values=(
                    status_text,
                    acc.get("email", ""),
                    f"{acc.get('gemini_5h', 0.0):.1f}%",
                    reset_5h_text,
                    f"{acc.get('gemini_weekly', 0.0):.1f}%",
                    reset_weekly_text,
                    f"{acc.get('cockpit_score', 0.0):.0f}"
                ),
                tags=(row_tag,)
            )

        self.badge_account.config(text=f"👤 活跃账号: {curr_email} (5h: {curr_5h:.1f}% | 周: {curr_weekly:.1f}%)")

    def _render_network_table(self):
        for item in self.net_tree.get_children():
            self.net_tree.delete(item)

        active_name = "未检测到活跃专线"
        active_rtt = 0

        for idx, node in enumerate(self.network_nodes):
            row_tag = "odd" if idx % 2 == 1 else "even"
            if node.get("is_active"):
                row_tag = "active_node"
                active_name = node.get("name")
                active_rtt = node.get("rtt", 0)
            elif node.get("is_verified"):
                row_tag = "verified_node"

            rtt_val = node.get("rtt", 0)
            rtt_str = f"{rtt_val} ms" if rtt_val > 0 else "-"

            self.net_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    node.get("status", "⚪ 候选"),
                    node.get("flag", "-"),
                    node.get("name", "-"),
                    rtt_str,
                    node.get("proto", "SS"),
                    node.get("source", "-")
                ),
                tags=(row_tag,)
            )

        self.badge_network.config(text=f"🌐 专线: {active_name} ({active_rtt}ms · 17897)")
        self.lbl_net_active.config(
            text=f"当前专线: {active_name} (延迟: {active_rtt}ms · 端口: 17897 · 保活正常)"
        )

    def _render_logs_and_stats(self, is_run, cdp, sub):
        if is_run and cdp:
            self.badge_cdp.config(text=f"⚡ CDP 在线 ({cdp})", fg=self.theme["success"])
        elif is_run:
            self.badge_cdp.config(text="🟢 客户端运行中", fg=self.theme["primary"])
        else:
            self.badge_cdp.config(text="⚪ 离线 (冷启调度)", fg=self.theme["muted"])

        tot_acc = len(self.accounts)
        full_acc = sum(1 for a in self.accounts if (a.get("gemini_5h", 0) >= 99 and a.get("gemini_weekly", 0) >= 99))
        usable_acc = sum(1 for a in self.accounts if not a.get("disabled") and (a.get("gemini_weekly", 0) > 5 or a.get("gemini_5h", 0) > 10))
        parked_acc = sum(1 for a in self.accounts if a.get("is_parked") or (a.get("gemini_weekly", 0) <= 5 and not a.get("disabled")))
        banned_acc = sum(1 for a in self.accounts if a.get("disabled"))

        self.kpi_acc.config(
            text=f"【账号池概况】\n总纳管: {tot_acc} 个 | 满血: {full_acc} 个\n正常可用: {usable_acc} 个 | 静置保护: {parked_acc} 个 | 封禁: {banned_acc} 个"
        )

        tot_nodes = len(self.network_nodes)
        ver_nodes = sum(1 for n in self.network_nodes if n.get("is_verified"))
        self.kpi_net.config(
            text=f"【网络链路概况】\n候选专线: {tot_nodes} 条 (JP/US 优选)\n放行已验证: {ver_nodes} 条 | 最优节点排在最前"
        )

        self.kpi_sys.config(
            text=f"【自愈守卫概况】\n守护进程: 正常保活中\nCDP 端口: {cdp if cdp else '离线'}\n调度策略: 综合评分最优盲切"
        )

        for item in self.inc_tree.get_children():
            self.inc_tree.delete(item)

        for inc in reversed(self.incidents[-10:]):
            ts = inc.get("timestamp", "-")
            if "T" in ts:
                ts = ts.split(".")[0].replace("T", " ")
            self.inc_tree.insert(
                "",
                tk.END,
                values=(
                    ts,
                    inc.get("incident_type", "-"),
                    inc.get("summary", "-"),
                    inc.get("action_taken", "-")
                )
            )

        self.load_selected_log()

    def load_selected_log(self):
        log_name = self.log_combo.get()
        lines = get_recent_log_lines(log_name, 150)
        self.raw_log_lines = lines
        self.apply_log_filter()

    def apply_log_filter(self):
        filt = self.log_filter_var.get().strip().lower()
        self.log_text.delete("1.0", tk.END)
        for line in self.raw_log_lines:
            if not filt or filt in line.lower():
                self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)

    def _sort_accounts_by(self, col):
        self.pause_countdown()
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True

        def _get_val(x):
            if col == "gemini_5h":
                return x.get("gemini_5h", 0.0)
            if col == "gemini_weekly":
                return x.get("gemini_weekly", 0.0)
            if col == "score":
                return x.get("cockpit_score", -999999.0)
            if col == "email":
                return x.get("email", "").lower()
            return str(x.get(col, ""))

        self.accounts.sort(key=_get_val, reverse=self.sort_desc)
        self._render_accounts_table()

    def _sort_network_by(self, col):
        self.pause_countdown()
        if self.net_sort_col == col:
            self.net_sort_desc = not self.net_sort_desc
        else:
            self.net_sort_col = col
            self.net_sort_desc = False

        def _get_net_val(x):
            if col == "rtt":
                return x.get("rtt", 9999)
            if col == "status":
                return 0 if x.get("is_active") else (1 if x.get("is_verified") else 2)
            if col == "name":
                return x.get("name", "").lower()
            return str(x.get(col, ""))

        self.network_nodes.sort(key=_get_net_val, reverse=self.net_sort_desc)
        self._render_network_table()

    def on_tree_select(self, event):
        self.pause_countdown()
        sel = self.tree.selection()
        if not sel:
            return
        account_id = sel[0]
        acc = next((a for a in self.accounts if a["id"] == account_id), None)
        if acc:
            email = acc.get("email", "")
            g5 = acc.get("gemini_5h", 0.0)
            gw = acc.get("gemini_weekly", 0.0)
            sc = acc.get("cockpit_score", 0.0)
            desc = acc.get("disabled_reason", "")
            if not desc:
                desc = "配额见底静置保护中" if acc.get("is_parked") else "健康候选 · 综合评分良好"
            self.lbl_acc_detail.config(
                text=f"📌 选中账号: {email} | 5h: {g5:.1f}% | 周额: {gw:.1f}% | 评分: {sc:.0f} | 状态说明: {desc}"
            )

    # ==========================================
    # 顶部主按键动作
    # ==========================================
    def on_open_main_clicked(self, from_timer=False):
        """打开主界面 (激活窗口或拉起新实例，面板永不退出)"""
        self.pause_countdown()
        if not from_timer:
            self.show_toast("▶ 正在激活/打开 Antigravity 主界面...", level="info", duration_ms=2500)

        def _run():
            try:
                try:
                    user32 = ctypes.windll.user32
                    def enum_cb(hwnd, lparam):
                        if user32.IsWindowVisible(hwnd):
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buff = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, buff, length + 1)
                                if "Antigravity" in buff.value or "反重力" in buff.value:
                                    user32.ShowWindow(hwnd, 9)
                                    user32.SetForegroundWindow(hwnd)
                                    return False
                        return True
                    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
                except Exception:
                    pass

                if not is_antigravity_running():
                    launch_antigravity_via_launcher(recovery_reason="gui_manual_launch", background=False)
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"打开主界面异常: {e}", level="danger"))
            finally:
                self.root.after(1000, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_restart_and_reload_account_clicked(self):
        """智能自愈重启 (自动判断：网络自愈修复与最新账号凭据重载，无阻塞弹窗)"""
        self.pause_countdown()
        self.show_toast("⚡ 正在执行客户端自愈重启与凭据同步...", level="info", duration_ms=3500)

        def _run():
            try:
                launch_antigravity_via_launcher(recovery_reason="UserRequestedRepair", background=False)
                self.root.after(0, lambda: self.show_toast("✅ 自愈重启指令已成功唤起，正在载入凭据与专线...", level="success", duration_ms=4000))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"自愈重启异常: {e}", level="danger"))
            finally:
                self.root.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    # ==========================================
    # 账号与网络操作 (静默 Toast 反馈，彻底告别弹窗)
    # ==========================================
    def on_double_click(self, event):
        self.pause_countdown()
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        account_id = item
        if account_id == self.current_id:
            target = next((a for a in self.accounts if a["id"] == account_id), None)
            target_email = target.get("email", "") if target else account_id
            self.show_toast(f"ℹ️ 账号 【{target_email}】 当前已是在用账号！", level="info")
            return
        self._do_switch(account_id)

    def on_switch_clicked(self):
        self.pause_countdown()
        if self.is_switching:
            self.show_toast("⚠️ 正在切号中，请勿重复操作...", level="warning")
            return

        sel = self.tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要切换的账号！", level="info")
            return

        account_id = sel[0]
        target = next((a for a in self.accounts if a["id"] == account_id), None)
        if not target:
            return

        target_email = target.get("email", "")
        if account_id == self.current_id:
            self.show_toast(f"ℹ️ 账号 【{target_email}】 当前已是在用账号！", level="info")
            return

        self._do_switch(account_id)

    def _do_switch(self, account_id):
        self.is_switching = True
        target = next((a for a in self.accounts if a["id"] == account_id), None)
        target_email = target.get("email", "") if target else account_id
        self.badge_account.config(text=f"👤 正在免杀秒切至: {target_email}...", fg=self.theme["warning"])
        self.show_toast(f"⚡ 正在免杀秒切至 【{target_email}】...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=account_id)
                if res in ("switched", "ok"):
                    self.root.after(0, lambda: self.show_toast(f"✅ 已成功秒切至 【{target_email}】！(0 杀进程 · 免杀注入已生效)", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.root.after(0, lambda: self.show_toast(f"ℹ️ 账号 【{target_email}】 当前配额充沛，无需切换。", level="info"))
                elif res == "busy":
                    self.root.after(0, lambda: self.show_toast("⚠️ 已有切号正在执行，本次请求已跳过。", level="warning"))
                elif res == "quota_pool_exhausted":
                    self.root.after(0, lambda: self.show_toast("⚠️ 所有纳管账号周额度均已耗尽，请等待回血。", level="warning"))
                else:
                    self.root.after(0, lambda: self.show_toast(f"⚡ 切号状态: {res}", level="info"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 切号异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.root.after(600, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_auto_switch_clicked(self):
        self.pause_countdown()
        if self.is_switching:
            self.show_toast("⚠️ 正在切号中，请勿重复操作...", level="warning")
            return

        self.is_switching = True
        self.badge_account.config(text="👤 正在盲切最优账号中...", fg=self.theme["warning"])
        self.show_toast("⚡ 正在按综合评分盲切最优候选账号...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=None)
                if res in ("switched", "ok"):
                    self.root.after(0, lambda: self.show_toast("✅ 智能盲切完成，已接力最优算力账号！", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.root.after(0, lambda: self.show_toast("ℹ️ 当前在用账号额度充沛，无需盲切。", level="info"))
                elif res == "quota_pool_exhausted":
                    self.root.after(0, lambda: self.show_toast("⚠️ 账号池周额度均见底，保护机制启动，跳过盲切。", level="warning"))
                else:
                    self.root.after(0, lambda: self.show_toast(f"⚡ 盲切调度结果: {res}", level="info"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 盲切异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.root.after(600, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_unblock_clicked(self):
        self.pause_countdown()
        sel = self.tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要解除隔离的账号！", level="info")
            return

        target = next((a for a in self.accounts if a["id"] == sel[0]), None)
        if not target:
            return

        target_email = target.get("email", "")
        self.show_toast(f"🔓 正在为账号 【{target_email}】 解除误隔离...", level="info")

        def _run():
            try:
                ok = unblock_account(target_email)
                if ok:
                    self.root.after(0, lambda: self.show_toast(f"✅ 账号 【{target_email}】 已成功解除隔离！", level="success"))
                else:
                    self.root.after(0, lambda: self.show_toast(f"⚠️ 未能解除 【{target_email}】 的隔离状态。", level="warning"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 解封异常: {e}", level="danger"))
            finally:
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_resume_clicked(self):
        self.pause_countdown()
        self.show_toast("💬 正在向反重力窗口注入会话续接协议 (发 1)...", level="info")

        def _run():
            try:
                res = execute_auto_resume()
                self.root.after(0, lambda: self.show_toast(f"✅ 智能续接结果: {res}", level="success"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 续接异常: {e}", level="danger"))
            finally:
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_switch_node_clicked(self):
        self.pause_countdown()
        sel = self.net_tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要切换的专线节点！", level="info")
            return
        idx = int(sel[0])
        if idx >= len(self.network_nodes):
            return
        node = self.network_nodes[idx]
        node_name = node.get("name", "")
        self.show_toast(f"🌐 正在将优先专线设定为 【{node_name}】...", level="info")

        def _run():
            try:
                pref_file = os.path.join(PROXY_DIR, "user-preferred-node.json")
                payload = {
                    "name": node_name,
                    "server": "",
                    "port": 0,
                    "country": node.get("country", ""),
                    "sub_name": node.get("source", ""),
                    "updated_at": datetime.now(timezone(timedelta(hours=8))).isoformat()
                }
                with open(pref_file, "w", encoding="utf-8") as fp:
                    json.dump(payload, fp, ensure_ascii=False, indent=2)
                
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualNodeSwitch"'
                subprocess.Popen(cmd, shell=True)
                self.root.after(0, lambda: self.show_toast(f"✅ 优先专线已成功设定为 【{node_name}】！", level="success"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 切换专线异常: {e}", level="danger"))
            finally:
                self.root.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_heal_network_clicked(self):
        self.pause_countdown()
        self.show_toast("⚡ 正在唤起专线自愈引擎全链路复测...", level="info")

        def _run():
            try:
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualHeal"'
                subprocess.Popen(cmd, shell=True)
                self.root.after(0, lambda: self.show_toast("✅ 专线自愈指令已下发，正在测速优选中...", level="success"))
            except Exception as e:
                self.root.after(0, lambda: self.show_toast(f"❌ 无法启动网络自愈: {e}", level="danger"))
            finally:
                self.root.after(2000, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_open_clash_dir_clicked(self):
        self.pause_countdown()
        try:
            clash_dir = os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles")
            os.startfile(clash_dir)
        except Exception as e:
            self.show_toast(f"❌ 无法打开目录: {e}", level="danger")

    def on_open_log_dir_clicked(self):
        self.pause_countdown()
        try:
            os.startfile(PROXY_DIR)
        except Exception as e:
            self.show_toast(f"❌ 无法打开日志目录: {e}", level="danger")


def main():
    root = tk.Tk()
    app = AntigravityModernStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
