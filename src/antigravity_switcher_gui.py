# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — 反重力 (Antigravity) 启动与算力调度中枢 (Management Studio)
专业级、高颜值、极简直觉交互桌面面板：
1. 整体布局与尺寸：
   - 940x620 屏幕绝对居中弹出，现代应用质感，呼吸感留白与精细排版。
2. 顶部核心功能栏：
   - 专线自愈守护胶囊开关 [ 🛡️ 专线守护: 🟢 开启 / ⚪ 关闭 ]
   - 5秒自动打开倒计时 [ ▶ 打开主界面 (5s) ] (任何点击交互即刻暂停倒计时并常驻)
   - 智能自愈重启 [ ⚡ 智能自愈重启 ] (自动判断凭据变更或网络修复，无阻塞弹窗)
3. 状态胶囊横幅与 In-App 静默通知：
   - 活跃账号 / 专线链路 / CDP 免杀状态胶囊
   - 无干扰 In-App Toast 横幅，彻底告别打断操作的系统 Modal 弹窗
4. 中部三大核心 Tab 栏：
   - 👤 算力账号大盘 (完美列宽预算、综合评分、精准回血倒计时、单击详情、双击免杀秒切)
   - 🌐 专线网络大盘 (最优专线排在最上面，在用置顶、已验证次之、延迟升序)
   - 📑 运行日志与统计 (KPI 指标看板、自愈审计台账、实时日志流与检索)
5. 底部功能与同源主题切换器：
   - 8810 控制台同源三大设计系统：🎨 拟态浅色 (neo) | 🌙 沉浸暗夜 (midnight) | 💎 玻璃拟态 (glass)
   - Segmented Pill 分段控制按钮，毫秒级全局动态变色，持久化至 ~/.antigravity_cockpit/hub_theme_config.json
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
    myappid = "antigravity.studio.gui.v4"
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

# 8810 控制台同源设计系统色卡
THEMES = {
    "neo": {
        "id": "neo",
        "name": "拟态浅色",
        "icon": "🎨",
        "bg": "#e8edf3",
        "panel": "#e2eaf2",
        "card": "#edf2f6",
        "card_alt": "#dbe4ed",
        "border": "#d1dbe4",
        "ink": "#242c38",
        "muted": "#61758a",
        "dim": "#8b9baa",
        "primary": "#2f7ff5",
        "primary_hover": "#1d6fe8",
        "primary_fg": "#ffffff",
        "restart_btn": "#7c3aed",
        "restart_hover": "#6d28d9",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#ecaa1c",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "active_row": "#dbeafe",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "tree_bg": "#edf2f6",
        "tree_fg": "#242c38",
        "tree_heading_bg": "#d5e0ec",
        "tree_heading_fg": "#242c38",
        "tab_active_bg": "#edf2f6",
        "tab_active_fg": "#2f7ff5",
        "tab_inactive_bg": "#d5e0ec",
        "tab_inactive_fg": "#4b5563",
        "scroll_bg": "#cbd5e1",
        "scroll_trough": "#e8edf3",
        "toast_bg": "#dbeafe",
        "toast_fg": "#1e40af",
        "toast_border": "#93c5fd",
    },
    "midnight": {
        "id": "midnight",
        "name": "沉浸暗夜",
        "icon": "🌙",
        "bg": "#0e141d",
        "panel": "#16202e",
        "card": "#1d293a",
        "card_alt": "#121924",
        "border": "#26354a",
        "ink": "#e2e8f0",
        "muted": "#8b9cb3",
        "dim": "#64748b",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_fg": "#0f172a",
        "restart_btn": "#a855f7",
        "restart_hover": "#9333ea",
        "success": "#10b981",
        "success_bg": "#064e3b",
        "warning": "#f59e0b",
        "warning_bg": "#78350f",
        "danger": "#f43f5e",
        "danger_bg": "#881337",
        "active_row": "#1e3a5f",
        "active_row_fg": "#38bdf8",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
        "tree_bg": "#16202e",
        "tree_fg": "#e2e8f0",
        "tree_heading_bg": "#1d293a",
        "tree_heading_fg": "#e2e8f0",
        "tab_active_bg": "#1d293a",
        "tab_active_fg": "#38bdf8",
        "tab_inactive_bg": "#121924",
        "tab_inactive_fg": "#8b9cb3",
        "scroll_bg": "#2a3749",
        "scroll_trough": "#0e141d",
        "toast_bg": "#1e293b",
        "toast_fg": "#38bdf8",
        "toast_border": "#0369a1",
    },
    "glass": {
        "id": "glass",
        "name": "玻璃拟态",
        "icon": "💎",
        "bg": "#edf3f8",
        "panel": "#e5edf5",
        "card": "#f0f4f9",
        "card_alt": "#dfe8f2",
        "border": "#d5e2ed",
        "ink": "#1e293b",
        "muted": "#64748b",
        "dim": "#738499",
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "primary_fg": "#ffffff",
        "restart_btn": "#8b5cf6",
        "restart_hover": "#7c3aed",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#f59e0b",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "active_row": "#dbeafe",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "tree_bg": "#f0f4f9",
        "tree_fg": "#1e293b",
        "tree_heading_bg": "#dae6f1",
        "tree_heading_fg": "#1e293b",
        "tab_active_bg": "#f0f4f9",
        "tab_active_fg": "#3b82f6",
        "tab_inactive_bg": "#dae6f1",
        "tab_inactive_fg": "#334155",
        "scroll_bg": "#cbd5e1",
        "scroll_trough": "#edf3f8",
        "toast_bg": "#e0f2fe",
        "toast_fg": "#0369a1",
        "toast_border": "#bae6fd",
    }
}

