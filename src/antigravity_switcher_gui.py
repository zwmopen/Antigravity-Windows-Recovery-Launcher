# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — Antigravity 管理面板 (Compact Neumorphic & Liquid Glass Edition)
基于 CustomTkinter 构建的高集成、紧凑精致软拟态与液态玻璃桌面中枢：
1. 视觉风格与尺寸调优 (Compact Neumorphic & Liquid Glass)：
   - 窗口尺寸精准收敛至 800x500，彻底解决“面板过大、元素分散、多层浮动卡片碎裂”的问题；
   - 头部卡片一体化融合：品牌标题、5秒自愈/拉起主按钮、状态胶囊、守护开关与倒计时合为一体；
   - 账号与网络采用高密度通透 Treeview，底部操作栏与选中信息横向集成同一行；
   - 1:1 对齐《人生游戏系统》与《团队工作台》三大设计系统：
     🎨 拟态浅色 (#e0e5ec / #4d5b6d / #3b82f6)
     💧 液态玻璃 (#eaf4fd / #f4f9ff / #0284c7)
     🌙 拟态深色 (#1e1e2e / #f4f4f5 / #38bdf8)
2. 交互逻辑 (智能 5 秒倒计时 & 自愈分支)：
   - 若客户端已在运行：5 秒未操作自动平滑激活主窗口
   - 若客户端未运行：5 秒未操作自动执行网络自愈、挂载专线并拉起客户端 (跑网络/测速/自愈全流程)
   - 任何交互 (点击、按键、双击、切换 Tab) 瞬间暂停倒计时并永久常驻
3. 信息命名 (极简纯粹，绝不花里胡哨)：
   - 三大 Tab 直观命名：【账号】、【网络】、【日志】
   - 核心功能按键精炼命名：【⚡ 智能盲切】、【🔄 切换账号】、【🔓 解除隔离】、【💬 恢复会话】等
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
    myappid = "antigravity.studio.gui.ctk.v6.compact"
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
import customtkinter as ctk

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
SINGLE_INSTANCE_MUTEX_NAME = "Local\\Antigravity.ManagerPanel.v6"
SINGLE_INSTANCE_WINDOW_TITLE = "Antigravity 管理面板"
SINGLE_INSTANCE_MUTEX_HANDLE = None

# 人生游戏系统 & 团队工作台 1:1 同源高阶设计系统
THEMES = {
    "neo": {
        "id": "neo",
        "name": "拟态浅色",
        "icon": "🎨",
        "appearance": "Light",
        "bg": "#e0e5ec",
        "panel": "#e0e5ec",
        "card": "#e8edf4",
        "card_border": "#c8d4e2",
        "ink": "#4d5b6d",
        "muted": "#7a8b9e",
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "primary_fg": "#ffffff",
        "restart_btn": "#3d4856",
        "restart_hover": "#2e3742",
        "restart_fg": "#ffffff",
        "btn_sec_bg": "#e0e5ec",
        "btn_sec_border": "#c8d4e2",
        "btn_sec_hover": "#d6dee7",
        "btn_sec_fg": "#4d5b6d",
        "tree_bg": "#e8edf4",
        "tree_even": "#e8edf4",
        "tree_odd": "#e0e5ec",
        "tree_fg": "#4d5b6d",
        "tree_heading_bg": "#d4dfea",
        "tree_heading_fg": "#374151",
        "active_row": "#d4e4f7",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "toast_bg": "#dbeafe",
        "toast_fg": "#1d4ed8",
        "toast_border": "#93c5fd",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#e11d48",
    },
    "glass": {
        "id": "glass",
        "name": "液态玻璃",
        "icon": "💧",
        "appearance": "Light",
        "bg": "#eaf4fd",
        "panel": "#f4f9ff",
        "card": "#ffffff",
        "card_border": "#dae8f5",
        "ink": "#24364c",
        "muted": "#5e738c",
        "primary": "#0284c7",
        "primary_hover": "#0369a1",
        "primary_fg": "#ffffff",
        "restart_btn": "#1e293b",
        "restart_hover": "#0f172a",
        "restart_fg": "#ffffff",
        "btn_sec_bg": "#ffffff",
        "btn_sec_border": "#dae8f5",
        "btn_sec_hover": "#e0f2fe",
        "btn_sec_fg": "#24364c",
        "tree_bg": "#ffffff",
        "tree_even": "#ffffff",
        "tree_odd": "#f4f9ff",
        "tree_fg": "#24364c",
        "tree_heading_bg": "#e1effa",
        "tree_heading_fg": "#0369a1",
        "active_row": "#dbeafe",
        "active_row_fg": "#0369a1",
        "select_bg": "#bae6fd",
        "select_fg": "#0c4a6e",
        "toast_bg": "#e0f2fe",
        "toast_fg": "#0369a1",
        "toast_border": "#7dd3fc",
        "success": "#059669",
        "warning": "#d97706",
        "danger": "#e11d48",
    },
    "midnight": {
        "id": "midnight",
        "name": "拟态深色",
        "icon": "🌙",
        "appearance": "Dark",
        "bg": "#1e1e2e",
        "panel": "#252538",
        "card": "#252538",
        "card_border": "#2d2d42",
        "ink": "#f4f4f5",
        "muted": "#a3b1c6",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_fg": "#0f172a",
        "restart_btn": "#32324a",
        "restart_hover": "#3e3e5c",
        "restart_fg": "#f4f4f5",
        "btn_sec_bg": "#252538",
        "btn_sec_border": "#3b3b55",
        "btn_sec_hover": "#32324a",
        "btn_sec_fg": "#f4f4f5",
        "tree_bg": "#212132",
        "tree_even": "#212132",
        "tree_odd": "#1b1b2a",
        "tree_fg": "#f4f4f5",
        "tree_heading_bg": "#2d2d42",
        "tree_heading_fg": "#f4f4f5",
        "active_row": "#1e3a5f",
        "active_row_fg": "#38bdf8",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
        "toast_bg": "#192b42",
        "toast_fg": "#38bdf8",
        "toast_border": "#0284c7",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#f43f5e",
    }
}

FONT_FAMILY = "Microsoft YaHei UI"

def make_mini_bar(pct, width=7):
    """生成迷你文字进度条：████░░░ 87%"""
    pct = max(0.0, min(100.0, float(pct or 0)))
    filled = round(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {pct:.0f}%"


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

def _focus_existing_panel():
    try:
        user32 = ctypes.windll.user32
        target_hwnd = None
        def enum_cb(hwnd, lparam):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if buff.value == SINGLE_INSTANCE_WINDOW_TITLE:
                        target_hwnd = hwnd
                        return False
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if target_hwnd:
            user32.ShowWindow(target_hwnd, 9)
            user32.SetForegroundWindow(target_hwnd)
    except Exception:
        pass

def acquire_single_instance():
    global SINGLE_INSTANCE_MUTEX_HANDLE
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_bool
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, True, SINGLE_INSTANCE_MUTEX_NAME)
        if not handle:
            return False
        if ctypes.get_last_error() == 183:
            kernel32.CloseHandle(handle)
            _focus_existing_panel()
            return False
        SINGLE_INSTANCE_MUTEX_HANDLE = handle
        return True
    except Exception:
        return True

def release_single_instance():
    global SINGLE_INSTANCE_MUTEX_HANDLE
    if SINGLE_INSTANCE_MUTEX_HANDLE:
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle.restype = ctypes.c_bool
            kernel32.CloseHandle(SINGLE_INSTANCE_MUTEX_HANDLE)
        except Exception:
            pass
        finally:
            SINGLE_INSTANCE_MUTEX_HANDLE = None

def format_reset_time(dt_utc, quota_val):
    if quota_val is not None and quota_val >= 99.5:
        return "已满血"
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

def get_recent_log_lines(filename, max_lines=120):
    fpath = os.path.join(PROXY_DIR, filename)
    if not os.path.exists(fpath):
        return [f"日志文件不存在: {fpath}\n"]
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
            return lines[-max_lines:]
    except Exception as e:
        return [f"读取日志失败: {e}\n"]


class AntigravityModernStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(SINGLE_INSTANCE_WINDOW_TITLE)
        
        # 紧凑精致视口：800x500，拒绝过大分散
        window_w = 860
        window_h = 460
        self.geometry(f"{window_w}x{window_h}")
        self.minsize(800, 430)

        # 屏幕绝对居中
        try:
            ws = self.winfo_screenwidth()
            hs = self.winfo_screenheight()
            x = max(0, (ws - window_w) // 2)
            y = max(0, (hs - window_h) // 2)
            self.geometry(f"{window_w}x{window_h}+{x}+{y}")
        except Exception:
            pass

        if ICON_PATH:
            try:
                self.iconbitmap(ICON_PATH)
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

        # 5秒自动启动/自愈倒计时
        self.countdown_seconds = 5
        self.countdown_paused = False
        self.timer_id = None
        self.toast_timer_id = None

        # 专线守护状态
        self.guard_switch_enabled = True
        self._load_guard_switch_state()

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()
        self.apply_theme(self.theme_id)

        # 绑定全局交互暂停倒计时并常驻
        self.bind_all("<Button-1>", lambda e: self.pause_countdown())
        self.bind_all("<Key>", lambda e: self.pause_countdown())

        self.refresh_data()
        self._start_countdown()

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
        self.guard_switch_enabled = bool(self.switch_guard.get())
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
        st = "开启" if self.guard_switch_enabled else "关闭"
        self.show_toast(f"🛡️ 专线守护已切换为: 【{st}】", level="info")

    def _start_countdown(self):
        if self.countdown_paused:
            return
        
        is_running = is_antigravity_running()
        action_name = "进入主界面" if is_running else "启动并自愈"

        if self.countdown_seconds > 0:
            self.btn_open_main.configure(text=f"▶ {action_name}")
            status_desc = "运行中 · 点击常驻" if is_running else "未启动 · 点击常驻"
            self.lbl_countdown_hint.configure(text=f"⏳ {status_desc}")
            # 独立大数字 badge 显示倒计时 (橙色醒目)
            try:
                self.lbl_countdown_badge.configure(text=str(self.countdown_seconds), text_color="#f97316")
            except Exception:
                pass
            self.countdown_seconds -= 1
            self.timer_id = self.after(1000, self._start_countdown)
        else:
            self.btn_open_main.configure(text=f"▶ {action_name}")
            self.lbl_countdown_hint.configure(text="🟢 面板常驻 · 操作就绪")
            try:
                self.lbl_countdown_badge.configure(text="✓", text_color="#22c55e")
            except Exception:
                pass
            self.on_open_main_clicked(from_timer=True)

    def pause_countdown(self):
        if self.countdown_paused:
            return
        self.countdown_paused = True
        if self.timer_id:
            try:
                self.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        is_running = is_antigravity_running()
        action_name = "进入主界面" if is_running else "启动并自愈"
        self.btn_open_main.configure(text=f"▶ {action_name}")
        self.lbl_countdown_hint.configure(text="🟢 面板常驻 · 操作就绪")
        try:
            self.lbl_countdown_badge.configure(text="", text_color="#22c55e")
        except Exception:
            pass

    def show_toast(self, message, level="info", duration_ms=3200):
        t = self.theme
        color_map = {
            "info": (t["toast_bg"], t["toast_fg"], t["toast_border"]),
            "success": ("#dcfce7", "#15803d", "#86efac"),
            "warning": ("#fef3c7", "#b45309", "#fde68a"),
            "danger": ("#ffe4e6", "#be123c", "#fecdd3"),
        }
        bg, fg, border = color_map.get(level, (t["toast_bg"], t["toast_fg"], t["toast_border"]))
        self.toast_banner.configure(fg_color=bg, border_color=border, border_width=1)
        self.lbl_toast.configure(text=message, text_color=fg)
        self.toast_banner.pack(fill="x", padx=16, pady=(1, 4), before=self.tabview)

        if self.toast_timer_id:
            try:
                self.after_cancel(self.toast_timer_id)
            except Exception:
                pass
        self.toast_timer_id = self.after(duration_ms, self._hide_toast)

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

        ctk.set_appearance_mode(t["appearance"])
        self.configure(fg_color=t["bg"])

        # 头部一体化卡片
        self.header_frame.configure(fg_color=t["panel"], border_color=t["card_border"])
        self.lbl_title.configure(text_color=t["ink"])
        self.lbl_countdown_hint.configure(text_color=t["muted"])
        self.switch_guard.configure(text_color=t["ink"], progress_color=t["primary"])
        self.lbl_header_status.configure(text_color=t["muted"])

        self.btn_open_main.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        try:
            # badge 颜色随主题：深色主题用更亮橙，浅色用标准橙
            badge_color = "#fb923c" if t.get("appearance") == "Dark" else "#f97316"
            self.lbl_countdown_badge.configure(text_color=badge_color)
        except Exception:
            pass
        self.btn_restart_repair.configure(fg_color=t["restart_btn"], hover_color=t["restart_hover"], text_color=t["restart_fg"])
        self.btn_refresh.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # Tabview 拟态/玻璃通透样式
        self.tabview.configure(
            fg_color=t["panel"],
            border_color=t["card_border"],
            segmented_button_selected_color=t["primary"],
            segmented_button_selected_hover_color=t["primary_hover"],
            segmented_button_unselected_color=t["btn_sec_bg"],
            segmented_button_unselected_hover_color=t["btn_sec_hover"],
            segmented_button_fg_color=t["panel"],
            text_color=t["ink"]
        )

        # Tab 1 账号
        self.tree_acc_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.lbl_acc_detail.configure(text_color=t["ink"])
        self.btn_smart.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        for b in [self.btn_switch, self.btn_unblock, self.btn_resume]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # Tab 2 网络
        self.lbl_net_active.configure(text_color=t["ink"])
        self.tree_net_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.btn_switch_node.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        for b in [self.btn_heal_net, self.btn_open_clash]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # Tab 3 日志
        for k in [self.kpi_acc, self.kpi_net, self.kpi_sys]:
            k.configure(fg_color=t["card"], border_color=t["card_border"])
        self.lbl_kpi_acc.configure(text_color=t["ink"])
        self.lbl_kpi_net.configure(text_color=t["ink"])
        self.lbl_kpi_sys.configure(text_color=t["ink"])
        self.tree_inc_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.log_text_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.log_text.configure(bg=t["tree_bg"], fg=t["ink"], insertbackground=t["primary"])
        for b in [self.btn_log_refresh, self.btn_open_log_dir]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # 底部提示与风格切换
        self.lbl_tips.configure(text_color=t["muted"])
        self.seg_theme.configure(
            selected_color=t["primary"],
            selected_hover_color=t["primary_hover"],
            unselected_color=t["btn_sec_bg"],
            unselected_hover_color=t["btn_sec_hover"],
            text_color=t["ink"]
        )

        # 刷新 ttk.Treeview 现代紧凑样式
        self.style.configure(
            "Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            rowheight=20,
            font=(FONT_FAMILY, 8),
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
            font=(FONT_FAMILY, 8, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(4, 2)
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", t["card_border"])],
            foreground=[("active", t["primary"])]
        )

        self.tree.tag_configure("current", background=t["active_row"], foreground=t["active_row_fg"])
        self.tree.tag_configure("quarantined", background="#fee2e2", foreground="#991b1b")
        self.tree.tag_configure("parked", background="#fef3c7", foreground="#92400e")
        self.tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

        self.net_tree.tag_configure("active_node", background=t["active_row"], foreground=t["active_row_fg"])
        self.net_tree.tag_configure("verified_node", background="#dcfce7", foreground="#15803d")
        self.net_tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.net_tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

    def _build_ui(self):
        # 1. 顶部区域：一体化紧凑卡片 (解决“过大分散”的核心关键)
        self.header_frame = ctk.CTkFrame(self, corner_radius=14, border_width=1)
        self.header_frame.pack(fill="x", padx=12, pady=(6, 2))

        # 头部第 1 行：标题 + 核心操作按钮
        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(5, 2))

        self.lbl_title = ctk.CTkLabel(
            top_row,
            text="⚡ Antigravity 管理面板",
            font=(FONT_FAMILY, 11, "bold")
        )
        self.lbl_title.pack(side="left")

        top_btn_bar = ctk.CTkFrame(top_row, fg_color="transparent")
        top_btn_bar.pack(side="right")

        # 倒计时独立数字 badge —— 橙色醒目大字，让用户一眼看见倒计时
        self.lbl_countdown_badge = ctk.CTkLabel(
            top_btn_bar,
            text="5",
            font=(FONT_FAMILY, 20, "bold"),
            text_color="#f97316",
            width=28
        )
        self.lbl_countdown_badge.pack(side="left", padx=(0, 2))

        self.btn_open_main = ctk.CTkButton(
            top_btn_bar,
            text="▶ 进入主界面 (5s)",
            command=self.on_open_main_clicked,
            corner_radius=12,
            font=(FONT_FAMILY, 8, "bold"),
            height=24,
            width=112
        )
        self.btn_open_main.pack(side="left", padx=3)

        self.btn_restart_repair = ctk.CTkButton(
            top_btn_bar,
            text="⚡ 自愈重启",
            command=self.on_restart_and_reload_account_clicked,
            corner_radius=12,
            font=(FONT_FAMILY, 8, "bold"),
            height=24,
            width=76
        )
        self.btn_restart_repair.pack(side="left", padx=3)

        self.btn_refresh = ctk.CTkButton(
            top_btn_bar,
            text="🔄",
            command=self.refresh_data,
            corner_radius=12,
            font=(FONT_FAMILY, 8, "bold"),
            height=24,
            width=26,
            border_width=1
        )
        self.btn_refresh.pack(side="left", padx=3)

        # 头部第 2 行：专线守护开关 + 倒计时提示 + 状态胶囊横条 (内嵌于卡片内，告别分散悬浮)
        sub_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        sub_row.pack(fill="x", padx=10, pady=(0, 5))

        sub_left = ctk.CTkFrame(sub_row, fg_color="transparent")
        sub_left.pack(side="left")

        self.switch_guard = ctk.CTkSwitch(
            sub_left,
            text="专线守护",
            font=(FONT_FAMILY, 8),
            command=self._toggle_guard_switch,
            width=28,
            height=14
        )
        if self.guard_switch_enabled:
            self.switch_guard.select()
        else:
            self.switch_guard.deselect()
        self.switch_guard.pack(side="left")

        self.lbl_countdown_hint = ctk.CTkLabel(
            sub_left,
            text="⏳ 5秒未操作自动启动 · 点击常驻",
            font=(FONT_FAMILY, 8)
        )
        self.lbl_countdown_hint.pack(side="left", padx=(10, 0))

        # 头部右侧内联状态指标
        self.lbl_header_status = ctk.CTkLabel(
            sub_row,
            text="账号: 加载中... | 专线: 检测中...",
            font=(FONT_FAMILY, 8)
        )
        self.lbl_header_status.pack(side="right")

        # 2. In-App 静默反馈横幅
        self.toast_banner = ctk.CTkFrame(self, corner_radius=8, height=22)
        self.lbl_toast = ctk.CTkLabel(self.toast_banner, text="", font=(FONT_FAMILY, 9, "bold"))
        self.lbl_toast.pack(side="left", padx=10, pady=3)
        btn_close_toast = ctk.CTkButton(
            self.toast_banner,
            text="✕",
            command=self._hide_toast,
            width=18,
            height=18,
            corner_radius=9,
            fg_color="transparent",
            text_color="#64748b",
            hover_color="#e2e8f0"
        )
        btn_close_toast.pack(side="right", padx=6, pady=3)

        # 3. 中部三大简洁 Tab 栏：【账号】、【网络】、【日志】
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=14,
            border_width=1
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(1, 2))

        self.tab_accounts = self.tabview.add("账号")
        self.tab_network = self.tabview.add("网络")
        self.tab_logs = self.tabview.add("日志")

        self._build_accounts_tab()
        self._build_network_tab()
        self._build_logs_tab()

        # 4. 底部功能栏 (极简高度，不占地方)
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=12, pady=(0, 4))

        self.lbl_tips = ctk.CTkLabel(
            self.bottom_bar,
            text="💡 双击账号即秒级无感切换 · 智能排序最优专线与账号置顶",
            font=(FONT_FAMILY, 8)
        )
        self.lbl_tips.pack(side="left")

        theme_box = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        theme_box.pack(side="right")

        ctk.CTkLabel(theme_box, text="风格:", font=(FONT_FAMILY, 8)).pack(side="left", padx=(0, 4))

        theme_map = {"neo": "🎨 拟态浅色", "glass": "💧 液态玻璃", "midnight": "🌙 拟态深色"}
        rev_theme_map = {v: k for k, v in theme_map.items()}

        def _on_theme_select(choice):
            tid = rev_theme_map.get(choice, "neo")
            self.apply_theme(tid)

        self.seg_theme = ctk.CTkSegmentedButton(
            theme_box,
            values=["🎨 拟态浅色", "💧 液态玻璃", "🌙 拟态深色"],
            command=_on_theme_select,
            corner_radius=12,
            font=(FONT_FAMILY, 8),
            height=20
        )
        self.seg_theme.set(theme_map.get(self.theme_id, "🎨 拟态浅色"))
        self.seg_theme.pack(side="left")

    def _build_accounts_tab(self):
        # 账号表格容器 (紧凑且精致的圆角卡片)
        self.tree_acc_frame = ctk.CTkFrame(self.tab_accounts, corner_radius=12, border_width=1)
        self.tree_acc_frame.pack(fill="both", expand=True, padx=4, pady=(3, 2))

        columns = ("status", "email", "gemini_5h", "reset_5h", "gemini_weekly", "reset_weekly", "score")
        self.tree = ttk.Treeview(
            self.tree_acc_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        col_defs = [
            ("status", "状态", 46, "center"),
            ("email", "账号", 180, "w"),
            ("gemini_5h", "5h额度", 96, "center"),
            ("reset_5h", "回血", 94, "center"),
            ("gemini_weekly", "周额度", 96, "center"),
            ("reset_weekly", "周重置", 94, "center"),
            ("score", "分", 38, "center"),
        ]

        for col_id, col_name, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_accounts_by(c))
            self.tree.column(col_id, width=col_w, minwidth=40, anchor=col_anchor)

        scrollbar = ttk.Scrollbar(self.tree_acc_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=3, pady=3)
        scrollbar.pack(side="right", fill="y", pady=3, padx=(0, 3))

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 账号底部条：横向融合【左侧选中信息】与【右侧动作按键】(杜绝层层垂直堆叠)
        acc_bottom = ctk.CTkFrame(self.tab_accounts, fg_color="transparent")
        acc_bottom.pack(fill="x", padx=4, pady=(1, 2))

        self.lbl_acc_detail = ctk.CTkLabel(
            acc_bottom,
            text="📌 点击账号查看说明 · 双击账号极速秒切",
            font=(FONT_FAMILY, 8),
            anchor="w"
        )
        self.lbl_acc_detail.pack(side="left", fill="x", expand=True, padx=(2, 8))

        acc_tools = ctk.CTkFrame(acc_bottom, fg_color="transparent")
        acc_tools.pack(side="right")

        self.btn_smart = ctk.CTkButton(
            acc_tools,
            text="⚡ 智能盲切",
            command=self.on_auto_switch_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            height=22,
            width=76
        )
        self.btn_smart.pack(side="left", padx=2)

        self.btn_switch = ctk.CTkButton(
            acc_tools,
            text="🔄 切换账号",
            command=self.on_switch_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            border_width=1,
            height=22,
            width=76
        )
        self.btn_switch.pack(side="left", padx=2)

        self.btn_unblock = ctk.CTkButton(
            acc_tools,
            text="🔓 解除隔离",
            command=self.on_unblock_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            border_width=1,
            height=22,
            width=76
        )
        self.btn_unblock.pack(side="left", padx=2)

        self.btn_resume = ctk.CTkButton(
            acc_tools,
            text="💬 恢复会话",
            command=self.on_resume_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            border_width=1,
            height=22,
            width=76
        )
        self.btn_resume.pack(side="left", padx=2)

    def _build_network_tab(self):
        self.tree_net_frame = ctk.CTkFrame(self.tab_network, corner_radius=12, border_width=1)
        self.tree_net_frame.pack(fill="both", expand=True, padx=4, pady=(4, 4))

        net_columns = ("status", "country", "name", "rtt", "proto", "source")
        self.net_tree = ttk.Treeview(
            self.tree_net_frame,
            columns=net_columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        net_col_defs = [
            ("status", "状态", 80, "center"),
            ("country", "地区", 75, "center"),
            ("name", "专线节点名称", 300, "w"),
            ("rtt", "延迟", 75, "center"),
            ("proto", "协议", 65, "center"),
            ("source", "订阅源", 120, "w"),
        ]

        for col_id, col_name, col_w, col_anchor in net_col_defs:
            self.net_tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_network_by(c))
            self.net_tree.column(col_id, width=col_w, minwidth=40, anchor=col_anchor)

        net_scrollbar = ttk.Scrollbar(self.tree_net_frame, orient="vertical", command=self.net_tree.yview)
        self.net_tree.configure(yscrollcommand=net_scrollbar.set)

        self.net_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        net_scrollbar.pack(side="right", fill="y", pady=3, padx=(0, 3))

        # 网络底部条：横向融合【左侧在用状态】与【右侧节点操作】
        net_bottom = ctk.CTkFrame(self.tab_network, fg_color="transparent")
        net_bottom.pack(fill="x", padx=4, pady=(2, 4))

        self.lbl_net_active = ctk.CTkLabel(
            net_bottom,
            text="🟢 当前专线: 检测中...",
            font=(FONT_FAMILY, 8),
            anchor="w"
        )
        self.lbl_net_active.pack(side="left", fill="x", expand=True, padx=(2, 8))

        net_tools = ctk.CTkFrame(net_bottom, fg_color="transparent")
        net_tools.pack(side="right")

        self.btn_switch_node = ctk.CTkButton(
            net_tools,
            text="🌐 切换节点",
            command=self.on_switch_node_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            height=22,
            width=76
        )
        self.btn_switch_node.pack(side="left", padx=2)

        self.btn_heal_net = ctk.CTkButton(
            net_tools,
            text="⚡ 自愈测速",
            command=self.on_heal_network_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            border_width=1,
            height=22,
            width=76
        )
        self.btn_heal_net.pack(side="left", padx=2)

        self.btn_open_clash = ctk.CTkButton(
            net_tools,
            text="📁 配置文件",
            command=self.on_open_clash_dir_clicked,
            corner_radius=10,
            font=(FONT_FAMILY, 8, "bold"),
            border_width=1,
            height=22,
            width=76
        )
        self.btn_open_clash.pack(side="left", padx=2)

    def _build_logs_tab(self):
        kpi_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=4, pady=(4, 2))

        self.kpi_acc = ctk.CTkFrame(kpi_frame, corner_radius=10, border_width=1)
        self.kpi_acc.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.lbl_kpi_acc = ctk.CTkLabel(self.kpi_acc, text="【账号】加载中...", font=(FONT_FAMILY, 8), justify="left")
        self.lbl_kpi_acc.pack(padx=8, pady=4)

        self.kpi_net = ctk.CTkFrame(kpi_frame, corner_radius=10, border_width=1)
        self.kpi_net.pack(side="left", fill="x", expand=True, padx=3)
        self.lbl_kpi_net = ctk.CTkLabel(self.kpi_net, text="【专线】加载中...", font=(FONT_FAMILY, 8), justify="left")
        self.lbl_kpi_net.pack(padx=8, pady=4)

        self.kpi_sys = ctk.CTkFrame(kpi_frame, corner_radius=10, border_width=1)
        self.kpi_sys.pack(side="left", fill="x", expand=True, padx=(3, 0))
        self.lbl_kpi_sys = ctk.CTkLabel(self.kpi_sys, text="【自愈】加载中...", font=(FONT_FAMILY, 8), justify="left")
        self.lbl_kpi_sys.pack(padx=8, pady=4)

        self.tree_inc_frame = ctk.CTkFrame(self.tab_logs, corner_radius=10, border_width=1, height=85)
        self.tree_inc_frame.pack(fill="x", padx=4, pady=2)

        inc_cols = ("timestamp", "incident_type", "summary", "action")
        self.inc_tree = ttk.Treeview(
            self.tree_inc_frame,
            columns=inc_cols,
            show="headings",
            height=3,
            style="Treeview"
        )
        self.inc_tree.heading("timestamp", text="时间")
        self.inc_tree.heading("incident_type", text="分类")
        self.inc_tree.heading("summary", text="说明")
        self.inc_tree.heading("action", text="动作")

        self.inc_tree.column("timestamp", width=120, anchor="center")
        self.inc_tree.column("incident_type", width=100, anchor="center")
        self.inc_tree.column("summary", width=340, anchor="w")
        self.inc_tree.column("action", width=180, anchor="w")

        inc_scroll = ttk.Scrollbar(self.tree_inc_frame, orient="vertical", command=self.inc_tree.yview)
        self.inc_tree.configure(yscrollcommand=inc_scroll.set)

        self.inc_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        inc_scroll.pack(side="right", fill="y", pady=4, padx=(0, 3))

        log_ctrl = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        log_ctrl.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(log_ctrl, text="日志源:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 4))

        self.log_combo = ctk.CTkComboBox(
            log_ctrl,
            values=["supervisor.log", "account-watcher.log", "smart-quota-watcher.log", "launcher-error.log"],
            state="readonly",
            width=170,
            corner_radius=10,
            font=(FONT_FAMILY, 8),
            height=26,
            command=lambda e: self.load_selected_log()
        )
        self.log_combo.set("supervisor.log")
        self.log_combo.pack(side="left", padx=2)

        self.btn_log_refresh = ctk.CTkButton(
            log_ctrl,
            text="🔄",
            command=self.load_selected_log,
            corner_radius=10,
            width=28,
            height=26,
            border_width=1
        )
        self.btn_log_refresh.pack(side="left", padx=2)

        self.btn_open_log_dir = ctk.CTkButton(
            log_ctrl,
            text="📁",
            command=self.on_open_log_dir_clicked,
            corner_radius=10,
            width=28,
            height=26,
            border_width=1
        )
        self.btn_open_log_dir.pack(side="left", padx=2)

        self.log_filter_var = tk.StringVar()
        ctk.CTkLabel(log_ctrl, text="🔍 过滤:", font=(FONT_FAMILY, 8)).pack(side="left", padx=(8, 4))
        self.ent_filter = ctk.CTkEntry(
            log_ctrl,
            textvariable=self.log_filter_var,
            placeholder_text="搜索日志...",
            font=(FONT_FAMILY, 8),
            corner_radius=10,
            height=26
        )
        self.ent_filter.pack(side="left", fill="x", expand=True, padx=2)
        self.ent_filter.bind("<KeyRelease>", lambda e: self.filter_log_view())

        self.log_text_frame = ctk.CTkFrame(self.tab_logs, corner_radius=10, border_width=1)
        self.log_text_frame.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        self.log_text = tk.Text(
            self.log_text_frame,
            wrap="none",
            font=("Consolas", 8),
            borderwidth=0,
            relief="flat",
            padx=6,
            pady=4
        )
        text_scroll_y = ttk.Scrollbar(self.log_text_frame, orient="vertical", command=self.log_text.yview)
        text_scroll_x = ttk.Scrollbar(self.log_text_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)

        self.log_text.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(4, 0))
        text_scroll_y.pack(side="right", fill="y", pady=(4, 0), padx=(0, 3))
        text_scroll_x.pack(side="bottom", fill="x", padx=4, pady=(0, 3))

    def refresh_data(self):
        def _fetch():
            ret = get_all_accounts_and_quotas()
            if isinstance(ret, tuple) and len(ret) == 2:
                if isinstance(ret[0], list):
                    acc_list, cur_id = ret[0], ret[1]
                else:
                    cur_id, acc_list = ret[0], ret[1]
            else:
                acc_list, cur_id = [], None

            cdp = get_devtools_active_port()
            nodes = get_network_nodes_data()
            inc = get_recent_incidents(15)
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._apply_data(acc_list, cur_id, cdp, nodes, inc))
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_data(self, acc_list, cur_id, cdp, nodes, inc):
        self.accounts = acc_list or []
        self.current_id = cur_id
        self.cdp_port = cdp
        self.network_nodes = nodes or []
        self.incidents = inc or []

        self._render_accounts_table()
        self._render_network_table()
        self._render_incidents_table()
        self._update_badges()
        self.load_selected_log()

    def _update_badges(self):
        cur_acc = next((a for a in self.accounts if a["id"] == self.current_id), None)
        active_node = next((n for n in self.network_nodes if n.get("is_active")), None)

        acc_txt = cur_acc.get("email", "未接入") if cur_acc else "未检测到有效账号"
        net_txt = f"{active_node['flag']} ({active_node['rtt']}ms)" if active_node else "检测中..."
        cdp_txt = f"CDP:{self.cdp_port}" if self.cdp_port else "CDP未挂载"

        # 更新头部内联状态
        self.lbl_header_status.configure(text=f"👤 {acc_txt}  |  🌐 {net_txt}  |  🔌 {cdp_txt}")

        # 网络 Tab 说明
        if active_node:
            self.lbl_net_active.configure(
                text=f"🟢 当前在用专线: {active_node['name']} · 延迟 {active_node['rtt']}ms · {active_node['proto']} · 运行保活中"
            )
        else:
            self.lbl_net_active.configure(text="🟡 专线节点探活中 · 暂未获取到活跃出口...")

        # 日志 Tab KPI
        total = len(self.accounts)
        healthy = len([a for a in self.accounts if not a.get("disabled") and not a.get("is_parked")])
        self.lbl_kpi_acc.configure(text=f"【账号池】在用: {acc_txt}\n健康: {healthy}/{total} 候选")
        
        node_status = f"{active_node['flag']} {active_node['rtt']}ms" if active_node else "探活中"
        self.lbl_kpi_net.configure(text=f"【专线链路】出口: {node_status}\n节点总数: {len(self.network_nodes)} 个")

        guard_st = "运行中" if self.guard_switch_enabled else "已停用"
        self.lbl_kpi_sys.configure(text=f"【守护引擎】自愈状态: {guard_st}\n通道: {cdp_txt}")

    def _render_accounts_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._sort_accounts_data()

        for idx, acc in enumerate(self.accounts):
            is_cur = (acc["id"] == self.current_id)
            if is_cur:
                status_text = "🟢 在用"
                row_tag = "current"
            elif acc.get("disabled"):
                status_text = "🔒 隔离"
                row_tag = "quarantined"
            elif acc.get("is_parked"):
                status_text = "⏸️ 保护"
                row_tag = "parked"
            else:
                status_text = "⚪ 候选"
                row_tag = "even" if idx % 2 == 0 else "odd"

            reset_5h_text = format_reset_time(acc.get("reset_5h_dt"), acc.get("gemini_5h"))
            reset_weekly_text = format_reset_time(acc.get("reset_weekly_dt"), acc.get("gemini_weekly"))

            self.tree.insert(
                "",
                "end",
                iid=acc["id"],
                values=(
                    status_text,
                    acc.get("email", ""),
                    make_mini_bar(acc.get('gemini_5h', 0.0), 6),
                    reset_5h_text,
                    make_mini_bar(acc.get('gemini_weekly', 0.0), 6),
                    reset_weekly_text,
                    f"{acc.get('cockpit_score', 0.0):.0f}"
                ),
                tags=(row_tag,)
            )

    def _render_network_table(self):
        for item in self.net_tree.get_children():
            self.net_tree.delete(item)

        for idx, node in enumerate(self.network_nodes):
            if node.get("is_active"):
                row_tag = "active_node"
            elif node.get("is_verified"):
                row_tag = "verified_node"
            else:
                row_tag = "even" if idx % 2 == 0 else "odd"

            self.net_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    node.get("status", ""),
                    node.get("flag", ""),
                    node.get("name", ""),
                    f"{node.get('rtt', 0)}ms",
                    node.get("proto", "SS"),
                    node.get("source", "")
                ),
                tags=(row_tag,)
            )

    def _render_incidents_table(self):
        for item in self.inc_tree.get_children():
            self.inc_tree.delete(item)

        for inc in reversed(self.incidents):
            ts = inc.get("timestamp", "")
            if len(ts) >= 19:
                ts = ts[5:19].replace("T", " ")
            self.inc_tree.insert(
                "",
                "end",
                values=(
                    ts,
                    inc.get("incident_type", "INCIDENT"),
                    inc.get("summary", ""),
                    inc.get("action", "")
                )
            )

    def load_selected_log(self):
        fname = self.log_combo.get()
        lines = get_recent_log_lines(fname, max_lines=150)
        self.raw_log_lines = lines
        self.filter_log_view()

    def filter_log_view(self):
        kw = self.log_filter_var.get().strip().lower()
        self.log_text.delete("1.0", "end")
        matched = []
        for line in self.raw_log_lines:
            if not kw or kw in line.lower():
                matched.append(line)
        self.log_text.insert("end", "".join(matched))
        self.log_text.see("end")

    def _sort_accounts_by(self, col):
        self.pause_countdown()
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True
        self._render_accounts_table()

    def _sort_accounts_data(self):
        def _get_val(a):
            if self.sort_col == "gemini_5h":
                return a.get("gemini_5h", 0.0)
            if self.sort_col == "gemini_weekly":
                return a.get("gemini_weekly", 0.0)
            if self.sort_col == "score":
                return a.get("cockpit_score", 0.0)
            if self.sort_col == "email":
                return a.get("email", "").lower()
            if self.sort_col == "status":
                return 0 if a["id"] == self.current_id else (1 if not a.get("disabled") else 2)
            return a.get(self.sort_col, "")

        self.accounts.sort(key=lambda x: (
            x["id"] != self.current_id,
            x.get("disabled", False),
            x.get("is_parked", False),
            -_get_val(x) if isinstance(_get_val(x), (int, float)) else _get_val(x)
        ))

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
                desc = "静置保护" if acc.get("is_parked") else "健康候选"
            self.lbl_acc_detail.configure(
                text=f"● {email}  5h {make_mini_bar(g5,5)}  周 {make_mini_bar(gw,5)}  评分 {sc:.0f}"
            )

    # ==========================================
    # 核心交互逻辑：智能判断运行态与自愈启动
    # ==========================================
    def on_open_main_clicked(self, from_timer=False):
        """打开主界面 (运行中则激活窗口；未运行则完整跑自愈网络与启动)"""
        self.pause_countdown()
        is_running = is_antigravity_running()

        if is_running:
            self.show_toast("▶ 正在激活并切换到主界面窗口...", level="info", duration_ms=2500)
            def _activate():
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
                self.after(1000, self.refresh_data)
            threading.Thread(target=_activate, daemon=True).start()
        else:
            self.show_toast("⚡ 正在自愈专线网络并拉起应用 (跑网络/测速/凭据同步)...", level="info", duration_ms=4500)
            def _boot():
                try:
                    launch_antigravity_via_launcher(recovery_reason="LauncherAutoBootstrap", background=False)
                    self.after(0, lambda: self.show_toast("✅ 自愈启动完成，客户端已就绪！", level="success"))
                except Exception as e:
                    self.after(0, lambda: self.show_toast(f"启动异常: {e}", level="danger"))
                finally:
                    self.after(1500, self.refresh_data)
            threading.Thread(target=_boot, daemon=True).start()

    def on_restart_and_reload_account_clicked(self):
        """智能自愈重启 (网络自愈修复与最新账号凭据重载)"""
        self.pause_countdown()
        self.show_toast("⚡ 正在执行客户端自愈重启与凭据同步...", level="info", duration_ms=3500)

        def _run():
            try:
                launch_antigravity_via_launcher(recovery_reason="UserRequestedRepair", background=False)
                self.after(0, lambda: self.show_toast("✅ 自愈重启指令已成功唤起，正在载入凭据与专线...", level="success", duration_ms=4000))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"自愈重启异常: {e}", level="danger"))
            finally:
                self.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    # ==========================================
    # 账号与网络操作 (静默 Toast 反馈)
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
        self.lbl_header_status.configure(text=f"正在秒切至: {target_email}...")
        self.show_toast(f"⚡ 正在免杀秒切至 【{target_email}】...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=account_id)
                if res in ("switched", "ok"):
                    self.after(0, lambda: self.show_toast(f"✅ 已成功秒切至 【{target_email}】！(0 杀进程 · 免杀注入已生效)", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.after(0, lambda: self.show_toast(f"ℹ️ 账号 【{target_email}】 当前配额充沛，无需切换。", level="info"))
                elif res == "busy":
                    self.after(0, lambda: self.show_toast("⚠️ 已有切号正在执行，本次请求已跳过。", level="warning"))
                elif res == "quota_pool_exhausted":
                    self.after(0, lambda: self.show_toast("⚠️ 所有纳管账号周额度均已耗尽，请等待回血。", level="warning"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚡ 切号状态: {res}", level="info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 切号异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.after(600, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_auto_switch_clicked(self):
        self.pause_countdown()
        if self.is_switching:
            self.show_toast("⚠️ 正在切号中，请勿重复操作...", level="warning")
            return

        self.is_switching = True
        self.lbl_header_status.configure(text="正在盲切最优账号...")
        self.show_toast("⚡ 正在按综合评分盲切最优候选账号...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=None)
                if res in ("switched", "ok"):
                    self.after(0, lambda: self.show_toast("✅ 智能盲切完成，已接力最优算力账号！", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.after(0, lambda: self.show_toast("ℹ️ 当前在用账号额度充沛，无需盲切。", level="info"))
                elif res == "quota_pool_exhausted":
                    self.after(0, lambda: self.show_toast("⚠️ 账号池周额度均见底，保护机制启动，跳过盲切。", level="warning"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚡ 盲切调度结果: {res}", level="info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 盲切异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.after(600, self.refresh_data)

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
                    self.after(0, lambda: self.show_toast(f"✅ 账号 【{target_email}】 已成功解除隔离！", level="success"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚠️ 未能解除 【{target_email}】 的隔离状态。", level="warning"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 解封异常: {e}", level="danger"))
            finally:
                self.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_resume_clicked(self):
        self.pause_countdown()
        self.show_toast("💬 正在向反重力窗口注入会话续接协议 (发 1)...", level="info")

        def _run():
            try:
                res = execute_auto_resume()
                self.after(0, lambda: self.show_toast(f"✅ 智能续接结果: {res}", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 续接异常: {e}", level="danger"))
            finally:
                self.after(500, self.refresh_data)

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
                self.after(0, lambda: self.show_toast(f"✅ 优先专线已成功设定为 【{node_name}】！", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 切换专线异常: {e}", level="danger"))
            finally:
                self.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_heal_network_clicked(self):
        self.pause_countdown()
        self.show_toast("⚡ 正在唤起专线自愈引擎全链路复测...", level="info")

        def _run():
            try:
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualHeal"'
                subprocess.Popen(cmd, shell=True)
                self.after(0, lambda: self.show_toast("✅ 专线自愈指令已下发，正在测速优选中...", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 无法启动网络自愈: {e}", level="danger"))
            finally:
                self.after(2000, self.refresh_data)

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
    if not acquire_single_instance():
        return
    try:
        app = AntigravityModernStudio()
        app.protocol("WM_DELETE_WINDOW", app.destroy)
        app.mainloop()
    finally:
        release_single_instance()


if __name__ == "__main__":
    main()