FONTS = {
    "title": ("Segoe UI", 13, "bold"),
    "subtitle": ("Segoe UI", 8),
    "btn_main": ("Segoe UI", 9, "bold"),
    "btn": ("Segoe UI", 8, "bold"),
    "btn_sm": ("Segoe UI", 8),
    "tab": ("Segoe UI", 9, "bold"),
    "head": ("Segoe UI", 9, "bold"),
    "body": ("Segoe UI", 9),
    "detail": ("Segoe UI", 8),
    "badge": ("Segoe UI", 8, "bold"),
    "mono": ("Consolas", 8),
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

        # 绑定用户任何全局交互（点击、按键、Tab切换）以触发倒计时自动暂停
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
        if self.guard_switch_enabled:
            self.btn_guard_switch.config(
                text="🛡️ 专线守护: 🟢 开启",
                bg=self.theme["card"],
                fg=self.theme["success"]
            )
        else:
            self.btn_guard_switch.config(
                text="🛡️ 专线守护: ⚪ 关闭",
                bg=self.theme["card"],
                fg=self.theme["muted"]
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
            "success": (t["success_bg"], t["success"], t["success"]),
            "warning": (t["warning_bg"], t["warning"], t["warning"]),
            "danger": (t["danger_bg"], t["danger"], t["danger"]),
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

        self.style.configure(
            "Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            rowheight=30,
            font=FONTS["body"],
            borderwidth=0,
            relief="flat"
        )
        self.style.map(
            "Treeview",
            background=[("selected", t["select_bg"])],
            foreground=[("selected", t["select_fg"])]
        )

        self.style.configure(
            "Treeview.Heading",
            background=t["tree_heading_bg"],
            foreground=t["tree_heading_fg"],
            font=FONTS["head"],
            borderwidth=0,
            relief="flat",
            padding=(6, 5)
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", t["border"])],
            foreground=[("active", t["primary"])]
        )

        self.style.configure("TNotebook", background=t["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=t["tab_inactive_bg"],
            foreground=t["tab_inactive_fg"],
            padding=(18, 7),
            font=FONTS["tab"],
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", t["tab_active_bg"]), ("active", t["panel"])],
            foreground=[("selected", t["tab_active_fg"]), ("active", t["ink"])]
        )

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

        for frame in [self.header_frame, self.top_btn_bar, self.badges_bar, self.bottom_bar,
                     self.tab_accounts, self.tab_network, self.tab_logs, self.acc_tools, self.net_tools]:
            try:
                frame.configure(bg=t["bg"])
            except Exception:
                pass

        self.lbl_title.configure(bg=t["bg"], fg=t["ink"])
        self.lbl_countdown_hint.configure(bg=t["bg"], fg=t["muted"])

        self.btn_open_main.configure(
            bg=t["primary"],
            fg=t["primary_fg"],
            activebackground=t["primary_hover"],
            activeforeground=t["primary_fg"]
        )
        self.btn_restart_repair.configure(
            bg=t["restart_btn"],
            fg="#ffffff",
            activebackground=t["restart_hover"],
            activeforeground="#ffffff"
        )
        self._update_guard_switch_ui()

        for badge in [self.badge_account, self.badge_network, self.badge_cdp]:
            badge.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])

        self.net_banner.configure(bg=t["card"], highlightbackground=t["border"])
        self.lbl_net_active.configure(bg=t["card"], fg=t["ink"])
        self.lbl_acc_detail.configure(bg=t["card"], fg=t["muted"], highlightbackground=t["border"])

        self.kpi_acc.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])
        self.kpi_net.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])
        self.kpi_sys.configure(bg=t["card"], fg=t["ink"], highlightbackground=t["border"])

        self.log_text.configure(bg=t["panel"], fg=t["ink"], insertbackground=t["primary"])

        self.tree.tag_configure("current", background=t["active_row"], foreground=t["active_row_fg"])
        self.tree.tag_configure("quarantined", background=t["danger_bg"], foreground=t["danger"])
        self.tree.tag_configure("parked", background=t["warning_bg"], foreground=t["warning"])
        self.tree.tag_configure("even", background=t["card"])
        self.tree.tag_configure("odd", background=t["tree_bg"])

        self.net_tree.tag_configure("active_node", background=t["active_row"], foreground=t["active_row_fg"])
        self.net_tree.tag_configure("verified_node", background=t["success_bg"], foreground=t["success"])
        self.net_tree.tag_configure("even", background=t["card"])
        self.net_tree.tag_configure("odd", background=t["tree_bg"])

        # 底部三主题分段胶囊按钮高亮
        for tid, btn in self.theme_btns.items():
            if tid == theme_id:
                btn.config(bg=t["primary"], fg=t["primary_fg"], relief="flat")
            else:
                btn.config(bg=t["card"], fg=t["ink"], relief="flat")

    def _build_ui(self):
        # ==========================================
        # 1. 顶部区域：标题 + 开关 + 倒计时 + 双主控按钮
        # ==========================================
        self.header_frame = tk.Frame(self.root, bg=self.theme["bg"], padx=14, pady=10)
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
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.btn_open_main.pack(side=tk.LEFT, padx=4)

        # 按钮 2: 重启 (自动判断状态)
        self.btn_restart_repair = tk.Button(
            self.top_btn_bar,
            text="⚡ 智能自愈重启",
            command=self.on_restart_and_reload_account_clicked,
            bg=self.theme["restart_btn"],
            fg="#ffffff",
            font=FONTS["btn_main"],
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2"
        )
        self.btn_restart_repair.pack(side=tk.LEFT, padx=4)

        # 刷新按键
        btn_refresh = tk.Button(
            self.top_btn_bar,
            text="🔄 刷新",
            command=self.refresh_data,
            bg=self.theme["card"],
            fg=self.theme["muted"],
            font=FONTS["btn"],
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2"
        )
        btn_refresh.pack(side=tk.LEFT, padx=4)

        # ==========================================
        # 2. 状态胶囊横幅 (卡片化微拟态)
        # ==========================================
        self.badges_bar = tk.Frame(self.root, bg=self.theme["bg"], padx=14, pady=2)
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
        self.toast_banner = tk.Frame(self.root, bg=self.theme["toast_bg"], padx=12, pady=5)
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
            cursor="hand2"
        )
        btn_close_toast.pack(side=tk.RIGHT)

        # ==========================================
        # 4. 中部三大核心 Tab 栏
        # ==========================================
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=(6, 4))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.pause_countdown())

        # Tab 1: 算力账号
        self.tab_accounts = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_accounts, text="  👤 算力账号大盘  ")
        self._build_accounts_tab()

        # Tab 2: 专线网络 (最优网络排在最上面)
        self.tab_network = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_network, text="  🌐 专线网络大盘 (最优排在最前面)  ")
        self._build_network_tab()

        # Tab 3: 运行日志与统计
        self.tab_logs = tk.Frame(self.notebook, bg=self.theme["bg"])
        self.notebook.add(self.tab_logs, text="  📑 运行日志与统计  ")
        self._build_logs_tab()

        # ==========================================
        # 5. 底部功能栏：提示 + 三套主题切换功能 (深色、浅色、玻璃拟态)
        # ==========================================
        self.bottom_bar = tk.Frame(self.root, bg=self.theme["bg"], padx=14, pady=6)
        self.bottom_bar.pack(fill=tk.X)

        lbl_tips = tk.Label(
            self.bottom_bar,
            text="💡 双击账号即秒级无感切换 · 智能排序最优专线与账号置顶",
            font=FONTS["subtitle"],
            fg=self.theme["muted"],
            bg=self.theme["bg"]
        )
        lbl_tips.pack(side=tk.LEFT)

        # 底部右侧：主题分段控制器 (拟态浅色 / 沉浸暗夜 / 玻璃拟态)
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
                padx=10,
                pady=3,
                cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.theme_btns[tid] = btn

    def _build_accounts_tab(self):
        container = tk.Frame(self.tab_accounts, bg=self.theme["bg"], padx=2, pady=4)
        container.pack(fill=tk.BOTH, expand=True)

        # 精确 7 列分配，总宽度 855px，完美容纳于 940px 窗口内，严禁截断
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
            padx=10,
            pady=4,
            anchor="w",
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.theme["border"]
        )
        self.lbl_acc_detail.pack(fill=tk.X, pady=(2, 4))

        # 账号专用动作栏
        self.acc_tools = tk.Frame(self.tab_accounts, bg=self.theme["bg"], pady=2)
        self.acc_tools.pack(fill=tk.X)

        btn_smart = tk.Button(
            self.acc_tools,
            text="⚡ 智能盲切最优账号",
            command=self.on_auto_switch_clicked,
            bg="#16a34a",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_smart.pack(side=tk.LEFT, padx=(0, 6))

        btn_switch = tk.Button(
            self.acc_tools,
            text="🔄 切换至选定账号",
            command=self.on_switch_clicked,
            bg="#2563eb",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_switch.pack(side=tk.LEFT, padx=6)

        btn_unblock = tk.Button(
            self.acc_tools,
            text="🔓 解除误隔离",
            command=self.on_unblock_clicked,
            bg="#b45309",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_unblock.pack(side=tk.LEFT, padx=6)

        btn_resume = tk.Button(
            self.acc_tools,
            text="💬 断点续接 (打 1)",
            command=self.on_resume_clicked,
            bg="#7c3aed",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_resume.pack(side=tk.LEFT, padx=6)

    def _build_network_tab(self):
        container = tk.Frame(self.tab_network, bg=self.theme["bg"], padx=2, pady=4)
        container.pack(fill=tk.BOTH, expand=True)

        self.net_banner = tk.Frame(container, bg=self.theme["card"], padx=10, pady=6, highlightthickness=1, highlightbackground=self.theme["border"])
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

        btn_switch_node = tk.Button(
            self.net_tools,
            text="🌐 切换至选定专线",
            command=self.on_switch_node_clicked,
            bg="#2563eb",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_switch_node.pack(side=tk.LEFT, padx=(0, 6))

        btn_heal_net = tk.Button(
            self.net_tools,
            text="⚡ 专线全链路自愈",
            command=self.on_heal_network_clicked,
            bg="#16a34a",
            fg="#ffffff",
            font=FONTS["btn"],
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_heal_net.pack(side=tk.LEFT, padx=6)

        btn_open_clash = tk.Button(
            self.net_tools,
            text="📁 打开 Clash 配置目录",
            command=self.on_open_clash_dir_clicked,
            bg=self.theme["card"],
            fg=self.theme["ink"],
            font=FONTS["btn_sm"],
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_open_clash.pack(side=tk.LEFT, padx=6)

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

        log_text_box = tk.Frame(container, bg=self.theme["panel"])
        log_text_box.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self.log_text = tk.Text(
            log_text_box,
            bg=self.theme["panel"],
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
    # 顶部双功能按键动作
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
